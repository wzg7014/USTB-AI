# USTB AI教务助手项目 - 8专家分工详细文档

## 🎯 项目概览

### 项目基本信息
- **项目名称**: USTB AI教务助手 - 混合架构升级版
- **开发周期**: 14天 (2025-08-01 至 2025-08-14)
- **专家配置**: 8个专业专家 + 1个项目经理
- **管理模式**: RACI矩阵责任分配 + 阶段性验收
- **技术架构**: RAG+微调混合架构 + PromptX MCP工具链

### 核心目标
- **数据处理**: 4180条→500条高质量数据 (Qwen评分≥7.5分)
- **问答生成**: 约2500个高质量问答对 (质量评分≥0.8)
- **系统构建**: RAG检索系统 + Web界面 + 微调模型
- **性能指标**: 准确率>85%，响应时间<2秒，Recall@5>0.8

## 🏗️ 8专家架构体系

### 三层协作架构
```
           项目经理（梁晓阳）
                  |
    ┌─────────────┼─────────────┐
    │             │             │
  数据层        开发层        集成层
┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
│           │ │           │ │           │
数据处理    数据科学   RAG系统   Web前端   模型训练   系统集成
专家        专家      专家      专家      专家      专家
│           │ │           │ │           │
└───────────┘ └───────────┘ └───────────┘
     |             |             |
  问答生成       Web后端      (独立专家)
   专家          专家
```

## 📋 专家详细分工

### 🔬 数据层专家（3个）

#### 1. 数据处理专家
**专业领域**: 数据工程 + 数据清洗
**RACI角色**: R(执行者) - 数据筛选和清洗的主要执行者

**核心职责**:
- Qwen API环境配置和6维度评分系统开发
- 4180条→500条高质量数据筛选（评分≥7.5分）
- 智能去重处理（语义+URL+标题，重复率<2%）
- **双数据集生成**：
  - RAG检索数据集（包含附件链接，用于实时检索）
  - 微调训练数据集（纯文本内容，用于模型训练）
- 附件信息提取和链接验证
- 数据格式标准化和质量报告生成

**技能要求**:
- Python编程和数据处理库（pandas, numpy）
- Qwen API调用和参数优化
- 数据质量评估和统计分析
- JSON/CSV数据格式处理

**具体交付物**:
1. **RAG检索数据文件**: `data/processed/rag_data.json` (包含附件链接)
   ```json
   [
     {
       "id": "ustb_001",
       "title": "关于转专业申请的通知",
       "content": "根据学校规定，转专业申请需要满足以下条件...",
       "url": "https://jwc.ustb.edu.cn/notice/001",
       "category": "转专业",
       "publish_date": "2024-09-01",
       "attachments": [
         {
           "name": "转专业申请表.docx",
           "url": "https://jwc.ustb.edu.cn/files/transfer_form.docx",
           "type": "application/docx"
         },
         {
           "name": "转专业流程图.pdf",
           "url": "https://jwc.ustb.edu.cn/files/transfer_process.pdf",
           "type": "application/pdf"
         }
       ],
       "qwen_score": 8.2,
       "score_breakdown": {
         "completeness": 8.5,
         "relevance": 8.0,
         "timeliness": 8.5,
         "usability": 8.0,
         "accuracy": 8.0,
         "density": 7.5
       }
     }
   ]
   ```

2. **微调训练数据文件**: `data/processed/training_data.json` (纯文本，无附件)
   ```json
   [
     {
       "id": "ustb_001",
       "title": "关于转专业申请的通知",
       "content": "根据学校规定，转专业申请需要满足以下条件：1.学习成绩优良，2.有明确的转专业理由，3.通过目标专业的考核。申请流程包括：提交申请表、院系审核、学校批准等步骤。",
       "category": "转专业",
       "publish_date": "2024-09-01",
       "qwen_score": 8.2
     }
   ]
   ```

2. **数据质量报告**: `reports/data_quality_report.md`
   - 筛选前后数据对比统计
   - 6维度评分分布图表
   - 重复率分析和去重日志
   - 质量问题识别和处理记录

3. **数据处理脚本**: `scripts/data_processing/`
   - `qwen_scorer.py` - Qwen评分系统
   - `deduplication.py` - 去重处理脚本
   - `attachment_extractor.py` - 附件信息提取脚本
   - `data_splitter.py` - 双数据集分离脚本
   - `link_validator.py` - 附件链接验证脚本
   - `data_validator.py` - 数据验证脚本
   - `config.yaml` - 配置文件

4. **API调用日志**: `logs/qwen_api_calls.log`
   - 每次API调用记录
   - 成本统计和额度使用情况

**文件存放规范**:
- 所有脚本放在: `scripts/data_processing/`
- 处理后数据放在: `data/processed/`
- 测试文件放在: `tests/unit/data_processing/`
- 日志文件放在: `logs/data_processing.log`

**验收检查点**:
- Day 2: Qwen API环境配置完成
- Day 3: 数据筛选算法开发完成
- Day 4: 高质量数据输出完成

#### 2. 数据科学专家 🆕
**专业领域**: 数据分析 + 质量验证
**RACI角色**: C(咨询者) - 为数据处理专家提供专业建议和独立验证

**核心职责**:
- 独立验证数据处理专家的筛选结果
- 数据分布分析和统计建模
- 质量评估指标设计和监控
- 数据偏差检测和纠正建议

**技能要求**:
- 统计学和数据科学理论
- Python数据分析（matplotlib, seaborn, scipy）
- 机器学习评估方法
- 数据可视化和报告生成

**具体交付物**:
1. **独立验证报告**: `reports/data_science_validation.md`
   - 对数据处理专家结果的独立验证
   - 抽样检验结果（至少100条数据）
   - 评分一致性分析
   - 质量问题发现和建议

2. **数据分析可视化**: `analysis/data_visualization/`
   - `score_distribution.png` - 6维度评分分布图
   - `category_analysis.png` - 8个分类数据分布
   - `quality_trends.png` - 数据质量趋势分析
   - `correlation_matrix.png` - 评分维度相关性分析

3. **质量监控仪表板**: `dashboard/quality_monitor.html`
   - 实时数据质量指标展示
   - 异常数据预警机制
   - 评分分布动态图表

4. **统计分析脚本**: `scripts/data_analysis/`
   - `statistical_analysis.py` - 统计分析主脚本
   - `visualization.py` - 可视化生成脚本
   - `quality_metrics.py` - 质量指标计算

**文件存放规范**:
- 分析脚本放在: `scripts/data_analysis/`
- 可视化文件放在: `analysis/data_visualization/`
- 报告文件放在: `reports/data_science_validation.md`
- 测试文件放在: `tests/unit/data_analysis/`

**验收检查点**:
- Day 3: 数据质量验证方法确定
- Day 4: 独立验证报告完成
- Day 5: 质量监控系统上线

#### 3. 问答生成专家
**专业领域**: NLP + 内容生成
**RACI角色**: R(执行者) - 问答对生成的主要执行者

**核心职责**:
- 基于**微调训练数据集**（纯文本）设计问答生成策略
- 批量生成约2500个高质量问答对（不包含附件链接）
- 质量评分和多样性控制（覆盖8个教务分类）
- 训练数据格式化和验证
- 确保问答内容完整性（即使没有附件链接也能回答核心问题）

**技能要求**:
- NLP和Prompt Engineering
- 大语言模型API调用
- 文本质量评估方法
- 数据格式转换和验证

**具体交付物**:
1. **训练数据集**: `data/training/qa_dataset.jsonl`
   ```json
   {"instruction": "如何进行2024-2025学年的选课？", "input": "", "output": "根据教务处通知，选课时间为...", "source_id": "ustb_001", "category": "选课", "quality_score": 0.85}
   {"instruction": "USTB学分要求是什么？", "input": "", "output": "根据学校规定，本科生需要完成...", "source_id": "ustb_002", "category": "学分", "quality_score": 0.82}
   ```

2. **质量评估报告**: `reports/qa_quality_report.md`
   - 2500个问答对的质量分布统计
   - 8个分类的覆盖情况分析
   - 问题类型多样性分析
   - 人工抽检结果（10%抽检）

3. **生成脚本和配置**: `scripts/qa_generation/`
   - `qa_generator.py` - 问答生成主脚本
   - `quality_evaluator.py` - 质量评估脚本
   - `prompt_templates.yaml` - 生成提示词模板
   - `generation_config.json` - 生成参数配置

4. **验证数据集**: `data/validation/qa_validation.json`
   - 人工验证的高质量问答对样本
   - 用于模型训练效果验证

**文件存放规范**:
- 生成脚本放在: `scripts/qa_generation/`
- 训练数据放在: `data/training/qa_dataset.jsonl`
- 验证数据放在: `data/evaluation/qa_validation.json`
- 测试文件放在: `tests/unit/qa_generation/`

**验收检查点**:
- Day 5: 问答生成策略确定
- Day 6: 批量生成系统开发完成
- Day 7: 问答对生成和验证完成

### 💻 开发层专家（3个）

#### 4. RAG系统专家
**专业领域**: 向量检索 + 后端开发
**RACI角色**: R(执行者) - RAG系统开发的主要执行者

**核心职责**:
- Qdrant向量数据库部署和配置
- BCE-embedding-base_v1嵌入模型集成
- 基于**RAG检索数据集**（包含附件链接）构建向量索引
- 语义检索+关键词过滤系统开发
- **附件信息检索**：确保检索结果包含相关附件链接
- 检索性能优化和API接口开发

**技能要求**:
- Qdrant向量数据库管理
- 向量嵌入和相似度计算
- Python后端开发（FastAPI/Flask）
- 检索算法优化

**具体交付物**:
1. **RAG系统服务**: `services/rag_system/`
   - `app.py` - FastAPI主服务
   - `vector_store.py` - Qdrant向量数据库操作
   - `embedding_service.py` - BCE嵌入模型服务
   - `retrieval_engine.py` - 检索引擎核心逻辑
   - `requirements.txt` - 依赖包列表

2. **API接口文档**: `docs/rag_api.md`
   ```python
   # 检索接口
   POST /api/v1/search
   {
     "query": "如何选课",
     "top_k": 5,
     "category_filter": ["选课"],
     "date_range": ["2024-01-01", "2024-12-31"]
   }

   # 响应格式
   {
     "results": [
       {
         "id": "ustb_001",
         "title": "转专业申请通知",
         "content": "...",
         "score": 0.85,
         "category": "转专业",
         "url": "https://jwc.ustb.edu.cn/notice/001",
         "attachments": [
           {
             "name": "转专业申请表.docx",
             "url": "https://jwc.ustb.edu.cn/files/transfer_form.docx",
             "type": "application/docx"
           }
         ]
       }
     ],
     "total": 5,
     "response_time": 245
   }
   ```

3. **向量数据库**: `data/vectors/`
   - Qdrant数据库文件
   - 向量索引配置
   - 备份和恢复脚本

4. **性能测试报告**: `reports/rag_performance.md`
   - Recall@5测试结果
   - 响应时间基准测试
   - 并发性能测试结果

**文件存放规范**:
- 服务代码放在: `src/services/rag_system/`
- 向量数据放在: `data/vectors/`
- API文档放在: `docs/api/rag_api.md`
- 测试文件放在: `tests/integration/rag_system/`

**验收检查点**:
- Day 6: Qdrant环境部署完成
- Day 7: 检索系统开发完成
- Day 8: 性能优化和测试完成

#### 5. Web前端专家 🆕
**专业领域**: 前端开发 + 用户体验
**RACI角色**: R(执行者) - 前端界面开发的主要执行者

**核心职责**:
- React/Vue现代化前端界面开发
- 响应式设计和移动端适配
- 用户体验优化和交互设计
- 前端性能优化和测试

**技能要求**:
- React/Vue前端框架
- 响应式设计和CSS
- 用户体验设计
- 前端性能优化

**具体交付物**:
1. **前端应用**: `frontend/`
   - `src/` - React/Vue源代码
   - `public/` - 静态资源文件
   - `package.json` - 依赖和脚本配置
   - `dist/` - 构建后的生产版本

2. **核心页面组件**:
   - `ChatInterface.vue` - 主聊天界面组件
   - `SearchResults.vue` - 搜索结果展示组件
   - `CategoryFilter.vue` - 分类筛选组件
   - `MobileLayout.vue` - 移动端布局组件

3. **API集成配置**: `src/api/`
   - `ragApi.js` - RAG系统API调用
   - `backendApi.js` - 后端服务API调用
   - `config.js` - API配置和环境变量

4. **响应式测试报告**: `reports/frontend_testing.md`
   - 桌面端兼容性测试（Chrome, Firefox, Safari）
   - 移动端适配测试（iOS, Android）
   - 性能测试结果（加载时间、交互响应）
   - 用户体验测试反馈

**文件存放规范**:
- 前端代码放在: `src/frontend/`
- 静态资源放在: `src/frontend/public/`
- 构建输出放在: `src/frontend/dist/`
- 测试文件放在: `tests/e2e/frontend/`

**验收检查点**:
- Day 6: 前端框架搭建完成
- Day 7: 核心界面开发完成
- Day 8: 响应式适配和优化完成

#### 6. Web后端专家
**专业领域**: 后端开发 + API设计
**RACI角色**: R(执行者) - 后端API开发的主要执行者

**核心职责**:
- Flask/FastAPI后端API开发
- 业务逻辑实现和数据库设计
- API接口规范制定和文档
- 后端性能优化和安全控制

**技能要求**:
- Python后端开发
- API设计和RESTful规范
- 数据库设计和优化
- 安全认证和权限控制

**具体交付物**:
1. **后端服务**: `backend/`
   - `app.py` - Flask/FastAPI主应用
   - `models/` - 数据模型定义
   - `routes/` - API路由处理
   - `middleware/` - 中间件（认证、日志等）
   - `requirements.txt` - Python依赖包

2. **API接口实现**:
   ```python
   # 主要API端点
   POST /api/v1/chat          # 聊天对话接口
   GET  /api/v1/categories    # 获取分类列表
   POST /api/v1/feedback      # 用户反馈接口
   GET  /api/v1/health        # 健康检查接口
   ```

3. **数据库设计**: `database/`
   - `schema.sql` - 数据库表结构
   - `migrations/` - 数据库迁移脚本
   - `seeds/` - 初始数据
   - `backup_scripts/` - 备份脚本

4. **API文档**: `docs/backend_api.yaml`
   - OpenAPI 3.0规范文档
   - 接口参数和响应格式详细说明
   - 错误码定义和处理说明

5. **集成测试套件**: `tests/`
   - `test_api.py` - API接口测试
   - `test_integration.py` - 与RAG系统集成测试
   - `test_performance.py` - 性能基准测试

**文件存放规范**:
- 后端代码放在: `src/backend/`
- 数据库脚本放在: `src/backend/database/`
- API文档放在: `docs/api/backend_api.yaml`
- 测试文件放在: `tests/integration/backend/`

**验收检查点**:
- Day 6: 后端框架搭建完成
- Day 7: 核心API开发完成
- Day 8: 集成测试和优化完成

### 🔧 集成层专家（2个）

#### 7. 模型训练专家
**专业领域**: 深度学习 + 模型优化
**RACI角色**: R(执行者) - 模型训练的主要执行者

**核心职责**:
- RTX 4090 + Unsloth环境配置
- DeepSeek-R1-Distill-Llama-8B LoRA微调
- 训练过程监控和超参数调优
- 模型性能评估和优化

**技能要求**:
- PyTorch深度学习框架
- LoRA微调技术
- 模型训练和优化
- GPU计算和性能调优

**具体交付物**:
1. **训练好的模型**: `models/trained/`
   - `adapter_model.bin` - LoRA适配器权重
   - `adapter_config.json` - LoRA配置文件
   - `tokenizer/` - 分词器文件
   - `training_args.json` - 训练参数记录

2. **训练脚本**: `scripts/training/`
   - `train_model.py` - 主训练脚本
   - `data_loader.py` - 数据加载器
   - `evaluation.py` - 模型评估脚本
   - `config.yaml` - 训练配置文件

3. **训练报告**: `reports/training_report.md`
   - 训练过程详细记录（loss曲线、学习率变化）
   - 模型性能评估结果
   - 准确率测试（>85%目标验证）
   - 推理速度基准测试（<2秒验证）
   - GPU使用情况和训练时间统计

4. **模型部署包**: `deployment/model/`
   - `inference_server.py` - 推理服务器
   - `model_loader.py` - 模型加载器
   - `Dockerfile` - 容器化部署文件
   - `requirements.txt` - 推理环境依赖

5. **评估数据集**: `data/evaluation/`
   - `test_set.json` - 测试数据集
   - `evaluation_results.json` - 评估结果详情

**文件存放规范**:
- 训练脚本放在: `scripts/training/`
- 模型文件放在: `models/trained/`
- 训练报告放在: `reports/training_report.md`
- 测试文件放在: `tests/unit/model_training/`

**验收检查点**:
- Day 9: 训练环境配置完成
- Day 10: 模型训练执行完成
- Day 11: 模型评估和优化完成

#### 8. 系统集成专家
**专业领域**: DevOps + 系统集成
**RACI角色**: R(执行者) - 系统集成的主要执行者

**核心职责**:
- RAG+Web+微调模型的系统整合
- **混合回答机制**：微调模型生成基础回答 + RAG系统提供附件链接
- 端到端功能测试（包括附件链接有效性测试）
- 部署环境配置和监控系统
- 完整系统的交付和文档

**技能要求**:
- 系统集成和DevOps
- 容器化部署（Docker）
- 系统监控和日志管理
- 自动化测试和CI/CD

**具体交付物**:
1. **完整系统**: `system/`
   - `docker-compose.yml` - 完整系统编排
   - `nginx.conf` - 反向代理配置
   - `env/` - 环境配置文件
   - `scripts/deploy.sh` - 一键部署脚本

2. **集成测试套件**: `tests/integration/`
   - `test_e2e.py` - 端到端功能测试
   - `test_performance.py` - 系统性能测试
   - `test_load.py` - 负载测试
   - `test_stability.py` - 稳定性测试

3. **监控系统**: `monitoring/`
   - `prometheus.yml` - 监控配置
   - `grafana/dashboards/` - 监控仪表板
   - `alerts.yml` - 告警规则配置
   - `log_config.yaml` - 日志配置

4. **部署文档**: `docs/deployment/`
   - `deployment_guide.md` - 部署指南
   - `system_architecture.md` - 系统架构说明
   - `troubleshooting.md` - 故障排除手册
   - `maintenance_guide.md` - 运维手册

5. **系统验收报告**: `reports/system_acceptance.md`
   - 端到端功能测试结果
   - 性能基准测试报告
   - 稳定性测试报告（99%可用性验证）
   - 安全性测试结果
   - 用户验收测试反馈

6. **生产环境配置**: `production/`
   - 生产环境部署配置
   - 数据库连接配置
   - 安全证书和密钥管理
   - 备份和恢复策略

**文件存放规范**:
- 系统配置放在: `system/`
- 部署脚本放在: `deployment/scripts/`
- 集成测试放在: `tests/integration/system/`
- 验收报告放在: `reports/system_acceptance.md`

**验收检查点**:
- Day 12: 系统集成完成
- Day 13: 端到端测试完成
- Day 14: 部署和文档完成

## 🔗 专家交付物联动关系

### 关键接口和数据流转
```
                    数据处理专家
                         ↓
              ┌─────────────────────┐
              │                     │
    training_data.json      rag_data.json
         (纯文本)            (含附件链接)
              │                     │
              ↓                     ↓
        问答生成专家              RAG系统专家
              │                     │
              ↓                     ↓
        qa_dataset.jsonl      检索API接口
              │              (含附件信息)
              ↓                     │
        模型训练专家                 │
              │                     │
              ↓                     ↓
        微调模型              Web后端专家 ← API集成
              │                     ↓
              └─────→ Web前端专家 ← 接口调用
                          ↓
                    系统集成专家
                 (整合微调+RAG+附件)
```

### 标准化接口规范
1. **数据格式标准**: 所有JSON文件必须包含id、timestamp、source等标准字段
2. **API接口标准**: 统一使用RESTful API，返回格式标准化
3. **文件命名规范**: 按照`{专家角色}_{交付物类型}_{版本号}`格式命名
4. **文档格式标准**: 所有报告使用Markdown格式，包含标准的元数据头部

## 📁 项目文件夹结构规范

### 完整目录结构
```
USTB-AI-Assistant/
├── 📋 docs/                           # 项目文档
│   ├── project/                       # 项目管理文档
│   ├── technical/                     # 技术文档
│   ├── api/                          # API文档
│   └── deployment/                    # 部署文档
├── 📊 data/                           # 数据文件
│   ├── raw/                          # 原始数据
│   │   └── 全部原始数据/              # 4180条原始数据
│   ├── processed/                     # 处理后数据
│   │   ├── rag_data.json             # RAG检索数据集(含附件)
│   │   └── training_data.json        # 微调训练数据集(纯文本)
│   ├── training/                      # 训练数据
│   │   └── qa_dataset.jsonl          # 问答对数据集
│   ├── evaluation/                    # 评估数据
│   └── vectors/                       # 向量数据库文件
├── 🔧 scripts/                        # 脚本文件
│   ├── data_processing/               # 数据处理脚本
│   ├── qa_generation/                 # 问答生成脚本
│   ├── training/                      # 模型训练脚本
│   └── deployment/                    # 部署脚本
├── 🏗️ src/                           # 源代码
│   ├── backend/                       # 后端代码
│   │   ├── app.py                    # 主应用
│   │   ├── models/                   # 数据模型
│   │   ├── routes/                   # API路由
│   │   └── middleware/               # 中间件
│   ├── frontend/                      # 前端代码
│   │   ├── src/                      # 源码
│   │   ├── public/                   # 静态资源
│   │   └── dist/                     # 构建输出
│   └── services/                      # 服务层
│       ├── rag_system/               # RAG系统
│       └── model_inference/          # 模型推理
├── 🧪 tests/                         # 测试文件 (重要!)
│   ├── unit/                         # 单元测试
│   ├── integration/                  # 集成测试
│   ├── e2e/                         # 端到端测试
│   ├── performance/                  # 性能测试
│   ├── data/                        # 测试数据
│   │   ├── mock_data.json           # 模拟数据
│   │   └── test_samples.json        # 测试样本
│   └── temp/                        # 临时测试文件
├── 🤖 models/                        # 模型文件
│   ├── trained/                      # 训练好的模型
│   ├── checkpoints/                  # 训练检查点
│   └── configs/                      # 模型配置
├── 📈 reports/                       # 报告文件
│   ├── data_quality_report.md        # 数据质量报告
│   ├── training_report.md            # 训练报告
│   └── system_acceptance.md          # 系统验收报告
├── 📊 analysis/                      # 分析文件
│   ├── data_visualization/           # 数据可视化
│   └── performance_analysis/         # 性能分析
├── 🔧 configs/                       # 配置文件
│   ├── development.yaml              # 开发环境配置
│   ├── production.yaml               # 生产环境配置
│   └── testing.yaml                  # 测试环境配置
├── 📋 logs/                          # 日志文件
│   ├── application.log               # 应用日志
│   ├── error.log                     # 错误日志
│   └── qwen_api_calls.log           # API调用日志
├── 🐳 deployment/                    # 部署相关
│   ├── docker/                       # Docker文件
│   ├── kubernetes/                   # K8s配置
│   └── scripts/                      # 部署脚本
├── 📦 system/                        # 系统集成
│   ├── docker-compose.yml           # 系统编排
│   ├── nginx.conf                    # 反向代理配置
│   └── monitoring/                   # 监控配置
└── 🔄 temp/                          # 临时文件 (重要!)
    ├── downloads/                     # 临时下载
    ├── uploads/                       # 临时上传
    ├── cache/                         # 缓存文件
    └── scratch/                       # 草稿文件
```

### 🚨 关键规则
1. **测试文件严格分离**: 所有测试相关文件必须放在 `tests/` 目录下
2. **临时文件统一管理**: 所有临时文件放在 `temp/` 目录，定期清理
3. **环境配置分离**: 开发、测试、生产环境配置严格分离
4. **日志文件集中**: 所有日志统一放在 `logs/` 目录
5. **文档分类管理**: 项目文档、技术文档、API文档分类存放

## 🔄 专家协作流程

### 时间线和依赖关系
```
Day 1-3: 数据处理专家 → 输出原始筛选数据
Day 2-4: 数据科学专家 → 验证和优化数据质量 (并行)
Day 4-6: 问答生成专家 → 输出训练数据集
Day 5-8: RAG系统专家 ∥ Web前端专家 ∥ Web后端专家 (三并行)
Day 9-11: 模型训练专家 → 输出微调模型
Day 11-14: 系统集成专家 → 输出完整系统
```

### RACI责任矩阵
| 任务/专家 | 数据处理 | 数据科学 | 问答生成 | RAG系统 | Web前端 | Web后端 | 模型训练 | 系统集成 | 项目经理 |
|----------|---------|---------|---------|---------|---------|---------|---------|---------|---------|
| 数据筛选 | R | C | I | I | I | I | I | I | A |
| 质量验证 | I | R | C | I | I | I | I | I | A |
| 问答生成 | I | C | R | I | I | I | I | I | A |
| RAG开发 | I | I | I | R | C | C | I | I | A |
| 前端开发 | I | I | I | C | R | C | I | I | A |
| 后端开发 | I | I | I | C | C | R | I | I | A |
| 模型训练 | I | I | C | I | I | I | R | I | A |
| 系统集成 | I | I | I | C | C | C | C | R | A |

**RACI说明**:
- R(Responsible): 执行者 - 负责完成任务
- A(Accountable): 负责者 - 对结果负责（项目经理）
- C(Consulted): 咨询者 - 提供专业建议
- I(Informed): 知情者 - 需要了解进展

## 📊 质量控制体系

### 验收标准
每个专家的交付物都必须通过以下验收：
1. **功能验收**: 满足技术规格要求
2. **性能验收**: 达到性能指标标准
3. **质量验收**: 通过代码审查和测试
4. **文档验收**: 提供完整的技术文档

### 风险管控
- **技术风险**: 每个专家都有备选技术方案
- **时间风险**: 关键路径监控，及时调整资源
- **质量风险**: 双重验证机制，确保交付质量
- **协作风险**: 每日同步会议，及时解决协调问题

---

**文档维护**: 本文档由项目经理梁晓阳维护，每日更新专家进展状态
**最后更新**: 2025-08-01 17:30
**下次更新**: 2025-08-02 17:00
