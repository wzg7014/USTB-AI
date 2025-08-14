# USTB AI教务助手系统技术架构设计文档 v3.0

## 文档信息
- 文档版本：v3.0
- 编写日期：2025-08-13
- 技术专家：Technical Architect
- 项目代号：USTB-RAG-Architecture-Design
- 目标环境：AutoDL RTX 4090（本地/云均可部署）

---

## 一、概述与目标
- 业务目标：构建稳定、快速、可扩展的教务问答系统，支撑多渠道接入与持续演进。
- 技术目标：
  - 响应时间（P95）< 3s，错误率 < 1%，并发 50 用户稳定；
  - 检索精度（RAG）> 0.8；
  - 完整可观测性（日志/指标/追踪）与可降级架构；
  - 渐进式迁移与可回滚，保证线上稳定。

---

## 二、设计原则
- 简洁性优先：遵循奥卡姆剃刀，避免过度工程。
- 标准化优先：能用标准框架不自建；接口契约化、版本化。
- 可观测性内置：从第一天开始提供日志、指标与可追踪性。
- 渐进式升级：保持向后兼容，阶段推进，随时可回滚。

---

## 三、目标架构总览
```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                            │
│  Web前端(Next.js) → API网关(FastAPI) → 负载均衡         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  智能服务层                              │
│  LangChain Agent → Conversation Chain → RetrievalQA     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                  数据处理层                              │
│  文档加载器 → 质量过滤器 → 智能分块器 → 向量化处理       │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   存储层                                │
│  Qdrant向量库 → 关系型数据库（当前MySQL）→ Redis缓存     │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                 可观测性层                               │
│  结构化日志 → Prometheus指标 → LangSmith/OTel追踪 → 告警 │
└─────────────────────────────────────────────────────────┘
```

---

## 四、架构分层与核心组件

### 4.1 RAG Pipeline 标准化
查询处理：输入 → 预处理 → 检索 → 重排 → 生成 → 后处理 → 输出
- 查询预处理：意图识别、关键词提取、查询扩展
- 混合检索：向量检索 + 关键词检索 + 时间过滤
- 智能重排：相关性重排 + 多样性控制 + 质量分
- 上下文生成：检索结果整合，提示词构建
- 模型推理：Qwen2.5-7B-Instruct（可替换）
- 智能后处理：附件选择、格式化、质量校验

### 4.2 数据治理架构
数据生命周期：摄入 → 清洗 → 存储 → 更新 → 清理
- 清洗门槛：近3年有效数据；重复率 < 5%；字段完整性 > 90%
- 存储：Qdrant（向量）+ MySQL（元数据/日志/统计）+ 文件存储（原文/附件）
- 更新：增量更新、版本管理、索引重建；生成质量报告

### 4.3 统一 API 架构
- API 网关：统一入口、路由管理、版本控制、鉴权与限流
- 协议：RESTful API + WebSocket（可选）+ 流式SSE
- 版本策略：路径前缀或Header控制（预留 `X-API-Version`）

### 4.4 可观测性架构
- 日志：结构化JSON、分级；`X-Request-ID`贯穿全链路；日志脱敏
- 指标：请求量/耗时/错误率、下游健康、缓存命中率等；暴露 `/metrics`
- 追踪：LangSmith或OpenTelemetry可选；优先日志+指标

---

## 五、技术选型对比

### 5.1 RAG 框架
| 方案 | 优势 | 劣势 | 适用性 | 推荐度 |
|------|------|------|--------|--------|
| LangChain | 生态丰富、标准化、社区活跃 | 框架开销、学习曲线 | 高 | ⭐⭐⭐⭐⭐ |
| 自建 | 完全可控、性能可优化 | 开发成本高、维护难 | 中 | ⭐⭐ |
| LlamaIndex | 专注RAG、性能优秀 | 生态相对有限 | 中 | ⭐⭐⭐ |

结论：优先 LangChain，降低自建成本，利于演进。

### 5.2 向量数据库
| 方案 | 性能 | 易用性 | 生态 | 成本 | 推荐度 |
|------|------|--------|------|------|--------|
| Qdrant | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⭐⭐⭐⭐⭐ |
| Milvus | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐⭐ |
| Weaviate | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 付费 | ⭐⭐⭐ |

结论：继续使用 Qdrant（本地/服务化均可）。

### 5.3 大语言模型
| 方案 | 性能 | 中文能力 | 部署难度 | 成本 | 推荐度 |
|------|------|----------|----------|------|--------|
| Qwen2.5-7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⭐⭐⭐⭐⭐ |
| ChatGLM3-6B | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ⭐⭐⭐ |
| GPT-4 API | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐ |

结论：主推 Qwen2.5-7B（可量化/蒸馏），支持替换。

### 5.4 Web 框架
| 方案 | 性能 | 生态 | 学习成本 | 异步支持 | 推荐度 |
|------|------|------|----------|----------|--------|
| FastAPI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Django | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Flask | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

结论：继续使用 FastAPI。

---

## 六、配置与安全基线（更新：统一端口与脱敏）
- 环境变量白名单（后端核心）：`DATABASE_URL`、`RAG_API_URL`、`HYBRID_API_URL`、`SECRET_KEY`、`HOST`、`PORT`、`CORS_ORIGINS`、`LOG_LEVEL`、`REQUEST_TIMEOUT`、`CACHE_TTL`
- 端口规划（统一）：RAG 8000、LoRA 8001、Hybrid 8002、Web连接器 8003（前端 3000；Qdrant 6333；GPU 9100）
- 密钥管理：仓库禁明文；`.env.example` 仅示例键；生产用密管/平台注入
- 认证与限流：最小 JWT/访问码；`/api/v1/chat`、`/v1/chat/completions` 速率限制（429）
- CORS 与日志脱敏：白名单；过滤 `Authorization`、连接串等敏感字段

---

## 七、接口契约（OpenAI 兼容层）
- 路径：`/v1/models`、`/v1/chat/completions`（POST）；支持 `stream: true` SSE
- SSE 规范：
  - `data: { id, object:"chat.completion.chunk", delta:{ role?, content? }, finish_reason? }`
  - 结束：`data: [DONE]`
- 错误：4xx（参数/鉴权），5xx（下游/超时）；统一错误结构：
  - `{ "error": { "code": "UPSTREAM_TIMEOUT", "message": "...", "request_id": "..." } }`
- 版本：路径或Header（预留 `X-API-Version`）

---

## 八、可观测性最小可用集（状态：规范已提出，AutoDL 与后端待落地）
- 结构化日志：JSON；字段含 `timestamp, level, request_id, path, latency_ms, user_id, upstream_status`
- 请求ID：`X-Request-ID` 贯穿网关/后端/下游
- 指标 `/metrics`：
  - 计数器：`http_requests_total{path,status}`、`upstream_errors_total{service}`
  - 直方图：`http_request_duration_ms_bucket{path}`
  - Gauge：`cache_hit_ratio`、`external_health{service}`
- 追踪：LangSmith/OTel（可选，次于日志+指标）
 - 验收：四个服务至少 1 个计数器+1 个直方图；/metrics 可抓取；日志含 `X-Request-ID`

---

## 九、LangChain 落地蓝图（最小链路）
- 组件：Retriever（向量召回）→ Reranker（重排）→ PromptTemplate（上下文拼接）→ LLM（Qwen）
- 可替换点：检索策略（语义/混合）、重排算法（BM25/融合）、Prompt模板（领域可配置）
- 度量：召回@k、重排NDCG、回答置信度、端到端延迟

---

## 十、数据治理流水线与门槛
- 流程：摄入→清洗→存储→更新→清理；周期性版本化与索引重建
- 质量阈值：时效≥近3年；重复率<5%；字段完整性>90%
- 结果：质量报告（通过/未过项）；不达标不入库

---

## 十一、性能目标与 SLO/SLI
- 目标：P95 延迟 < 3s，错误率 < 1%，并发 50 用户稳定；检索精度 > 0.8
- 基准脚本：locust/k6 与固定检索集；固定数据量与并发模型
- 报告：输出前后对比（JSON/图表），记录 CPU/GPU/缓存命中率

---

## 十二、风险识别与缓解
- GPU 显存不足：量化/分时加载；指标触发预警
- 网络不稳：连接重试/本地缓存；超时降级与快速失败
- 依赖升级破坏：锁版本与回滚；变更前跑全量集成测试

---

## 十三、现状 → 目标差距映射（As-Is vs To-Be）
- 配置与安全：存在硬编码与凭据历史；→ 统一 `config.py`+`.env`，密钥仅环境注入，鉴权与限流上线
- 数据库与数据访问：代码以 MySQL 为主，仍残留 Mongo 聚合写法；→ 单一 MySQL 栈，移除 Mongo 痕迹，提供 SQL 聚合
- RAG/Hybrid 依赖：对 Hybrid URL 硬绑定；→ Hybrid 可选（默认直连 RAG），URL 配置化，稳定ID写入Qdrant
- 可观测性：缺少结构化日志、指标、追踪；→ JSON日志、`/metrics`、请求ID贯穿
- 接口契约：OpenAI 兼容层流/非流与错误结构不统一；→ 统一契约与错误体
- 版本与依赖：未锁定与缺包/重复包；→ 锁定关键依赖，安装一把过

---

## 十四、渐进式迁移路线图（As-Is → To-Be）
- 阶段 P0：合规与统一（1周）
  - 移除明文密钥、统一配置、去硬编码、单一DB栈、修复依赖（移除 motor、去重 httpx、加入 aiomysql）
  - 验收：`/health`、`/v1/models`、`/v1/chat/completions`、`/api/v1/search` 最小联通
- 阶段 P1：联通与契约（1周）
  - SSE 规范、统一错误体；Hybrid 可选，默认直连 RAG
  - 验收：前端无需改代码可对接；关闭 Hybrid 仍可用
- 阶段 P1.5：LangChain 最小接入（1周）
  - 最小链路与指标；检索精度≥0.75
- 阶段 P2：可观测性与性能（1周）
  - 日志+指标、SLO/SLI、缓存与降级、压测优化
  - 验收：P95<3s，错误率<1%，50并发稳定

降级与回滚（示意）：
```
Frontend → Backend → Hybrid(失败) → Backend → RAG(成功) → Frontend
响应附加：{"degraded": true}
```

---

## 十五、依赖版本与安装策略
- 后端：FastAPI/uvicorn/httpx/pydantic/aiomysql（或SQLAlchemy）锁主次版本；移除未用与重复包
- RAG：qdrant-client/sentence-transformers/torch 锁版本；提供 CPU 运行建议（小模型/低线程）
- 文件：分别维护 `requirements.txt` 与 `services/rag_system/requirements.txt`，保证安装一把过

---

## 十六、里程碑与交付
- 里程碑：P0（合规）→ P1（联通/契约）→ P1.5（LangChain）→ P2（可观测/性能）
- 交付物：代码变更、配置样例、测试/压测报告、风险评审记录
- 评审节奏：每阶段评审通过方可进入下一阶段；全程保留回滚方案

---

## 十七、结论
基于本方案，系统将从“能用”走向“稳定、可观测、可演进”。通过统一配置与契约、内置可观测性、渐进式迁移与回滚保障，配合 LangChain 标准化组件与严格的数据治理，目标性能与稳定性可达成，并为后续功能扩展与规模化部署提供坚实基础。

---

## 附录A：原则对齐与验收矩阵（针对当前关键5点）

### A.1 RAG 优先生成 + 附件/链接必备
- 机制：严格执行「检索→重排→生成→后处理」；生成阶段仅使用检索上下文；后处理强制拼接附件与来源链接。
- 模板约束：PromptTemplate 中要求引用 Top-K 文档，输出末尾列“相关文档（标题+URL）”。
- 验收：
  - 集成用例：对教务类查询，`ChatResponse.rag_results` 非空，且文本包含 ≥1 个 URL；
  - 空召回时返回友好提示并给出改写建议（不胡编）；
  - 指标：retrieval_hit_rate ≥ 0.9（在标注样本集上）。

### A.2 数据时效与时间准确性（仅保留近3年）
- 机制：摄入/更新时过滤 `publish_date >= now-3y`；缺失时间时进行正则解析与字段推断；计划任务定期清理与重建索引。
- DB/索引：Qdrant 仅保留近3年文档 payload；MySQL 保留清理日志与版本快照。
- 验收：
  - 统计：索引中文档 `publish_date` 均在近3年；
  - 用例：按时间过滤检索命中率正确；
  - 任务：清理/重建脚本可重复执行且幂等。

### A.3 日志可观测性（无日志 → 结构化日志）
- 机制：JSON 日志 + `X-Request-ID` 贯穿；关键阶段打点：`request_received`、`retrieval_started/finished`、`rerank_finished`、`generate_finished`、`postprocess_finished`、`response_sent`；外部依赖健康打点。
- 脱敏：过滤 Authorization、连接串、个人敏感信息。
- 验收：
  - 任一请求可在日志中按 `request_id` 还原全链路；
  - 5xx 时日志含上下游状态、耗时、降级决策；
  - 日志覆盖率≥95%。

### A.4 API 统一与有序收敛（API 混乱 → 契约化）
- 目录：仅暴露 `GET /v1/models`、`POST /v1/chat/completions`、`POST /api/v1/search`、`GET /api/v1/categories`、`POST/GET /api/v1/feedback`、`GET /health`、`GET /metrics`；其余路径标记弃用并给出迁移期（30天）。
- 契约：OpenAI SSE 规范与统一错误结构；版本通过路径/头管理。
- 验收：
  - 前端无需改代码可对接；
  - 旧路径返回 404/410 并附迁移指引；
  - 集成测试覆盖率≥90%。

### A.5 其他问题的治理（持续Backlog）
- 机制：变更评审+缺陷看板+SLO守护（错误率/延迟告警）；每次回归固定基准脚本与对比报告。
- 验收：
  - 每周关闭≥80%高优先级缺陷；
  - 关键接口 P95 < 3s、错误率 < 1% 持续达标；
  - 重大变更均附回滚方案与演练记录。

---

## 附录B：日志事件规范（最小集）
| 事件 | 级别 | 关键字段 |
|------|------|----------|
| request_received | info | request_id, path, user_id |
| retrieval_started/finished | info | request_id, top_k, hit_count, latency_ms |
| rerank_finished | debug | request_id, candidates, latency_ms |
| generate_finished | info | request_id, tokens, latency_ms |
| postprocess_finished | info | request_id, attachments_count, has_links |
| upstream_status | warn/error | service, status, timeout, retries |
| response_sent | info | request_id, status_code, total_latency_ms |

---

## 附录C：API 目录与弃用计划（摘要）
- 保留：
  - `GET /v1/models`
  - `POST /v1/chat/completions`（支持 `stream`）
  - `POST /api/v1/search`、`GET /api/v1/categories`、`POST/GET /api/v1/feedback`
  - `GET /health`、`GET /metrics`
- 弃用：其余历史路径（30天后移除）；统一返回 404/410 与迁移说明。