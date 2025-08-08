# USTB AI教务助手 V2.0 - Graphiti知识图谱升级方案

## 📋 文档说明

**创建时间**: 2025-08-05  
**适用版本**: V2.0及以后版本  
**前置条件**: V1.0混合云架构已稳定运行  
**预期收益**: 查询精度提升50%，响应智能化程度质变  

## 🎯 升级背景与价值

### V1.0架构局限性分析

#### 当前痛点
1. **检索精度瓶颈**: RAG向量检索质量0.65，难以突破0.8
2. **关系理解缺失**: 无法理解"学生-课程-专业-政策"等复杂关系
3. **上下文丢失**: 每次查询独立，无法进行连贯对话
4. **个性化不足**: 无法根据用户身份提供定制化建议
5. **时态查询困难**: 难以回答"去年的政策和今年有什么不同"

#### V2.0升级价值
- **查询精度**: 从0.65提升到>0.9 (50%+提升)
- **智能化水平**: 从文档检索升级到知识推理
- **用户体验**: 从问答工具升级到智能助手
- **技术竞争力**: 从传统RAG升级到前沿知识图谱

## 🏗️ Graphiti技术架构设计

### 核心技术栈
```
Graphiti知识图谱层
├── Neo4j/FalkorDB (图数据库)
├── 实体识别与关系抽取
├── 时态数据管理
└── 混合检索引擎

现有V1.0架构保留
├── DeepSeek微调模型 (基础回答)
├── AutoDL混合云架构
├── ChatGPT-Next-Web前端
└── FastAPI后端服务
```

### 数据架构升级

#### 1. 教务知识图谱设计
```
实体类型:
├── 学生 (Student)
│   ├── 学号、姓名、专业、年级
│   └── 选课历史、成绩记录
├── 课程 (Course) 
│   ├── 课程代码、名称、学分、类型
│   └── 先修课程、开课时间
├── 教师 (Teacher)
│   ├── 工号、姓名、职称、院系
│   └── 授课课程、研究方向
├── 专业 (Major)
│   ├── 专业代码、名称、院系
│   └── 培养方案、毕业要求
├── 政策 (Policy)
│   ├── 政策名称、类型、生效时间
│   └── 适用范围、具体条款
└── 通知 (Notice)
    ├── 标题、内容、发布时间
    └── 发布部门、重要程度

关系类型:
├── 学生-选修-课程 (时间属性)
├── 课程-属于-专业 
├── 课程-先修-课程
├── 教师-授课-课程
├── 政策-适用于-专业
├── 通知-关联-政策
└── 政策-修订-政策 (时态关系)
```

#### 2. 时态数据模型
```
双时态设计:
├── 事件时间 (Event Time): 政策生效时间
├── 系统时间 (System Time): 数据录入时间
├── 版本管理: 政策变更历史追踪
└── 时间点查询: "2023年9月的选课政策"
```

## 🔧 技术实施方案

### 阶段一: 基础设施搭建 (2周)

#### 1.1 图数据库部署
```bash
# Neo4j部署 (推荐)
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/ustb2024 \
  neo4j:5.26

# 或FalkorDB部署 (轻量级选择)
docker run -d \
  --name falkordb \
  -p 6379:6379 \
  falkordb/falkordb:latest
```

#### 1.2 Graphiti环境配置
```python
# 安装依赖
pip install graphiti-core[neo4j]  # 或 [falkordb]

# 基础配置
from graphiti_core import Graphiti

graphiti = Graphiti(
    "bolt://localhost:7687",
    "neo4j",
    "ustb2024",
    llm_client=your_llm_client,  # 复用现有DeepSeek
    embedder=your_embedder       # 复用现有BCE模型
)
```

### 阶段二: 数据迁移与建模 (3周)

#### 2.1 现有数据转换
```python
# 教务数据转换为知识图谱
def convert_ustb_data_to_graph():
    """
    将现有4621条教务数据转换为知识图谱
    """
    for notice in ustb_notices:
        # 实体抽取
        entities = extract_entities(notice)
        
        # 关系识别
        relationships = extract_relationships(notice, entities)
        
        # 时态信息处理
        temporal_info = extract_temporal_info(notice)
        
        # 添加到图谱
        await graphiti.add_episode(
            content=notice.content,
            entities=entities,
            relationships=relationships,
            timestamp=temporal_info
        )
```

#### 2.2 实体识别优化
```python
# 自定义教务实体类型
from pydantic import BaseModel

class USTBStudent(BaseModel):
    student_id: str
    name: str
    major: str
    grade: int
    
class USTBCourse(BaseModel):
    course_code: str
    course_name: str
    credits: int
    course_type: str
    
# 注册自定义实体
graphiti.register_entity_types([USTBStudent, USTBCourse])
```

### 阶段三: 混合检索引擎 (2周)

#### 3.1 多层检索策略
```python
class USTBHybridRetriever:
    def __init__(self):
        self.graphiti = graphiti
        self.traditional_rag = current_rag_system
        
    async def hybrid_search(self, query: str, user_context: dict):
        # 1. 图谱语义检索
        graph_results = await self.graphiti.search(
            query=query,
            search_type="hybrid",  # 语义+关键词+图遍历
            limit=10
        )
        
        # 2. 传统RAG检索 (保底)
        rag_results = await self.traditional_rag.search(query)
        
        # 3. 结果融合与重排
        merged_results = self.merge_and_rerank(
            graph_results, rag_results, user_context
        )
        
        return merged_results
```

#### 3.2 个性化查询增强
```python
async def personalized_query(query: str, user_id: str):
    # 获取用户画像
    user_profile = await graphiti.get_user_context(user_id)
    
    # 查询扩展
    expanded_query = f"""
    用户背景: {user_profile.major}专业{user_profile.grade}年级学生
    查询内容: {query}
    相关历史: {user_profile.recent_queries}
    """
    
    # 执行个性化检索
    results = await graphiti.search(expanded_query)
    return results
```

### 阶段四: API集成与优化 (1周)

#### 4.1 现有API升级
```python
# 升级现有聊天API
@app.post("/api/v2/chat")
async def enhanced_chat(request: ChatRequest):
    # V1.0: 传统RAG + 微调模型
    # V2.0: 知识图谱 + RAG + 微调模型
    
    # 1. 知识图谱检索
    graph_context = await hybrid_retriever.hybrid_search(
        query=request.message,
        user_context=request.user_context
    )
    
    # 2. 微调模型生成 (保留)
    base_answer = await deepseek_model.generate(
        prompt=request.message,
        context=graph_context
    )
    
    # 3. 智能回答合并
    final_answer = merge_graph_and_model_response(
        graph_context, base_answer
    )
    
    return ChatResponse(
        answer=final_answer,
        sources=graph_context.sources,
        related_entities=graph_context.entities
    )
```

## 📊 性能指标与预期收益

### 技术指标提升
| 指标 | V1.0现状 | V2.0目标 | 提升幅度 |
|------|----------|----------|----------|
| 检索精度 | 0.65 | >0.9 | 38%+ |
| 响应时间 | <200ms | <300ms | 可接受 |
| 查询理解 | 关键词匹配 | 语义推理 | 质变 |
| 个性化程度 | 无 | 高度个性化 | 全新能力 |
| 时态查询 | 不支持 | 完全支持 | 全新能力 |

### 用户体验提升
```
V1.0对话示例:
用户: "如何转专业？"
系统: [返回转专业政策文档]

V2.0对话示例:
用户: "如何转专业？"
系统: "根据您计算机专业大二的背景，转专业需要满足以下条件:
1. GPA≥3.5 (您当前3.2，还需提升0.3)
2. 目标专业有空余名额 (当前软件工程专业还有3个名额)
3. 申请时间: 每年3月和9月 (下次机会是2025年3月)
相关文档: [转专业申请表] [GPA提升建议] [软件工程专业介绍]"
```

## 🚨 风险评估与缓解

### 技术风险
1. **复杂度增加**: 
   - 风险: 系统架构复杂化，维护成本上升
   - 缓解: 渐进式迁移，保留V1.0作为降级方案

2. **性能影响**:
   - 风险: 图数据库查询可能影响响应时间
   - 缓解: 多级缓存，异步处理，性能监控

3. **数据质量**:
   - 风险: 知识图谱构建质量影响整体效果
   - 缓解: 严格的数据验证，人工审核机制

### 实施风险
1. **学习成本**: 团队需要学习图数据库和Graphiti
2. **迁移风险**: 数据迁移过程可能出现问题
3. **兼容性**: 与现有系统的集成复杂度

## 💰 成本效益分析

### 开发成本
- **人力成本**: 2个月开发时间 (1人)
- **硬件成本**: Neo4j需要额外2-4GB内存
- **学习成本**: Graphiti和图数据库学习 (1周)

### 预期收益
- **用户体验**: 查询准确率提升50%+
- **技术竞争力**: 从传统RAG升级到前沿技术
- **商业价值**: 支持更复杂的教务场景
- **可扩展性**: 为其他高校复制提供技术基础

## 🛣️ 实施路线图

### 第一阶段: 技术验证 (2周)
- [ ] Graphiti环境搭建和测试
- [ ] 小规模数据转换验证 (100条)
- [ ] 基础查询功能测试
- [ ] 性能基准测试

### 第二阶段: 核心开发 (4周)
- [ ] 完整数据迁移 (4621条)
- [ ] 混合检索引擎开发
- [ ] API接口升级
- [ ] 前端界面适配

### 第三阶段: 集成测试 (2周)
- [ ] 端到端功能测试
- [ ] 性能压力测试
- [ ] 用户验收测试
- [ ] 文档完善

### 第四阶段: 上线部署 (1周)
- [ ] 生产环境部署
- [ ] 监控告警配置
- [ ] 用户培训
- [ ] 正式发布

## 📚 学习资源推荐

### 必读文档
1. [Graphiti官方文档](https://help.getzep.com/graphiti)
2. [Neo4j图数据库教程](https://neo4j.com/docs/)
3. [知识图谱构建最佳实践](https://arxiv.org/abs/2501.13956)

### 实践项目
1. 先用Graphiti做一个简单的个人知识管理系统
2. 学习Neo4j的Cypher查询语言
3. 研究其他高校的知识图谱应用案例

## 🎯 成功标准

### 技术指标
- [ ] 检索精度 > 0.9
- [ ] 响应时间 < 300ms
- [ ] 系统可用性 > 99%
- [ ] 并发支持 > 100用户

### 业务指标  
- [ ] 用户满意度 > 90%
- [ ] 查询成功率 > 95%
- [ ] 个性化推荐准确率 > 80%
- [ ] 复杂查询支持率 > 85%

## 🔗 相关资源链接

### 技术资源
- [Graphiti GitHub仓库](https://github.com/getzep/graphiti)
- [Zep官方文档](https://help.getzep.com/graphiti)
- [Neo4j官方教程](https://neo4j.com/docs/)
- [FalkorDB文档](https://docs.falkordb.com/)

### 论文资源
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- [Knowledge Graphs for AI Applications](https://arxiv.org/abs/2003.02320)

### 社区资源
- [Zep Discord社区](https://discord.com/invite/W8Kw6bsgXQ) - #Graphiti频道
- [Neo4j中文社区](https://community.neo4j.com/)

## 📝 附录: 快速开始代码模板

### A1. 基础环境配置
```python
# requirements.txt 新增依赖
graphiti-core[neo4j]==0.18.2
neo4j==5.26.0
python-dotenv==1.0.0

# .env 环境变量
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ustb2024
GRAPHITI_TELEMETRY_ENABLED=false
```

### A2. 初始化代码
```python
# graphiti_client.py
import os
from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder

async def init_graphiti():
    """初始化Graphiti客户端"""
    graphiti = Graphiti(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        # 复用现有的LLM和嵌入模型配置
    )

    # 初始化索引和约束
    await graphiti.build_indices_and_constraints()
    return graphiti
```

### A3. 数据迁移示例
```python
# data_migration.py
async def migrate_ustb_data():
    """迁移现有教务数据到知识图谱"""
    graphiti = await init_graphiti()

    # 读取现有数据
    with open('data/processed/ustb_notices.json', 'r') as f:
        notices = json.load(f)

    for notice in notices:
        episode_content = f"""
        标题: {notice['title']}
        内容: {notice['content']}
        发布时间: {notice['publish_time']}
        发布部门: {notice['department']}
        分类: {notice['category']}
        """

        # 添加到知识图谱
        await graphiti.add_episode(
            content=episode_content,
            group_id="ustb_notices"
        )

    print(f"成功迁移 {len(notices)} 条数据到知识图谱")
```

### A4. 混合检索示例
```python
# hybrid_search.py
class USTBGraphitiSearch:
    def __init__(self):
        self.graphiti = None
        self.traditional_rag = None  # 现有RAG系统

    async def search(self, query: str, user_context: dict = None):
        """混合检索: Graphiti + 传统RAG"""

        # 1. Graphiti知识图谱检索
        graph_results = await self.graphiti.search(
            query=query,
            group_ids=["ustb_notices"],
            limit=5
        )

        # 2. 传统RAG检索 (保底)
        rag_results = await self.traditional_rag.search(query, limit=3)

        # 3. 结果合并和去重
        combined_results = self._merge_results(graph_results, rag_results)

        return combined_results

    def _merge_results(self, graph_results, rag_results):
        """智能合并两种检索结果"""
        # 实现结果合并逻辑
        pass
```

## 🎯 关键决策点

### 何时启动V2.0升级？
**建议时机**:
1. V1.0系统稳定运行3个月以上
2. 用户反馈中出现复杂查询需求
3. 团队有充足的学习和开发时间
4. 有明确的ROI预期

### 技术选型建议
**图数据库选择**:
- **Neo4j**: 功能强大，生态完善，适合复杂场景
- **FalkorDB**: 轻量级，部署简单，适合快速验证

**部署策略**:
- **渐进式**: 先部署小规模验证，再全量迁移
- **并行式**: V1.0和V2.0并行运行，逐步切换流量

### 风险控制策略
1. **技术风险**: 保留V1.0作为降级方案
2. **性能风险**: 严格的性能测试和监控
3. **数据风险**: 完整的数据备份和恢复机制
4. **用户风险**: 灰度发布，逐步扩大用户范围

---

**文档版本**: v1.0
**最后更新**: 2025-08-05
**下次评审**: V1.0稳定运行后3个月
**负责人**: 梁晓阳

**备注**: 本文档将根据Graphiti技术发展和项目实际需求持续更新。建议在V1.0稳定运行3个月后开始V2.0规划。
