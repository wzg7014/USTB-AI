# Mem0 Memory System Tool Manual

## 工具概述

Mem0 Memory System Tool 是基于Mem0的增强记忆系统工具，为PromptX提供智能记忆存储和检索功能。

### 核心特性

- **智能记忆管理**: 基于Mem0的向量化记忆存储
- **用户隔离**: 支持多用户记忆隔离
- **语义搜索**: 基于向量相似度的智能搜索
- **多重降级**: Mem0 → Mock → 本地存储的降级机制
- **元数据支持**: 丰富的记忆元数据管理
- **历史追踪**: 记忆变更历史记录

## 安装要求

### Python依赖
```bash
pip install mem0ai openai chromadb
```

### 环境变量
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 工具参数

### 必需参数
- `action` (string): 要执行的操作

### 可选参数
- `user_id` (string): 用户ID，默认为 "luoxiaohan"
- `content` (string): 记忆内容
- `query` (string): 搜索查询
- `memory_id` (string): 记忆ID
- `metadata` (object): 记忆元数据
- `limit` (number): 结果数量限制，默认10
- `threshold` (number): 相似度阈值，默认0.7

## 支持的操作

### 1. add_memory - 添加记忆

添加新的记忆到系统中。

**参数:**
- `content` (必需): 记忆内容
- `metadata` (可选): 记忆元数据

**示例:**
```javascript
{
  "action": "add_memory",
  "content": "用户喜欢使用Python进行AI开发",
  "metadata": {
    "category": "preferences",
    "importance": "high",
    "tags": ["python", "ai", "development"]
  }
}
```

**返回:**
```json
{
  "success": true,
  "action": "add_memory",
  "result": {
    "id": "memory-uuid",
    "message": "Memory added successfully"
  },
  "message": "Memory added: 用户喜欢使用Python进行AI开发..."
}
```

### 2. search_memories - 搜索记忆

基于语义相似度搜索相关记忆。

**参数:**
- `query` (必需): 搜索查询
- `limit` (可选): 返回数量限制
- `threshold` (可选): 相似度阈值

**示例:**
```javascript
{
  "action": "search_memories",
  "query": "Python开发偏好",
  "limit": 5,
  "threshold": 0.7
}
```

**返回:**
```json
{
  "success": true,
  "action": "search_memories",
  "query": "Python开发偏好",
  "count": 2,
  "results": [
    {
      "id": "memory-uuid-1",
      "memory": "用户喜欢使用Python进行AI开发",
      "metadata": {"category": "preferences"},
      "score": 0.85
    }
  ]
}
```

### 3. get_all_memories - 获取所有记忆

获取用户的所有记忆。

**参数:**
- `limit` (可选): 返回数量限制

**示例:**
```javascript
{
  "action": "get_all_memories",
  "limit": 50
}
```

### 4. update_memory - 更新记忆

更新指定记忆的内容。

**参数:**
- `memory_id` (必需): 记忆ID
- `content` (必需): 新的记忆内容

**示例:**
```javascript
{
  "action": "update_memory",
  "memory_id": "memory-uuid",
  "content": "用户非常喜欢使用Python和TypeScript进行AI开发"
}
```

### 5. delete_memory - 删除记忆

删除指定的记忆。

**参数:**
- `memory_id` (必需): 记忆ID

**示例:**
```javascript
{
  "action": "delete_memory",
  "memory_id": "memory-uuid"
}
```

### 6. get_memory_history - 获取记忆历史

获取指定记忆的变更历史。

**参数:**
- `memory_id` (必需): 记忆ID

**示例:**
```javascript
{
  "action": "get_memory_history",
  "memory_id": "memory-uuid"
}
```

### 7. reset_memories - 重置记忆

删除用户的所有记忆。

**示例:**
```javascript
{
  "action": "reset_memories"
}
```

### 8. get_stats - 获取统计信息

获取记忆系统的统计信息。

**示例:**
```javascript
{
  "action": "get_stats"
}
```

**返回:**
```json
{
  "success": true,
  "action": "get_stats",
  "user_id": "luoxiaohan",
  "stats": {
    "total_memories": 15,
    "categories": {
      "preferences": 5,
      "facts": 8,
      "experiences": 2
    },
    "memory_system_type": "Memory"
  }
}
```

## 使用最佳实践

### 1. 记忆内容设计
- **具体明确**: 记忆内容应该具体明确，避免模糊表述
- **结构化**: 使用一致的格式和结构
- **上下文**: 包含足够的上下文信息

### 2. 元数据使用
```javascript
{
  "category": "preferences|facts|experiences|skills",
  "importance": "high|medium|low",
  "tags": ["tag1", "tag2"],
  "source": "conversation|document|inference",
  "confidence": 0.9,
  "last_accessed": "2024-01-01T00:00:00Z"
}
```

### 3. 搜索优化
- **关键词选择**: 使用核心关键词进行搜索
- **阈值调整**: 根据需要调整相似度阈值
- **结果限制**: 合理设置返回数量限制

### 4. 错误处理
工具提供完整的错误处理机制：
- 网络连接错误
- API密钥无效
- 参数验证错误
- 系统降级处理

## 系统架构

### 降级机制
1. **Mem0系统**: 完整的向量化记忆系统
2. **Mock系统**: 本地JSON文件存储
3. **错误处理**: 优雅的错误处理和用户反馈

### 配置选项
```python
config = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "mem0_memories",
            "path": "./mem0_db"
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small"
        }
    }
}
```

## 故障排除

### 常见问题

1. **Mem0初始化失败**
   - 检查OPENAI_API_KEY环境变量
   - 确认网络连接正常
   - 验证API密钥有效性

2. **搜索结果为空**
   - 降低相似度阈值
   - 检查查询关键词
   - 确认记忆已正确添加

3. **性能问题**
   - 调整搜索限制
   - 优化记忆内容长度
   - 考虑定期清理无用记忆

### 日志调试
工具提供详细的日志输出，可通过Python日志系统查看详细信息。

## 版本信息
- 版本: 1.0.0
- 兼容性: PromptX v0.2.0+
- 依赖: Mem0, OpenAI, ChromaDB
