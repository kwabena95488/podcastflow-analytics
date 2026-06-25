"""
PodcastFlow Real-time Listening Events Processor

This Spark Structured Streaming job processes real-time listening events from Kafka
and writes them to Delta Lake following the medallion architecture pattern.

Based on creative phase decisions:
- Spark Structured Streaming for unified batch/streaming processing
- Kafka for message broker
- Delta Lake for ACID transactions and schema evolution
- Windowed aggregations for real-time metrics
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from delta import *

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
SCHEMA_REGISTRY_URL = os.getenv('SCHEMA_REGISTRY_URL', 'http://schema-registry:8081')
DELTA_LAKE_PATH = os.getenv('DELTA_LAKE_PATH', 's3a://podcastflow/delta-lake')
CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/tmp/checkpoints')

def create_spark_session():
    """Create Spark session with Delta Lake and Kafka configurations"""
    
    builder = SparkSession.builder \
        .appName("PodcastFlow-ListeningEventsProcessor") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
        .config("spark.databricks.delta.autoCompact.enabled", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_LOCATION)
    
    # Add Delta Lake packages
    builder = builder.config("spark.jars.packages", 
                           "io.delta:delta-core_2.12:2.4.0,"
                           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
    
    return configure_delta_tables(builder.getOrCreate())

def define_listening_event_schema():
    """Define the schema for listening events from Kafka"""
    
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("user_id", StringType(), False),
        StructField("episode_id", StringType(), False),
        StructField("session_id", StringType(), True),
        StructField("timestamp", TimestampType(), False),
        StructField("event_type", StringType(), False),  # play, pause, skip, complete, download
        StructField("position_seconds", IntegerType(), True),
        StructField("completion_percentage", DoubleType(), True),
        StructField("platform", StringType(), True),
        StructField("device_type", StringType(), True),
        StructField("app_version", StringType(), True),
        StructField("location_country", StringType(), True),
        StructField("skip_count", IntegerType(), True),
        StructField("rewind_count", IntegerType(), True),
        StructField("fast_forward_count", IntegerType(), True),
        StructField("pause_count", IntegerType(), True)
    ])

def read_kafka_stream(spark):
    """Read streaming data from Kafka"""
    
    return spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "listening_events") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

def parse_listening_events(kafka_df):
    """Parse JSON messages from Kafka into structured data"""
    
    schema = define_listening_event_schema()
    
    return kafka_df.select(
        col("key").cast("string").alias("kafka_key"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("timestamp").alias("kafka_timestamp"),
        from_json(col("value").cast("string"), schema).alias("data")
    ).select(
        col("kafka_key"),
        col("topic"),
        col("partition"),
        col("offset"),
        col("kafka_timestamp"),
        col("data.*")
    )

def add_derived_fields(events_df):
    """Add derived fields and data quality indicators"""
    
    return events_df.select(
        "*",
        
        # Add processing timestamp
        current_timestamp().alias("processing_timestamp"),
        
        # Add date partitioning fields
        date_format(col("timestamp"), "yyyy-MM-dd").alias("event_date"),
        hour(col("timestamp")).alias("event_hour"),
        
        # Calculate engagement score using our custom macro logic
        when(col("completion_percentage") >= 80, 
             least(lit(100), 
                   lit(90) + 
                   when(col("position_seconds") > 3600, lit(10)).otherwise(lit(5)) +
                   least(col("rewind_count") * 2, lit(10)) -
                   least(col("skip_count") * 3, lit(15))
             )
        ).when(col("completion_percentage") >= 50,
             least(lit(100),
                   lit(60) + (col("completion_percentage") - 50) * 0.6 +
                   when(col("position_seconds") > 3600, lit(5)).otherwise(lit(2)) +
                   least(col("rewind_count") * 1.5, lit(8)) -
                   least(col("skip_count") * 2, lit(10))
             )
        ).when(col("completion_percentage") >= 25,
             least(lit(100),
                   lit(30) + (col("completion_percentage") - 25) * 1.2 +
                   when(col("position_seconds") > 3600, lit(3)).otherwise(lit(1)) +
                   least(col("rewind_count"), lit(5)) -
                   least(col("skip_count") * 1.5, lit(8))
             )
        ).otherwise(
             greatest(lit(0),
                     col("completion_percentage") +
                     least(col("rewind_count"), lit(3)) -
                     least(col("skip_count"), lit(5))
             )
        ).alias("engagement_score"),
        
        # Data quality flags
        when(col("event_id").isNull() | 
             col("user_id").isNull() | 
             col("episode_id").isNull() | 
             col("timestamp").isNull(), lit(False)
        ).otherwise(lit(True)).alias("is_valid_event"),
        
        # Session indicators
        when(col("event_type") == "play", lit(True)).otherwise(lit(False)).alias("is_session_start"),
        when(col("event_type").isin(["complete", "skip"]), lit(True)).otherwise(lit(False)).alias("is_session_end")
    )

def write_to_bronze_layer(events_df):
    """Write raw events to Bronze layer (Delta Lake)"""
    
    bronze_path = f"{DELTA_LAKE_PATH}/bronze/listening_events"
    
    return events_df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", f"{CHECKPOINT_LOCATION}/bronze_listening_events") \
        .option("path", bronze_path) \
        .partitionBy("event_date") \
        .trigger(processingTime="30 seconds") \
        .start()

def create_real_time_aggregations(events_df):
    """Create real-time aggregations for dashboard"""
    
    # 5-minute tumbling window aggregations
    windowed_metrics = events_df \
        .filter(col("is_valid_event") == True) \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window(col("timestamp"), "5 minutes"),
            col("episode_id"),
            col("platform")
        ).agg(
            count("*").alias("total_events"),
            countDistinct("user_id").alias("unique_listeners"),
            countDistinct("session_id").alias("unique_sessions"),
            avg("completion_percentage").alias("avg_completion_rate"),
            avg("engagement_score").alias("avg_engagement_score"),
            sum(when(col("event_type") == "complete", 1).otherwise(0)).alias("completion_count"),
            sum(when(col("event_type") == "skip", 1).otherwise(0)).alias("skip_count"),
            sum(when(col("event_type") == "download", 1).otherwise(0)).alias("download_count")
        ).select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("episode_id"),
            col("platform"),
            col("total_events"),
            col("unique_listeners"),
            col("unique_sessions"),
            col("avg_completion_rate"),
            col("avg_engagement_score"),
            col("completion_count"),
            col("skip_count"),
            col("download_count"),
            current_timestamp().alias("calculated_at")
        )
    
    return windowed_metrics

def write_real_time_metrics(metrics_df):
    """Write real-time metrics to Silver layer"""
    
    silver_path = f"{DELTA_LAKE_PATH}/silver/real_time_metrics"
    
    return metrics_df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", f"{CHECKPOINT_LOCATION}/silver_real_time_metrics") \
        .option("path", silver_path) \
        .trigger(processingTime="1 minute") \
        .start()

def main():
    """Main processing function"""
    
    print("Starting PodcastFlow Listening Events Processor...")
    
    # Create Spark session
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # Read from Kafka
        kafka_df = read_kafka_stream(spark)
        print("Connected to Kafka stream...")
        
        # Parse events
        events_df = parse_listening_events(kafka_df)
        print("Parsing Kafka messages...")
        
        # Add derived fields
        enriched_events_df = add_derived_fields(events_df)
        print("Adding derived fields...")
        
        # Write to Bronze layer
        bronze_query = write_to_bronze_layer(enriched_events_df)
        print("Writing to Bronze layer...")
        
        # Create real-time aggregations
        metrics_df = create_real_time_aggregations(enriched_events_df)
        print("Creating real-time aggregations...")
        
        # Write metrics to Silver layer
        silver_query = write_real_time_metrics(metrics_df)
        print("Writing metrics to Silver layer...")
        
        print("Streaming jobs started successfully!")
        print("Bronze layer checkpoint:", f"{CHECKPOINT_LOCATION}/bronze_listening_events")
        print("Silver layer checkpoint:", f"{CHECKPOINT_LOCATION}/silver_real_time_metrics")
        
        # Wait for termination
        bronze_query.awaitTermination()
        
    except Exception as e:
        print(f"Error in streaming job: {str(e)}")
        raise e
    finally:
        spark.stop()

if __name__ == "__main__":
    main() 