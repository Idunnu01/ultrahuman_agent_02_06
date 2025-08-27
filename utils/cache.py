"""
Redis cache utilities for performance optimization (PythonAnywhere compatible)
"""

import logging
from datetime import timedelta
from functools import wraps
import hashlib
import json
import pickle

logger = logging.getLogger(__name__)

# Try to import Redis, but handle if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using in-memory cache fallback")

class CacheManager:
    """Cache manager with Redis fallback to in-memory storage"""
    
    def __init__(self, redis_url=None):
        self.redis_available = False
        self.redis_client = None
        self.json_redis_client = None
        self._memory_cache = {}
        
        # Try to initialize Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.json_redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory cache: {str(e)}")
                self.redis_available = False
        else:
            logger.info("Redis not configured, using in-memory cache")
    
    def init_app(self, app):
        """Initialize with Flask app"""
        redis_url = app.config.get('REDIS_URL')
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.json_redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis cache initialized with Flask app")
            except Exception as e:
                logger.warning(f"Redis connection failed: {str(e)}")
                self.redis_available = False
        
        app.cache = self
    
    def _make_key(self, *args, **kwargs):
        """Generate cache key from arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key, default=None):
        """Get value from cache"""
        try:
            if self.redis_available:
                value = self.redis_client.get(key)
                if value is None:
                    return default
                return pickle.loads(value)
            else:
                return self._memory_cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {str(e)}")
            return default
    
    def set(self, key, value, expire=None):
        """Set value in cache with optional expiration"""
        try:
            if self.redis_available:
                serialized_value = pickle.dumps(value)
                if expire:
                    if isinstance(expire, timedelta):
                        expire = int(expire.total_seconds())
                    return self.redis_client.setex(key, expire, serialized_value)
                else:
                    return self.redis_client.set(key, serialized_value)
            else:
                self._memory_cache[key] = value
                return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {str(e)}")
            return False
    
    def get_json(self, key, default=None):
        """Get JSON value from cache"""
        try:
            if self.redis_available:
                value = self.json_redis_client.get(key)
                if value is None:
                    return default
                return json.loads(value)
            else:
                return self._memory_cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache JSON get failed for key {key}: {str(e)}")
            return default
    
    def set_json(self, key, value, expire=None):
        """Set JSON value in cache"""
        try:
            if self.redis_available:
                serialized_value = json.dumps(value, default=str)
                if expire:
                    if isinstance(expire, timedelta):
                        expire = int(expire.total_seconds())
                    return self.json_redis_client.setex(key, expire, serialized_value)
                else:
                    return self.json_redis_client.set(key, serialized_value)
            else:
                self._memory_cache[key] = value
                return True
        except Exception as e:
            logger.warning(f"Cache JSON set failed for key {key}: {str(e)}")
            return False
    
    def delete(self, key):
        """Delete key from cache"""
        try:
            if self.redis_available:
                return bool(self.redis_client.delete(key))
            else:
                return self._memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {str(e)}")
            return False
    
    def exists(self, key):
        """Check if key exists in cache"""
        try:
            if self.redis_available:
                return bool(self.redis_client.exists(key))
            else:
                return key in self._memory_cache
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {str(e)}")
            return False

# Global cache instance
cache = CacheManager()

# Cache decorators
def cache_result(expire_seconds=300, key_prefix=""):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{key_prefix}{func.__module__}.{func.__name__}"
            cache_key = f"{func_name}:{cache._make_key(*args, **kwargs)}"
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, expire_seconds)
            return result
        return wrapper
    return decorator

def cache_user_data(expire_seconds=600):
    def decorator(func):
        @wraps(func)
        def wrapper(user_id, *args, **kwargs):
            func_name = f"user_data.{func.__name__}"
            cache_key = f"{func_name}:{user_id}:{cache._make_key(*args, **kwargs)}"
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(user_id, *args, **kwargs)
            cache.set(cache_key, result, expire_seconds)
            return result
        return wrapper
    return decorator

def cache_statistical_analysis(expire_seconds=1800):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"stats.{func.__name__}"
            cache_key = f"{func_name}:{cache._make_key(*args, **kwargs)}"
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, expire_seconds)
            return result
        return wrapper
    return decorator

# Simple classes
class MetricsCache:
    @staticmethod
    def cache_recent_metrics(user_id, metrics_data, hours=24):
        cache_key = f"recent_metrics:{user_id}:{hours}h"
        cache.set_json(cache_key, metrics_data, expire=timedelta(hours=1))
    
    @staticmethod
    def get_recent_metrics(user_id, hours=24):
        cache_key = f"recent_metrics:{user_id}:{hours}h"
        return cache.get_json(cache_key)

class RateLimiter:
    @staticmethod
    def is_allowed(key, limit, window_seconds):
        try:
            import time
            current_time = time.time()
            rate_data = cache.get(key, {'count': 0, 'window_start': current_time})
            
            if current_time - rate_data['window_start'] > window_seconds:
                rate_data = {'count': 1, 'window_start': current_time}
            else:
                rate_data['count'] += 1
            
            cache.set(key, rate_data, window_seconds)
            return rate_data['count'] <= limit
        except Exception as e:
            logger.warning(f"Rate limit check failed: {str(e)}")
            return True
    
    @staticmethod
    def get_remaining(key, limit):
        try:
            rate_data = cache.get(key, {'count': 0})
            return max(0, limit - rate_data['count'])
        except Exception as e:
            return limit
