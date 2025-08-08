"""
USTB RAG系统 - 高级缓存服务
实现多级缓存机制：内存缓存 + Redis缓存
"""
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis不可用，将使用纯内存缓存")

class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self, 
                 memory_max_size: int = 1000,
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 default_ttl: int = 3600):
        
        # 内存缓存配置
        self.memory_cache = {}
        self.memory_access_order = []  # LRU顺序
        self.memory_max_size = memory_max_size
        
        # Redis缓存配置
        self.redis_client = None
        self.default_ttl = default_ttl
        
        # 统计信息
        self.stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        
        # 初始化Redis连接
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host, 
                    port=redis_port, 
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1
                )
                # 测试连接
                self.redis_client.ping()
                logger.info("Redis缓存连接成功")
            except Exception as e:
                logger.warning(f"Redis连接失败，使用纯内存缓存: {e}")
                self.redis_client = None
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """生成缓存键"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        hash_key = hashlib.md5(content.encode('utf-8')).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def _update_memory_lru(self, key: str):
        """更新内存缓存LRU顺序"""
        if key in self.memory_access_order:
            self.memory_access_order.remove(key)
        self.memory_access_order.append(key)
        
        # 清理超出限制的缓存
        while len(self.memory_cache) > self.memory_max_size:
            oldest_key = self.memory_access_order.pop(0)
            if oldest_key in self.memory_cache:
                del self.memory_cache[oldest_key]
    
    def get(self, prefix: str, key_data: Any) -> Optional[Any]:
        """获取缓存数据"""
        cache_key = self._generate_key(prefix, key_data)
        self.stats["total_requests"] += 1
        
        # 1. 检查内存缓存
        if cache_key in self.memory_cache:
            self._update_memory_lru(cache_key)
            self.stats["memory_hits"] += 1
            logger.debug(f"内存缓存命中: {prefix}")
            return self.memory_cache[cache_key]
        
        # 2. 检查Redis缓存
        if self.redis_client:
            try:
                redis_data = self.redis_client.get(cache_key)
                if redis_data:
                    data = json.loads(redis_data)
                    # 写入内存缓存
                    self.memory_cache[cache_key] = data
                    self._update_memory_lru(cache_key)
                    self.stats["redis_hits"] += 1
                    logger.debug(f"Redis缓存命中: {prefix}")
                    return data
            except Exception as e:
                logger.warning(f"Redis读取失败: {e}")
        
        # 3. 缓存未命中
        self.stats["misses"] += 1
        return None
    
    def set(self, prefix: str, key_data: Any, value: Any, ttl: Optional[int] = None):
        """设置缓存数据"""
        cache_key = self._generate_key(prefix, key_data)
        ttl = ttl or self.default_ttl
        
        # 1. 写入内存缓存
        self.memory_cache[cache_key] = value
        self._update_memory_lru(cache_key)
        
        # 2. 写入Redis缓存
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(value, ensure_ascii=False)
                )
                logger.debug(f"数据已缓存: {prefix}")
            except Exception as e:
                logger.warning(f"Redis写入失败: {e}")
    
    def delete(self, prefix: str, key_data: Any):
        """删除缓存数据"""
        cache_key = self._generate_key(prefix, key_data)
        
        # 删除内存缓存
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        if cache_key in self.memory_access_order:
            self.memory_access_order.remove(cache_key)
        
        # 删除Redis缓存
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis删除失败: {e}")
    
    def clear(self, prefix: Optional[str] = None):
        """清空缓存"""
        if prefix:
            # 清空特定前缀的缓存
            keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{prefix}:")]
            for key in keys_to_delete:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.memory_access_order:
                    self.memory_access_order.remove(key)
            
            if self.redis_client:
                try:
                    pattern = f"{prefix}:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis清空失败: {e}")
        else:
            # 清空所有缓存
            self.memory_cache.clear()
            self.memory_access_order.clear()
            
            if self.redis_client:
                try:
                    self.redis_client.flushdb()
                except Exception as e:
                    logger.warning(f"Redis清空失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self.stats["total_requests"]
        if total > 0:
            memory_hit_rate = self.stats["memory_hits"] / total
            redis_hit_rate = self.stats["redis_hits"] / total
            total_hit_rate = (self.stats["memory_hits"] + self.stats["redis_hits"]) / total
            miss_rate = self.stats["misses"] / total
        else:
            memory_hit_rate = redis_hit_rate = total_hit_rate = miss_rate = 0
        
        return {
            "memory_cache_size": len(self.memory_cache),
            "memory_max_size": self.memory_max_size,
            "redis_available": self.redis_client is not None,
            "total_requests": total,
            "memory_hits": self.stats["memory_hits"],
            "redis_hits": self.stats["redis_hits"],
            "misses": self.stats["misses"],
            "memory_hit_rate": round(memory_hit_rate, 3),
            "redis_hit_rate": round(redis_hit_rate, 3),
            "total_hit_rate": round(total_hit_rate, 3),
            "miss_rate": round(miss_rate, 3)
        }

# 全局缓存实例
cache_service = MultiLevelCache()

class CachedEmbeddingService:
    """带缓存的嵌入服务包装器"""
    
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        self.cache = cache_service
    
    def encode_query_cached(self, query: str) -> List[float]:
        """带缓存的查询编码"""
        # 检查缓存
        cached_result = self.cache.get("query_embedding", query)
        if cached_result:
            return cached_result
        
        # 编码并缓存
        embedding = self.embedding_service.encode_query(query)
        self.cache.set("query_embedding", query, embedding, ttl=7200)  # 2小时过期
        
        return embedding

class CachedRetrievalService:
    """带缓存的检索服务包装器"""
    
    def __init__(self, retrieval_engine):
        self.retrieval_engine = retrieval_engine
        self.cache = cache_service
    
    def search_cached(self, query: str, top_k: int = 5, **filters) -> List[Dict[str, Any]]:
        """带缓存的检索"""
        # 生成缓存键
        cache_key = {
            "query": query,
            "top_k": top_k,
            "filters": filters
        }
        
        # 检查缓存
        cached_result = self.cache.get("search_result", cache_key)
        if cached_result:
            return cached_result
        
        # 执行检索并缓存
        results = self.retrieval_engine.search(query, top_k, **filters)
        self.cache.set("search_result", cache_key, results, ttl=1800)  # 30分钟过期
        
        return results
