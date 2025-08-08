# USTB RAG系统 API接口文档

## 📋 概述

USTB RAG系统提供基于Qdrant向量数据库和BCE-embedding-base_v1嵌入模型的文档检索服务，专门为北京科技大学教务场景优化。

**基础信息**：
- **服务地址**: `http://localhost:8000`
- **API版本**: v1
- **技术栈**: FastAPI + Qdrant + BCE-embedding-base_v1
- **数据源**: 4,621条USTB教务文档（含附件链接）

## 🚀 快速开始

### 启动服务
```bash
cd src/services/rag_system
pip install -r requirements.txt
python app.py
```

### 访问文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API接口

### 1. 健康检查

**GET** `/health`

检查RAG系统运行状态。

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "qdrant_status": "healthy",
  "embedding_model": "maidalun1020/bce-embedding-base_v1",
  "document_count": 4621,
  "timestamp": "2025-08-04T10:30:00"
}
```

### 2. 文档检索 ⭐ 核心接口

**POST** `/api/v1/search`

执行语义检索，返回最相关的文档结果。

**请求体**:
```json
{
  "query": "如何选课",
  "top_k": 5,
  "category_filter": ["选课"],
  "date_range": ["2024-01-01", "2024-12-31"]
}
```

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 检索查询，1-500字符 |
| top_k | integer | ❌ | 返回结果数量，默认5，最大20 |
| category_filter | array | ❌ | 分类过滤，如["选课", "考试"] |
| date_range | array | ❌ | 日期范围，格式["开始日期", "结束日期"] |

**响应示例**:
```json
{
  "results": [
    {
      "id": "ustb_001",
      "title": "关于2024年春季学期选课的通知",
      "content": "根据学校教学安排，现将2024年春季学期选课事宜通知如下...",
      "score": 0.85,
      "category": "选课",
      "url": "https://jwc.ustb.edu.cn/notice/001",
      "attachments": [
        {
          "title": "选课操作指南.pdf",
          "url": "https://jwc.ustb.edu.cn/files/guide.pdf"
        }
      ]
    }
  ],
  "total": 5,
  "response_time": 0.245
}
```

### 3. 文档索引

**POST** `/api/v1/index`

重新索引RAG数据集到向量数据库。

**响应示例**:
```json
{
  "status": "success",
  "message": "成功索引 4621 个文档",
  "document_count": 4621
}
```

### 4. 系统统计

**GET** `/api/v1/stats`

获取系统运行统计信息。

**响应示例**:
```json
{
  "collection": {
    "name": "ustb_documents",
    "vectors_count": 4621,
    "points_count": 4621,
    "status": "green",
    "vector_size": 768
  },
  "embedding_model": {
    "model_name": "maidalun1020/bce-embedding-base_v1",
    "device": "cpu",
    "vector_size": 768,
    "is_loaded": true
  },
  "timestamp": "2025-08-04T10:30:00"
}
```

## 🎯 性能指标

### 检索性能
- **Recall@5**: > 0.8 (目标召回率)
- **响应时间**: < 500ms (平均响应时间)
- **并发支持**: 50+ 并发查询
- **相似度阈值**: 0.7 (默认最低相似度)

### 系统性能
- **向量维度**: 768 (BCE-embedding-base_v1)
- **索引算法**: HNSW (Qdrant默认)
- **相似度计算**: 余弦相似度
- **存储模式**: 本地持久化存储

## 🔧 错误处理

### 错误响应格式
```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码
| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 错误示例
```json
{
  "detail": "检索失败: 向量数据库连接超时"
}
```

## 📊 使用示例

### Python客户端示例
```python
import requests

# 检索文档
response = requests.post("http://localhost:8000/api/v1/search", json={
    "query": "转专业申请流程",
    "top_k": 3,
    "category_filter": ["转专业"]
})

results = response.json()
for result in results["results"]:
    print(f"标题: {result['title']}")
    print(f"相似度: {result['score']:.3f}")
    print(f"附件数量: {len(result['attachments'])}")
    print("---")
```

### JavaScript客户端示例
```javascript
// 检索文档
fetch('http://localhost:8000/api/v1/search', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: '期末考试安排',
        top_k: 5,
        category_filter: ['考试']
    })
})
.then(response => response.json())
.then(data => {
    console.log('检索结果:', data.results);
    console.log('响应时间:', data.response_time);
});
```

## 🔍 检索策略

### 语义检索
- 基于BCE-embedding-base_v1中文嵌入模型
- 支持语义理解和同义词匹配
- 自动处理查询扩展和语义推理

### 过滤机制
- **分类过滤**: 按教务分类筛选结果
- **时间过滤**: 按发布日期范围筛选
- **相似度过滤**: 按最低相似度阈值筛选

### 结果排序
1. **相似度排序**: 按语义相似度降序
2. **质量权重**: 结合Qwen评分调整排序
3. **时效性考虑**: 新发布文档适当提权

## 📝 集成指南

### Web前端集成
RAG API设计为RESTful接口，支持多种集成方式：
- ChatGPT-Next-Web (OpenAI兼容API)
- React/Vue.js单页应用 (直接REST API调用)
- 传统多页面应用
- 移动端H5应用

### 后端服务集成
可作为微服务集成到更大的系统中：
- 通过HTTP API调用
- 支持负载均衡和水平扩展
- 提供健康检查接口用于服务发现

## 🚀 部署说明

### 环境要求
- Python 3.8+
- 内存: 4GB+ (推荐8GB)
- 存储: 2GB+ (向量数据库文件)
- CPU: 2核+ (推荐4核)

### Docker部署
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
```

---

**文档版本**: v1.0.0  
**最后更新**: 2025-08-04  
**维护团队**: USTB RAG系统专家
