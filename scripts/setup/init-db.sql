-- PodcastFlow Database Initialization Script
-- This script sets up the initial database structure for the PodcastFlow analytics platform

-- Create schemas for different data layers (Medallion Architecture)
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Create schema for dbt artifacts and metadata
CREATE SCHEMA IF NOT EXISTS dbt_artifacts;

-- Create schema for streaming data staging
CREATE SCHEMA IF NOT EXISTS streaming;

-- Create schema for external data sources
CREATE SCHEMA IF NOT EXISTS external;

-- Grant permissions to the podcastflow user
GRANT ALL PRIVILEGES ON SCHEMA bronze TO podcastflow;
GRANT ALL PRIVILEGES ON SCHEMA silver TO podcastflow;
GRANT ALL PRIVILEGES ON SCHEMA gold TO podcastflow;
GRANT ALL PRIVILEGES ON SCHEMA dbt_artifacts TO podcastflow;
GRANT ALL PRIVILEGES ON SCHEMA streaming TO podcastflow;
GRANT ALL PRIVILEGES ON SCHEMA external TO podcastflow;

-- Create extensions for advanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create a table for tracking data lineage
CREATE TABLE IF NOT EXISTS dbt_artifacts.data_lineage (
    id SERIAL PRIMARY KEY,
    source_table VARCHAR(255),
    target_table VARCHAR(255),
    transformation_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create a table for storing streaming offsets
CREATE TABLE IF NOT EXISTS streaming.kafka_offsets (
    topic VARCHAR(255),
    partition_id INTEGER,
    offset_value BIGINT,
    consumer_group VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (topic, partition_id, consumer_group)
);

-- Create a table for API rate limiting tracking
CREATE TABLE IF NOT EXISTS external.api_rate_limits (
    api_name VARCHAR(100),
    endpoint VARCHAR(255),
    requests_made INTEGER DEFAULT 0,
    requests_limit INTEGER,
    reset_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (api_name, endpoint)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_data_lineage_source ON dbt_artifacts.data_lineage(source_table);
CREATE INDEX IF NOT EXISTS idx_data_lineage_target ON dbt_artifacts.data_lineage(target_table);
CREATE INDEX IF NOT EXISTS idx_kafka_offsets_topic ON streaming.kafka_offsets(topic);
CREATE INDEX IF NOT EXISTS idx_api_rate_limits_api ON external.api_rate_limits(api_name);

-- Insert initial configuration data
INSERT INTO external.api_rate_limits (api_name, endpoint, requests_limit, reset_time) VALUES
('spotify', '/v1/shows', 100, CURRENT_TIMESTAMP + INTERVAL '1 hour'),
('apple_podcasts', '/lookup', 20, CURRENT_TIMESTAMP + INTERVAL '1 minute'),
('podcast_index', '/api/1.0/podcasts', 1000, CURRENT_TIMESTAMP + INTERVAL '1 hour')
ON CONFLICT (api_name, endpoint) DO NOTHING;

-- Create a function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_api_rate_limits_updated_at 
    BEFORE UPDATE ON external.api_rate_limits 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create a view for monitoring data freshness
CREATE OR REPLACE VIEW dbt_artifacts.data_freshness AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname IN ('bronze', 'silver', 'gold');

-- Grant permissions on the new objects
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dbt_artifacts TO podcastflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA streaming TO podcastflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA external TO podcastflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dbt_artifacts TO podcastflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA streaming TO podcastflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA external TO podcastflow;

-- Create a user for read-only dashboard access
CREATE USER dashboard_user WITH PASSWORD 'dashboard123';
GRANT CONNECT ON DATABASE podcastflow TO dashboard_user;
GRANT USAGE ON SCHEMA gold TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO dashboard_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO dashboard_user;

COMMENT ON SCHEMA bronze IS 'Raw data layer - unprocessed data from various sources';
COMMENT ON SCHEMA silver IS 'Cleaned and validated data layer - business logic applied';
COMMENT ON SCHEMA gold IS 'Aggregated and business-ready data layer - optimized for analytics';
COMMENT ON SCHEMA dbt_artifacts IS 'dbt metadata and lineage tracking';
COMMENT ON SCHEMA streaming IS 'Real-time streaming data and offsets';
COMMENT ON SCHEMA external IS 'External API configurations and rate limiting'; 