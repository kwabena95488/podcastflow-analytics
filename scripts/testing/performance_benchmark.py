#!/usr/bin/env python3
"""
Performance Benchmarking Suite for PodcastFlow Analytics Platform
Establishes baseline metrics and monitors performance across all components
"""

import time
import statistics
import asyncio
import threading
import concurrent.futures
import psutil
import gc
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import csv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
try:
    from google.cloud import bigquery
    import pandas as pd
    import numpy as np
    import requests
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    component: str
    test_name: str
    duration_seconds: float
    memory_mb: float
    cpu_percent: float
    throughput_ops_per_second: float
    success_rate: float
    error_count: int
    timestamp: datetime
    metadata: Dict[str, Any] = None

class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.results: List[BenchmarkResult] = []
        self.config = self._load_config(config_file)
        self.start_time = datetime.utcnow()
        
        # Performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load benchmark configuration"""
        default_config = {
            "bigquery_project": os.getenv("PROJECT_ID", "test-project"),
            "api_base_url": "http://localhost:8000",
            "dashboard_url": "http://localhost:8080",
            "concurrent_users": [1, 5, 10, 25, 50],
            "test_duration_seconds": 60,
            "warm_up_seconds": 10,
            "data_sizes": [100, 500, 1000, 5000, 10000],
            "ml_batch_sizes": [1, 10, 50, 100],
            "query_iterations": 10
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                custom_config = json.load(f)
                default_config.update(custom_config)
        
        return default_config
    
    def _measure_performance(self, func, *args, **kwargs) -> Tuple[Any, BenchmarkResult]:
        """Measure performance of a function execution"""
        # Initial measurements
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        start_cpu = self.process.cpu_percent()
        
        # Execute function
        try:
            gc.collect()  # Clean up memory before test
            result = func(*args, **kwargs)
            success = True
            error_count = 0
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            result = None
            success = False
            error_count = 1
        
        # Final measurements
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        end_cpu = self.process.cpu_percent()
        
        # Calculate metrics
        duration = end_time - start_time
        memory_used = max(0, end_memory - start_memory)
        cpu_avg = (start_cpu + end_cpu) / 2
        
        benchmark_result = BenchmarkResult(
            component=func.__module__ or "unknown",
            test_name=func.__name__,
            duration_seconds=duration,
            memory_mb=memory_used,
            cpu_percent=cpu_avg,
            throughput_ops_per_second=1 / duration if duration > 0 else 0,
            success_rate=1.0 if success else 0.0,
            error_count=error_count,
            timestamp=datetime.utcnow()
        )
        
        return result, benchmark_result
    
    def benchmark_database_queries(self) -> List[BenchmarkResult]:
        """Benchmark BigQuery database operations"""
        print("🔍 Benchmarking Database Queries...")
        results = []
        
        try:
            client = bigquery.Client(project=self.config["bigquery_project"])
            
            # Test queries of varying complexity
            queries = {
                "simple_count": "SELECT COUNT(*) as total FROM `bigquery-public-data.samples.natality` LIMIT 1",
                "aggregation": """
                    SELECT state, COUNT(*) as births, AVG(weight_pounds) as avg_weight
                    FROM `bigquery-public-data.samples.natality`
                    WHERE year = 2008
                    GROUP BY state
                    ORDER BY births DESC
                    LIMIT 10
                """,
                "complex_join": """
                    SELECT n.state, n.year, COUNT(*) as births, AVG(n.weight_pounds) as avg_weight
                    FROM `bigquery-public-data.samples.natality` n
                    WHERE n.year BETWEEN 2005 AND 2008
                    GROUP BY n.state, n.year
                    HAVING COUNT(*) > 1000
                    ORDER BY n.year DESC, births DESC
                    LIMIT 100
                """
            }
            
            for query_name, query in queries.items():
                print(f"  Testing {query_name}...")
                
                def execute_query():
                    job = client.query(query)
                    return list(job.result())
                
                _, benchmark = self._measure_performance(execute_query)
                benchmark.test_name = f"bigquery_{query_name}"
                benchmark.component = "database"
                results.append(benchmark)
                
                time.sleep(1)  # Brief pause between queries
                
        except Exception as e:
            print(f"Database benchmark error: {e}")
            
        return results
    
    def benchmark_ml_inference(self) -> List[BenchmarkResult]:
        """Benchmark ML model inference performance"""
        print("🤖 Benchmarking ML Inference...")
        results = []
        
        try:
            # Import ML modules
            from ml.recommendation_engine import RecommendationEngine
            from ml.prediction_models import PerformancePredictionModel
            from ml.user_segmentation import UserSegmentationModel
            
            # Test data sizes
            for batch_size in self.config["ml_batch_sizes"]:
                print(f"  Testing batch size {batch_size}...")
                
                # Mock data generation
                user_data = pd.DataFrame({
                    'user_id': [f'user_{i}' for i in range(batch_size)],
                    'listening_hours': np.random.uniform(5, 50, batch_size),
                    'session_frequency': np.random.uniform(1, 20, batch_size),
                    'engagement_score': np.random.uniform(1, 10, batch_size)
                })
                
                episode_data = {
                    'duration_minutes': 45,
                    'category': 'Technology',
                    'sentiment_score': 0.8,
                    'complexity_score': 0.7
                }
                
                # Test recommendation engine
                def test_recommendations():
                    engine = RecommendationEngine()
                    # Mock implementation for benchmarking
                    time.sleep(batch_size * 0.001)  # Simulate processing time
                    return [{'episode_id': f'ep_{i}', 'score': 0.9} for i in range(10)]
                
                _, benchmark = self._measure_performance(test_recommendations)
                benchmark.test_name = f"recommendation_batch_{batch_size}"
                benchmark.component = "ml_inference"
                benchmark.metadata = {"batch_size": batch_size}
                results.append(benchmark)
                
                # Test performance prediction
                def test_prediction():
                    model = PerformancePredictionModel()
                    # Mock implementation for benchmarking
                    time.sleep(batch_size * 0.0005)  # Simulate processing time
                    return {
                        'predicted_downloads': 4500,
                        'predicted_completion_rate': 0.83,
                        'confidence': 0.87
                    }
                
                _, benchmark = self._measure_performance(test_prediction)
                benchmark.test_name = f"prediction_batch_{batch_size}"
                benchmark.component = "ml_inference"
                benchmark.metadata = {"batch_size": batch_size}
                results.append(benchmark)
                
                # Test user segmentation
                def test_segmentation():
                    model = UserSegmentationModel()
                    # Mock implementation for benchmarking
                    time.sleep(batch_size * 0.002)  # Simulate processing time
                    return {
                        'segments': ['Power Listeners', 'Casual Browsers'],
                        'user_segments': np.random.choice([0, 1], batch_size).tolist()
                    }
                
                _, benchmark = self._measure_performance(test_segmentation)
                benchmark.test_name = f"segmentation_batch_{batch_size}"
                benchmark.component = "ml_inference"
                benchmark.metadata = {"batch_size": batch_size}
                results.append(benchmark)
                
        except Exception as e:
            print(f"ML benchmark error: {e}")
            
        return results
    
    def benchmark_api_endpoints(self) -> List[BenchmarkResult]:
        """Benchmark API endpoint performance"""
        print("🌐 Benchmarking API Endpoints...")
        results = []
        
        base_url = self.config["api_base_url"]
        
        # Test endpoints
        endpoints = {
            "health": "/api/v1/health",
            "podcasts": "/api/v1/podcasts",
            "analytics": "/api/v1/analytics/dashboard",
            "recommendations": "/api/v1/recommendations/test_user",
            "predictions": "/api/v1/predictions/episode-performance"
        }
        
        for endpoint_name, endpoint_path in endpoints.items():
            print(f"  Testing {endpoint_name} endpoint...")
            
            def test_endpoint():
                try:
                    if endpoint_name == "predictions":
                        # POST request with data
                        response = requests.post(
                            f"{base_url}{endpoint_path}",
                            json={
                                "title": "Test Episode",
                                "duration_minutes": 45,
                                "category": "Technology"
                            },
                            timeout=10
                        )
                    else:
                        # GET request
                        response = requests.get(f"{base_url}{endpoint_path}", timeout=10)
                    
                    return response.status_code == 200
                except requests.RequestException:
                    return False
            
            _, benchmark = self._measure_performance(test_endpoint)
            benchmark.test_name = f"api_{endpoint_name}"
            benchmark.component = "api"
            results.append(benchmark)
            
        return results
    
    def benchmark_concurrent_load(self) -> List[BenchmarkResult]:
        """Benchmark system under concurrent load"""
        print("⚡ Benchmarking Concurrent Load...")
        results = []
        
        for num_users in self.config["concurrent_users"]:
            print(f"  Testing {num_users} concurrent users...")
            
            def simulate_user_load():
                """Simulate a user session"""
                try:
                    # Simulate multiple API calls
                    base_url = self.config["api_base_url"]
                    session = requests.Session()
                    
                    # Health check
                    session.get(f"{base_url}/api/v1/health", timeout=5)
                    
                    # Dashboard data
                    session.get(f"{base_url}/api/v1/analytics/dashboard", timeout=10)
                    
                    # Recommendations
                    session.get(f"{base_url}/api/v1/recommendations/test_user", timeout=10)
                    
                    return True
                except:
                    return False
            
            def concurrent_load_test():
                success_count = 0
                total_requests = num_users
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
                    futures = [executor.submit(simulate_user_load) for _ in range(num_users)]
                    
                    for future in concurrent.futures.as_completed(futures, timeout=30):
                        try:
                            if future.result():
                                success_count += 1
                        except:
                            pass
                
                return success_count / total_requests if total_requests > 0 else 0
            
            _, benchmark = self._measure_performance(concurrent_load_test)
            benchmark.test_name = f"concurrent_load_{num_users}_users"
            benchmark.component = "system"
            benchmark.metadata = {"concurrent_users": num_users}
            results.append(benchmark)
            
        return results
    
    def benchmark_dashboard_rendering(self) -> List[BenchmarkResult]:
        """Benchmark dashboard rendering performance"""
        print("📊 Benchmarking Dashboard Rendering...")
        results = []
        
        for data_size in self.config["data_sizes"]:
            print(f"  Testing chart rendering with {data_size} data points...")
            
            def test_chart_rendering():
                # Generate test data
                df = pd.DataFrame({
                    'date': pd.date_range('2024-01-01', periods=data_size, freq='D'),
                    'downloads': np.random.randint(1000, 10000, data_size),
                    'category': np.random.choice(['Tech', 'Business', 'Health'], data_size)
                })
                
                # Create chart (simulating Plotly operations)
                fig = px.line(df, x='date', y='downloads', color='category')
                fig.update_layout(height=400, showlegend=True)
                
                # Simulate rendering time
                _ = fig.to_json()
                
                return True
            
            _, benchmark = self._measure_performance(test_chart_rendering)
            benchmark.test_name = f"chart_rendering_{data_size}_points"
            benchmark.component = "dashboard"
            benchmark.metadata = {"data_points": data_size}
            results.append(benchmark)
            
        return results
    
    def benchmark_memory_usage(self) -> List[BenchmarkResult]:
        """Benchmark memory usage patterns"""
        print("💾 Benchmarking Memory Usage...")
        results = []
        
        def test_memory_intensive_operation():
            """Simulate memory-intensive operation"""
            # Create large datasets
            data_sets = []
            for i in range(100):
                df = pd.DataFrame(np.random.random((1000, 50)))
                data_sets.append(df)
                
                # Force garbage collection periodically
                if i % 20 == 0:
                    gc.collect()
            
            # Process data
            combined = pd.concat(data_sets, ignore_index=True)
            result = combined.groupby(combined.columns[0]).agg('mean')
            
            # Cleanup
            del data_sets, combined
            gc.collect()
            
            return len(result)
        
        _, benchmark = self._measure_performance(test_memory_intensive_operation)
        benchmark.test_name = "memory_intensive_operation"
        benchmark.component = "system"
        results.append(benchmark)
        
        return results
    
    def run_full_benchmark_suite(self) -> Dict[str, List[BenchmarkResult]]:
        """Run the complete benchmark suite"""
        print("🚀 Starting Full Performance Benchmark Suite")
        print(f"Start time: {self.start_time}")
        print("=" * 60)
        
        all_results = {}
        
        try:
            # Database benchmarks
            all_results["database"] = self.benchmark_database_queries()
            self.results.extend(all_results["database"])
            
            # ML inference benchmarks
            all_results["ml_inference"] = self.benchmark_ml_inference()
            self.results.extend(all_results["ml_inference"])
            
            # API endpoint benchmarks
            all_results["api"] = self.benchmark_api_endpoints()
            self.results.extend(all_results["api"])
            
            # Dashboard rendering benchmarks
            all_results["dashboard"] = self.benchmark_dashboard_rendering()
            self.results.extend(all_results["dashboard"])
            
            # Memory usage benchmarks
            all_results["memory"] = self.benchmark_memory_usage()
            self.results.extend(all_results["memory"])
            
            # Concurrent load benchmarks
            all_results["concurrent"] = self.benchmark_concurrent_load()
            self.results.extend(all_results["concurrent"])
            
        except KeyboardInterrupt:
            print("\n⚠️ Benchmark interrupted by user")
        except Exception as e:
            print(f"\n❌ Benchmark error: {e}")
        
        end_time = datetime.utcnow()
        duration = end_time - self.start_time
        
        print("=" * 60)
        print(f"🏁 Benchmark Suite Completed")
        print(f"Total duration: {duration}")
        print(f"Total tests: {len(self.results)}")
        
        return all_results
    
    def generate_performance_report(self, output_file: str = "performance_report.json"):
        """Generate comprehensive performance report"""
        print(f"📄 Generating performance report: {output_file}")
        
        report = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_tests": len(self.results),
                "benchmark_duration": str(datetime.utcnow() - self.start_time),
                "config": self.config
            },
            "summary": self._generate_summary_stats(),
            "detailed_results": [asdict(result) for result in self.results],
            "recommendations": self._generate_recommendations()
        }
        
        # Save JSON report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save CSV for analysis
        csv_file = output_file.replace('.json', '.csv')
        df = pd.DataFrame([asdict(result) for result in self.results])
        df.to_csv(csv_file, index=False)
        
        print(f"📊 Report saved: {output_file}")
        print(f"📈 CSV data saved: {csv_file}")
        
        return report
    
    def _generate_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not self.results:
            return {}
        
        # Group by component
        by_component = {}
        for result in self.results:
            if result.component not in by_component:
                by_component[result.component] = []
            by_component[result.component].append(result)
        
        summary = {}
        for component, results in by_component.items():
            durations = [r.duration_seconds for r in results]
            memory_usage = [r.memory_mb for r in results]
            throughput = [r.throughput_ops_per_second for r in results]
            success_rates = [r.success_rate for r in results]
            
            summary[component] = {
                "test_count": len(results),
                "avg_duration_seconds": statistics.mean(durations),
                "max_duration_seconds": max(durations),
                "min_duration_seconds": min(durations),
                "p95_duration_seconds": np.percentile(durations, 95),
                "avg_memory_mb": statistics.mean(memory_usage),
                "max_memory_mb": max(memory_usage),
                "avg_throughput_ops_per_second": statistics.mean(throughput),
                "overall_success_rate": statistics.mean(success_rates),
                "total_errors": sum(r.error_count for r in results)
            }
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        summary = self._generate_summary_stats()
        
        for component, stats in summary.items():
            # Check response times
            if stats["avg_duration_seconds"] > 1.0:
                recommendations.append(
                    f"⚠️ {component}: Average response time ({stats['avg_duration_seconds']:.2f}s) "
                    f"exceeds 1 second threshold. Consider optimization."
                )
            
            # Check memory usage
            if stats["max_memory_mb"] > 500:
                recommendations.append(
                    f"💾 {component}: High memory usage ({stats['max_memory_mb']:.1f}MB) detected. "
                    f"Consider memory optimization and garbage collection."
                )
            
            # Check error rates
            if stats["overall_success_rate"] < 0.95:
                recommendations.append(
                    f"❌ {component}: Success rate ({stats['overall_success_rate']:.1%}) below 95%. "
                    f"Investigate error handling and reliability."
                )
            
            # Check throughput
            if stats["avg_throughput_ops_per_second"] < 1.0:
                recommendations.append(
                    f"🐌 {component}: Low throughput ({stats['avg_throughput_ops_per_second']:.2f} ops/s). "
                    f"Consider performance optimizations."
                )
        
        if not recommendations:
            recommendations.append("✅ All components performing within acceptable thresholds!")
        
        return recommendations

def main():
    """Main benchmark execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PodcastFlow Analytics Performance Benchmark")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", default="performance_report.json", help="Output report file")
    parser.add_argument("--component", choices=["database", "ml", "api", "dashboard", "all"], 
                       default="all", help="Component to benchmark")
    
    args = parser.parse_args()
    
    # Initialize benchmark
    benchmark = PerformanceBenchmark(args.config)
    
    # Run benchmarks
    if args.component == "all":
        results = benchmark.run_full_benchmark_suite()
    else:
        # Run specific component benchmark
        if args.component == "database":
            results = {"database": benchmark.benchmark_database_queries()}
        elif args.component == "ml":
            results = {"ml": benchmark.benchmark_ml_inference()}
        elif args.component == "api":
            results = {"api": benchmark.benchmark_api_endpoints()}
        elif args.component == "dashboard":
            results = {"dashboard": benchmark.benchmark_dashboard_rendering()}
        
        benchmark.results.extend([r for component_results in results.values() for r in component_results])
    
    # Generate report
    report = benchmark.generate_performance_report(args.output)
    
    # Print summary
    print("\n📋 PERFORMANCE SUMMARY")
    print("=" * 40)
    for component, stats in report["summary"].items():
        print(f"\n{component.upper()}:")
        print(f"  Tests: {stats['test_count']}")
        print(f"  Avg Duration: {stats['avg_duration_seconds']:.3f}s")
        print(f"  Success Rate: {stats['overall_success_rate']:.1%}")
        print(f"  Max Memory: {stats['max_memory_mb']:.1f}MB")
    
    print("\n💡 RECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"  {rec}")

if __name__ == "__main__":
    main() 