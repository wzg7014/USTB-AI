# RAG系统性能优化方案

## 🚨 当前问题分析

### 性能问题
- **响应时间**: 2133.9ms >> 500ms (超标326%)
- **检索质量**: 0.45 << 0.8 (仅达到56%)

### 根本原因
1. **嵌入模型推理慢**: BCE模型每次查询都重新计算
2. **向量检索效率低**: Qdrant配置未优化
3. **缺乏缓存机制**: 重复查询重复计算
4. **相似度阈值过高**: 0.7阈值过滤掉太多结果

## 🎯 优化策略

### 1. 嵌入模型优化

#### 1.1 模型预热和缓存
```python
class OptimizedEmbeddingService:
    def __init__(self):
        self.model_name = "maidalun1020/bce-embedding-base_v1"
        self.device = "cpu"
        self.batch_size = 64  # 增加批处理大小
        self.query_cache = {}  # 查询缓存
        self.model = None
        self._load_and_warmup()
    
    def _load_and_warmup(self):
        """加载模型并预热"""
        self.model = SentenceTransformer(self.model_name, device=self.device)
        
        # 模型预热
        warmup_texts = ["测试", "查询", "检索", "文档"]
        self.model.encode(warmup_texts)
        logger.info("模型预热完成")
    
    @lru_cache(maxsize=1000)
    def encode_query_cached(self, query: str) -> List[float]:
        """带缓存的查询编码"""
        return self.model.encode([query])[0].tolist()
```

#### 1.2 批处理优化
```python
def encode_batch_optimized(self, texts: List[str]) -> List[List[float]]:
    """优化的批处理编码"""
    if not texts:
        return []
    
    # 增大批处理大小，减少调用次数
    batch_size = 64
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # 禁用进度条，减少IO开销
        batch_embeddings = self.model.encode(
            batch, 
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # 归一化提升检索效果
        )
        embeddings.extend(batch_embeddings)
    
    return [emb.tolist() for emb in embeddings]
```

### 2. Qdrant向量数据库优化

#### 2.1 HNSW索引优化
```python
def create_optimized_collection(self):
    """创建优化的向量集合"""
    collection_config = {
        "vectors": {
            "size": 768,
            "distance": "Cosine"
        },
        "hnsw_config": {
            "m": 32,  # 增加连接数，提升召回率
            "ef_construct": 400,  # 增加构建时搜索深度
            "full_scan_threshold": 20000  # 提高全扫描阈值
        },
        "optimizers_config": {
            "default_segment_number": 4,  # 增加段数
            "max_segment_size": 50000,
            "memmap_threshold": 100000,
            "indexing_threshold": 20000
        }
    }
    
    self.client.create_collection(
        collection_name=self.collection_name,
        vectors_config=collection_config["vectors"],
        hnsw_config=collection_config["hnsw_config"],
        optimizers_config=collection_config["optimizers_config"]
    )
```

#### 2.2 检索参数优化
```python
def search_optimized(self, query_vector, top_k=5, similarity_threshold=0.3):
    """优化的向量检索"""
    search_results = self.client.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        limit=top_k * 2,  # 检索更多候选，后续重排
        score_threshold=similarity_threshold,  # 降低阈值
        search_params={
            "hnsw": {
                "ef": 256  # 增加搜索时的ef参数
            }
        }
    )
    return search_results[:top_k]
```

### 3. 缓存机制实现

#### 3.1 多级缓存策略
```python
import redis
from functools import lru_cache
import hashlib

class CachedRetrievalEngine:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.memory_cache = {}
        self.cache_ttl = 3600  # 1小时过期
    
    def _get_cache_key(self, query: str, top_k: int, filters: dict) -> str:
        """生成缓存键"""
        cache_data = f"{query}_{top_k}_{str(sorted(filters.items()))}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def search_with_cache(self, query: str, top_k: int = 5, **filters):
        """带缓存的检索"""
        cache_key = self._get_cache_key(query, top_k, filters)
        
        # 1. 内存缓存
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # 2. Redis缓存
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            self.memory_cache[cache_key] = result
            return result
        
        # 3. 实际检索
        result = self._actual_search(query, top_k, **filters)
        
        # 4. 写入缓存
        self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
        self.memory_cache[cache_key] = result
        
        return result
```

### 4. 检索质量优化

#### 4.1 混合检索策略
```python
def hybrid_search(self, query: str, top_k: int = 5):
    """混合检索：向量检索 + 关键词检索"""
    # 1. 向量检索
    vector_results = self.vector_search(query, top_k * 2, threshold=0.3)
    
    # 2. 关键词检索
    keyword_results = self.keyword_search(query, top_k)
    
    # 3. 结果融合和重排
    combined_results = self._merge_and_rerank(vector_results, keyword_results, query)
    
    return combined_results[:top_k]

def _merge_and_rerank(self, vector_results, keyword_results, query):
    """结果融合和重排"""
    # 合并结果
    all_results = {}
    
    # 向量检索结果权重0.7
    for i, result in enumerate(vector_results):
        doc_id = result['id']
        score = result['similarity_score'] * 0.7 + (1 - i/len(vector_results)) * 0.1
        all_results[doc_id] = {**result, 'final_score': score}
    
    # 关键词检索结果权重0.3
    for i, result in enumerate(keyword_results):
        doc_id = result['id']
        keyword_score = (1 - i/len(keyword_results)) * 0.3
        if doc_id in all_results:
            all_results[doc_id]['final_score'] += keyword_score
        else:
            all_results[doc_id] = {**result, 'final_score': keyword_score}
    
    # 按最终得分排序
    return sorted(all_results.values(), key=lambda x: x['final_score'], reverse=True)
```

#### 4.2 查询扩展
```python
def expand_query(self, query: str) -> str:
    """查询扩展，提升召回率"""
    # 同义词扩展
    synonyms = {
        "选课": ["课程选择", "选修", "课程"],
        "考试": ["测试", "考核", "评估"],
        "申请": ["报名", "提交", "办理"]
    }
    
    expanded_terms = [query]
    for term, syns in synonyms.items():
        if term in query:
            expanded_terms.extend(syns)
    
    return " ".join(expanded_terms)
```

## 🚀 实施计划

### 阶段1：立即优化 (2小时)
1. 降低相似度阈值：0.7 → 0.3
2. 增加检索数量：top_k * 2
3. 优化Qdrant HNSW参数
4. 添加查询缓存

### 阶段2：深度优化 (4小时)
1. 实现多级缓存机制
2. 优化嵌入模型批处理
3. 实现混合检索策略
4. 添加查询扩展

### 阶段3：性能验证 (1小时)
1. 重新运行性能测试
2. 验证响应时间 < 500ms
3. 验证检索质量 > 0.8
4. 生成优化报告

## 📊 预期效果

- **响应时间**: 2133ms → 200-300ms (提升85%)
- **检索质量**: 0.45 → 0.85+ (提升89%)
- **系统稳定性**: 显著提升
- **用户体验**: 大幅改善

## 🔧 监控指标

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'response_times': [],
            'cache_hit_rate': 0,
            'search_quality': []
        }
    
    def log_search(self, query, response_time, cache_hit, quality_score):
        self.metrics['response_times'].append(response_time)
        self.metrics['search_quality'].append(quality_score)
        
        if cache_hit:
            self.metrics['cache_hit_rate'] += 1
    
    def get_performance_report(self):
        return {
            'avg_response_time': np.mean(self.metrics['response_times']),
            'p95_response_time': np.percentile(self.metrics['response_times'], 95),
            'cache_hit_rate': self.metrics['cache_hit_rate'] / len(self.metrics['response_times']),
            'avg_quality': np.mean(self.metrics['search_quality'])
        }
```

这个优化方案将显著提升RAG系统性能，确保通过梁晓阳项目经理的验收标准。
