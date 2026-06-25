"""
ML Model Optimization Module for PodcastFlow Analytics Platform
Implements model quantization, batch processing, and caching for improved performance
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import pickle
import os
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from functools import wraps, lru_cache
import json

try:
    import tensorflow as tf
    import tensorflow_model_optimization as tfmot
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    import joblib
except ImportError as e:
    print(f"Missing ML dependencies: {e}")
    print("Please install: pip install tensorflow tensorflow-model-optimization scikit-learn joblib")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelPerformanceMetrics:
    """Container for model performance metrics"""
    model_name: str
    inference_time_ms: float
    memory_usage_mb: float
    accuracy: float
    throughput_requests_per_second: float
    batch_size: int
    quantized: bool
    cached: bool
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

class ModelCache:
    """High-performance model result cache with TTL and size limits"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = {}
        self._timestamps = {}
        self._access_counts = {}
        self._lock = threading.RLock()
    
    def _generate_key(self, inputs: Any, model_name: str) -> str:
        """Generate cache key for model inputs"""
        if isinstance(inputs, dict):
            content = json.dumps(inputs, sort_keys=True)
        elif isinstance(inputs, (list, tuple)):
            content = str(inputs)
        else:
            content = str(inputs)
        
        key_content = f"{model_name}:{content}"
        return hashlib.sha256(key_content.encode()).hexdigest()[:32]
    
    def get(self, inputs: Any, model_name: str) -> Optional[Any]:
        """Get cached model result"""
        key = self._generate_key(inputs, model_name)
        
        with self._lock:
            if key in self._cache:
                # Check if cache entry is still valid
                timestamp = self._timestamps[key]
                if time.time() - timestamp < self.default_ttl:
                    self._access_counts[key] = self._access_counts.get(key, 0) + 1
                    return self._cache[key]
                else:
                    # Remove expired entry
                    self._remove_key(key)
        
        return None
    
    def set(self, inputs: Any, model_name: str, result: Any, ttl: Optional[int] = None):
        """Cache model result"""
        key = self._generate_key(inputs, model_name)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Remove least recently used entries if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = result
            self._timestamps[key] = time.time()
            self._access_counts[key] = 1
    
    def _remove_key(self, key: str):
        """Remove a key from all cache structures"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._access_counts.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._access_counts:
            return
        
        lru_key = min(self._access_counts.keys(), 
                     key=lambda k: (self._access_counts[k], self._timestamps[k]))
        self._remove_key(lru_key)
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._access_counts.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": sum(self._access_counts.values()) / len(self._access_counts) if self._access_counts else 0,
                "total_accesses": sum(self._access_counts.values())
            }

class BatchProcessor:
    """Optimized batch processing for ML models"""
    
    def __init__(self, max_batch_size: int = 100, max_workers: int = 4):
        self.max_batch_size = max_batch_size
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_batch(
        self, 
        inputs: List[Any], 
        model_func: Callable,
        batch_size: Optional[int] = None
    ) -> List[Any]:
        """Process inputs in optimized batches"""
        batch_size = batch_size or self.max_batch_size
        
        if len(inputs) <= batch_size:
            # Single batch processing
            return model_func(inputs)
        
        # Multi-batch processing
        results = []
        futures = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            future = self._executor.submit(model_func, batch)
            futures.append(future)
        
        # Collect results in order
        for future in futures:
            batch_results = future.result()
            results.extend(batch_results if isinstance(batch_results, list) else [batch_results])
        
        return results
    
    async def process_batch_async(
        self,
        inputs: List[Any],
        model_func: Callable,
        batch_size: Optional[int] = None
    ) -> List[Any]:
        """Asynchronous batch processing"""
        batch_size = batch_size or self.max_batch_size
        
        if len(inputs) <= batch_size:
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, model_func, inputs
            )
        
        # Create async tasks for each batch
        tasks = []
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            task = asyncio.get_event_loop().run_in_executor(
                self._executor, model_func, batch
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
        
        return results
    
    def close(self):
        """Close the executor"""
        self._executor.shutdown(wait=True)

class ModelQuantizer:
    """TensorFlow model quantization for improved performance"""
    
    @staticmethod
    def quantize_model(
        model: tf.keras.Model,
        representative_dataset: Optional[tf.data.Dataset] = None,
        optimization_target: str = "balanced"  # "speed", "size", "balanced"
    ) -> tf.lite.Interpreter:
        """Quantize a TensorFlow model using TFLite"""
        
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        
        # Configure optimization
        if optimization_target == "speed":
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        elif optimization_target == "size":
            converter.optimizations = [tf.lite.Optimize.OPTIMIZE_FOR_SIZE]
        else:  # balanced
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Post-training quantization
        if representative_dataset is not None:
            converter.representative_dataset = representative_dataset
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.int8
            converter.inference_output_type = tf.int8
        
        # Convert model
        quantized_model = converter.convert()
        
        # Create interpreter
        interpreter = tf.lite.Interpreter(model_content=quantized_model)
        interpreter.allocate_tensors()
        
        logger.info(f"Model quantized successfully. "
                   f"Size reduction: {len(quantized_model) / (1024*1024):.2f}MB")
        
        return interpreter
    
    @staticmethod
    def create_representative_dataset(
        data: np.ndarray,
        num_samples: int = 100
    ) -> tf.data.Dataset:
        """Create representative dataset for quantization"""
        
        # Sample random indices
        indices = np.random.choice(len(data), min(num_samples, len(data)), replace=False)
        representative_data = data[indices]
        
        def representative_data_gen():
            for sample in representative_data:
                yield [sample.astype(np.float32)]
        
        return representative_data_gen

class OptimizedMLModel:
    """Optimized ML model wrapper with caching, batching, and quantization"""
    
    def __init__(
        self,
        model_name: str,
        model_path: str,
        enable_cache: bool = True,
        enable_quantization: bool = False,
        max_batch_size: int = 100,
        cache_size: int = 10000
    ):
        self.model_name = model_name
        self.model_path = model_path
        self.enable_cache = enable_cache
        self.enable_quantization = enable_quantization
        self.max_batch_size = max_batch_size
        
        # Initialize components
        self.cache = ModelCache(cache_size) if enable_cache else None
        self.batch_processor = BatchProcessor(max_batch_size)
        self.performance_metrics: List[ModelPerformanceMetrics] = []
        
        # Load model
        self.model = None
        self.quantized_model = None
        self._load_model()
        
        # Performance tracking
        self._inference_count = 0
        self._total_inference_time = 0.0
        self._lock = threading.Lock()
    
    def _load_model(self):
        """Load the ML model"""
        try:
            if os.path.exists(self.model_path):
                if self.model_path.endswith('.pkl') or self.model_path.endswith('.joblib'):
                    # Scikit-learn model
                    self.model = joblib.load(self.model_path)
                    logger.info(f"Loaded scikit-learn model: {self.model_name}")
                elif self.model_path.endswith('.h5') or os.path.isdir(self.model_path):
                    # TensorFlow model
                    self.model = tf.keras.models.load_model(self.model_path)
                    logger.info(f"Loaded TensorFlow model: {self.model_name}")
                    
                    # Create quantized version if enabled
                    if self.enable_quantization:
                        self._create_quantized_model()
                else:
                    logger.warning(f"Unsupported model format: {self.model_path}")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
                # Create a dummy model for testing
                self._create_dummy_model()
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")
            self._create_dummy_model()
    
    def _create_dummy_model(self):
        """Create a dummy model for testing purposes"""
        logger.info(f"Creating dummy model for {self.model_name}")
        
        class DummyModel:
            def predict(self, X):
                time.sleep(0.01)  # Simulate processing time
                if hasattr(X, 'shape'):
                    return np.random.random((X.shape[0], 1))
                else:
                    return np.random.random((len(X), 1))
        
        self.model = DummyModel()
    
    def _create_quantized_model(self):
        """Create quantized version of TensorFlow model"""
        if isinstance(self.model, tf.keras.Model):
            try:
                # Create dummy representative dataset
                input_shape = self.model.input_shape
                if input_shape[0] is None:
                    input_shape = (100,) + input_shape[1:]
                
                representative_data = np.random.random(input_shape).astype(np.float32)
                rep_dataset = ModelQuantizer.create_representative_dataset(representative_data)
                
                self.quantized_model = ModelQuantizer.quantize_model(
                    self.model, rep_dataset, "balanced"
                )
                logger.info(f"Created quantized model for {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to create quantized model: {e}")
    
    def _measure_inference_time(self, func):
        """Decorator to measure inference time"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            inference_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            with self._lock:
                self._inference_count += 1
                self._total_inference_time += inference_time
            
            return result, inference_time
        return wrapper
    
    def predict_single(self, inputs: Any, use_cache: bool = None) -> Tuple[Any, Dict[str, Any]]:
        """Single prediction with optimization"""
        use_cache = use_cache if use_cache is not None else self.enable_cache
        
        # Check cache first
        if use_cache and self.cache:
            cached_result = self.cache.get(inputs, self.model_name)
            if cached_result is not None:
                return cached_result, {"cached": True, "inference_time_ms": 0}
        
        # Perform inference
        start_time = time.time()
        
        try:
            if self.quantized_model and self.enable_quantization:
                result = self._predict_quantized(inputs)
            else:
                result = self._predict_regular(inputs)
            
            inference_time = (time.time() - start_time) * 1000
            
            # Cache result
            if use_cache and self.cache:
                self.cache.set(inputs, self.model_name, result)
            
            # Record metrics
            metrics = ModelPerformanceMetrics(
                model_name=self.model_name,
                inference_time_ms=inference_time,
                memory_usage_mb=self._get_memory_usage(),
                accuracy=0.0,  # Would be calculated with ground truth
                throughput_requests_per_second=1000 / inference_time if inference_time > 0 else 0,
                batch_size=1,
                quantized=self.enable_quantization and self.quantized_model is not None,
                cached=False,
                timestamp=datetime.utcnow()
            )
            self.performance_metrics.append(metrics)
            
            return result, {
                "cached": False,
                "inference_time_ms": inference_time,
                "quantized": metrics.quantized
            }
            
        except Exception as e:
            logger.error(f"Prediction error for {self.model_name}: {e}")
            return None, {"error": str(e)}
    
    def predict_batch(
        self, 
        inputs_list: List[Any], 
        batch_size: Optional[int] = None,
        use_async: bool = False
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """Batch prediction with optimization"""
        batch_size = batch_size or self.max_batch_size
        start_time = time.time()
        
        def batch_predict_func(batch_inputs):
            if self.quantized_model and self.enable_quantization:
                return [self._predict_quantized(inp) for inp in batch_inputs]
            else:
                return [self._predict_regular(inp) for inp in batch_inputs]
        
        try:
            if use_async:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    self.batch_processor.process_batch_async(
                        inputs_list, batch_predict_func, batch_size
                    )
                )
                loop.close()
            else:
                results = self.batch_processor.process_batch(
                    inputs_list, batch_predict_func, batch_size
                )
            
            total_time = (time.time() - start_time) * 1000
            avg_time_per_request = total_time / len(inputs_list) if inputs_list else 0
            
            # Record batch metrics
            metrics = ModelPerformanceMetrics(
                model_name=self.model_name,
                inference_time_ms=avg_time_per_request,
                memory_usage_mb=self._get_memory_usage(),
                accuracy=0.0,
                throughput_requests_per_second=len(inputs_list) * 1000 / total_time if total_time > 0 else 0,
                batch_size=len(inputs_list),
                quantized=self.enable_quantization and self.quantized_model is not None,
                cached=False,
                timestamp=datetime.utcnow(),
                metadata={"async": use_async, "total_time_ms": total_time}
            )
            self.performance_metrics.append(metrics)
            
            return results, {
                "total_time_ms": total_time,
                "avg_time_per_request_ms": avg_time_per_request,
                "throughput_rps": metrics.throughput_requests_per_second,
                "batch_size": len(inputs_list),
                "quantized": metrics.quantized,
                "async": use_async
            }
            
        except Exception as e:
            logger.error(f"Batch prediction error for {self.model_name}: {e}")
            return [], {"error": str(e)}
    
    def _predict_regular(self, inputs: Any) -> Any:
        """Regular model prediction"""
        if hasattr(self.model, 'predict'):
            if isinstance(inputs, (list, np.ndarray)):
                return self.model.predict(np.array(inputs).reshape(1, -1))[0]
            else:
                return self.model.predict([[inputs]])[0]
        else:
            # Dummy prediction
            return {"prediction": 0.8, "confidence": 0.9}
    
    def _predict_quantized(self, inputs: Any) -> Any:
        """Quantized model prediction"""
        if self.quantized_model is None:
            return self._predict_regular(inputs)
        
        try:
            # Get input and output details
            input_details = self.quantized_model.get_input_details()
            output_details = self.quantized_model.get_output_details()
            
            # Prepare input data
            if isinstance(inputs, (list, tuple)):
                input_data = np.array(inputs, dtype=np.float32).reshape(1, -1)
            else:
                input_data = np.array([[inputs]], dtype=np.float32)
            
            # Set input tensor
            self.quantized_model.set_tensor(input_details[0]['index'], input_data)
            
            # Run inference
            self.quantized_model.invoke()
            
            # Get output
            output_data = self.quantized_model.get_tensor(output_details[0]['index'])
            return output_data[0]
            
        except Exception as e:
            logger.warning(f"Quantized prediction failed, falling back to regular: {e}")
            return self._predict_regular(inputs)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        if not self.performance_metrics:
            return {"message": "No performance metrics available"}
        
        # Calculate statistics
        inference_times = [m.inference_time_ms for m in self.performance_metrics]
        throughputs = [m.throughput_requests_per_second for m in self.performance_metrics]
        memory_usage = [m.memory_usage_mb for m in self.performance_metrics]
        
        report = {
            "model_name": self.model_name,
            "total_predictions": len(self.performance_metrics),
            "avg_inference_time_ms": np.mean(inference_times),
            "p95_inference_time_ms": np.percentile(inference_times, 95),
            "max_inference_time_ms": np.max(inference_times),
            "avg_throughput_rps": np.mean(throughputs),
            "max_throughput_rps": np.max(throughputs),
            "avg_memory_usage_mb": np.mean(memory_usage),
            "quantization_enabled": self.enable_quantization,
            "cache_enabled": self.enable_cache,
            "cache_stats": self.cache.stats() if self.cache else None,
            "recent_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "inference_time_ms": m.inference_time_ms,
                    "throughput_rps": m.throughput_requests_per_second,
                    "batch_size": m.batch_size,
                    "quantized": m.quantized,
                    "cached": m.cached
                }
                for m in self.performance_metrics[-10:]  # Last 10 metrics
            ]
        }
        
        return report
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations"""
        report = self.get_performance_report()
        
        if report.get("message"):
            return report
        
        suggestions = []
        
        # Analyze inference time
        avg_time = report["avg_inference_time_ms"]
        if avg_time > 100:  # 100ms threshold
            suggestions.append(
                f"High inference time ({avg_time:.1f}ms). Consider enabling quantization "
                f"or reducing model complexity."
            )
        
        # Analyze cache performance
        if self.cache:
            cache_stats = self.cache.stats()
            hit_rate = cache_stats.get("hit_rate", 0)
            if hit_rate < 0.5:
                suggestions.append(
                    f"Low cache hit rate ({hit_rate:.1%}). Consider increasing cache size "
                    f"or TTL for better performance."
                )
        elif not self.enable_cache:
            suggestions.append("Consider enabling caching for repeated predictions.")
        
        # Analyze quantization
        if not self.enable_quantization and isinstance(self.model, tf.keras.Model):
            suggestions.append(
                "Consider enabling quantization for TensorFlow models to improve speed "
                "and reduce memory usage."
            )
        
        # Analyze batch processing
        single_predictions = sum(1 for m in self.performance_metrics if m.batch_size == 1)
        total_predictions = len(self.performance_metrics)
        if single_predictions / total_predictions > 0.8:
            suggestions.append(
                "High ratio of single predictions. Consider batching requests "
                "for better throughput."
            )
        
        return {
            **report,
            "optimization_suggestions": suggestions
        }
    
    def benchmark(self, num_requests: int = 100, batch_sizes: List[int] = None) -> Dict[str, Any]:
        """Run comprehensive benchmark tests"""
        if batch_sizes is None:
            batch_sizes = [1, 10, 50, 100]
        
        results = {}
        
        # Generate test data
        test_inputs = [np.random.random(10).tolist() for _ in range(num_requests)]
        
        for batch_size in batch_sizes:
            logger.info(f"Benchmarking batch size: {batch_size}")
            
            # Split inputs into batches
            batches = [test_inputs[i:i + batch_size] for i in range(0, len(test_inputs), batch_size)]
            
            start_time = time.time()
            total_predictions = 0
            
            for batch in batches:
                _, stats = self.predict_batch(batch, batch_size=batch_size)
                total_predictions += len(batch)
            
            total_time = time.time() - start_time
            
            results[f"batch_size_{batch_size}"] = {
                "total_time_seconds": total_time,
                "total_predictions": total_predictions,
                "avg_time_per_prediction_ms": (total_time * 1000) / total_predictions,
                "throughput_rps": total_predictions / total_time if total_time > 0 else 0
            }
        
        return {
            "benchmark_results": results,
            "recommendations": self._generate_benchmark_recommendations(results)
        }
    
    def _generate_benchmark_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on benchmark results"""
        recommendations = []
        
        # Find optimal batch size
        best_throughput = 0
        best_batch_size = 1
        
        for batch_key, stats in results.items():
            throughput = stats["throughput_rps"]
            if throughput > best_throughput:
                best_throughput = throughput
                best_batch_size = int(batch_key.split("_")[-1])
        
        recommendations.append(
            f"Optimal batch size for throughput: {best_batch_size} "
            f"({best_throughput:.1f} requests/second)"
        )
        
        # Check for performance degradation with larger batches
        batch_1_throughput = results.get("batch_size_1", {}).get("throughput_rps", 0)
        batch_100_throughput = results.get("batch_size_100", {}).get("throughput_rps", 0)
        
        if batch_100_throughput > batch_1_throughput * 5:
            recommendations.append(
                "Significant performance improvement with batching. "
                "Consider implementing request batching in production."
            )
        
        return recommendations
    
    def close(self):
        """Clean up resources"""
        if self.batch_processor:
            self.batch_processor.close()
        if self.cache:
            self.cache.clear()

# Example usage for podcast analytics models
class PodcastRecommendationModel(OptimizedMLModel):
    """Optimized recommendation model for podcasts"""
    
    def __init__(self, model_path: str, **kwargs):
        super().__init__("podcast_recommendation", model_path, **kwargs)
    
    def recommend_episodes(
        self, 
        user_features: Dict[str, Any], 
        num_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """Get podcast episode recommendations"""
        
        # Prepare input features
        feature_vector = [
            user_features.get("listening_hours", 0),
            user_features.get("session_frequency", 0),
            user_features.get("engagement_score", 0),
            user_features.get("category_preference", 0),
            user_features.get("duration_preference", 0)
        ]
        
        result, stats = self.predict_single(feature_vector)
        
        # Convert to recommendation format
        if isinstance(result, dict):
            scores = result.get("scores", [0.9] * num_recommendations)
        else:
            scores = [float(result)] * num_recommendations
        
        recommendations = [
            {
                "episode_id": f"ep_{i+1}",
                "score": scores[i % len(scores)] if scores else 0.9,
                "confidence": 0.85
            }
            for i in range(num_recommendations)
        ]
        
        return recommendations

class PodcastPerformancePredictionModel(OptimizedMLModel):
    """Optimized performance prediction model for podcasts"""
    
    def __init__(self, model_path: str, **kwargs):
        super().__init__("performance_prediction", model_path, **kwargs)
    
    def predict_episode_performance(
        self, 
        episode_features: Dict[str, Any]
    ) -> Dict[str, float]:
        """Predict episode performance metrics"""
        
        # Prepare input features
        feature_vector = [
            episode_features.get("duration_minutes", 45),
            episode_features.get("sentiment_score", 0.7),
            episode_features.get("complexity_score", 0.5),
            episode_features.get("host_popularity", 0.8),
            episode_features.get("topic_trending_score", 0.6)
        ]
        
        result, stats = self.predict_single(feature_vector)
        
        # Convert to prediction format
        if isinstance(result, dict):
            return result
        else:
            return {
                "predicted_downloads": int(float(result) * 10000),
                "predicted_completion_rate": min(float(result), 1.0),
                "predicted_rating": min(float(result) * 5, 5.0),
                "confidence": 0.85,
                "inference_time_ms": stats.get("inference_time_ms", 0)
            }

# Factory function for model optimization
def create_optimized_model(
    model_type: str,
    model_path: str,
    optimization_config: Optional[Dict[str, Any]] = None
) -> OptimizedMLModel:
    """Factory function to create optimized models"""
    
    config = optimization_config or {}
    
    model_classes = {
        "recommendation": PodcastRecommendationModel,
        "performance_prediction": PodcastPerformancePredictionModel,
        "generic": OptimizedMLModel
    }
    
    model_class = model_classes.get(model_type, OptimizedMLModel)
    return model_class(model_path, **config)

# Example usage and testing
if __name__ == "__main__":
    # Create optimized recommendation model
    rec_model = create_optimized_model(
        "recommendation",
        "./models/recommendation_model.pkl",
        {
            "enable_cache": True,
            "enable_quantization": False,
            "max_batch_size": 50,
            "cache_size": 5000
        }
    )
    
    # Test single prediction
    user_features = {
        "listening_hours": 25.5,
        "session_frequency": 8,
        "engagement_score": 7.8,
        "category_preference": 0.8,
        "duration_preference": 0.6
    }
    
    recommendations = rec_model.recommend_episodes(user_features)
    print(f"Generated {len(recommendations)} recommendations")
    
    # Run benchmark
    benchmark_results = rec_model.benchmark(num_requests=100)
    print(f"Benchmark completed: {benchmark_results}")
    
    # Get performance report
    report = rec_model.get_performance_report()
    print(f"Performance report: {report}")
    
    # Clean up
    rec_model.close() 