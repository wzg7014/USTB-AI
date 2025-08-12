## USTB AI教务助手 - 技术实现方案（第二阶段 / 企业级升级版）

### 1. 概述

- 目标：在不破坏现有使用体验的前提下，将系统升级为企业级可运维、可观测、可回滚的架构形态；对外保持统一契约，对内引入编排、网关与治理能力。
- 范围：后端 API 聚合与编排、RAG 质量与稳定、模型网关与重排、可观测与安全、CI/CD 与容器化、K8s 与 API 网关。
- 与第一阶段对比（升级点）：
  - 从“直连 RAG/模型”→“统一 `/api/v1/answer` 聚合契约 + 薄编排（LangGraph）”。
  - 从“硬编码与分散配置”→“12-Factor 环境变量 + 特性开关矩阵（Feature Flags）”。
  - 从“有限日志”→“指标/追踪/结构化日志三位一体（Prometheus + OpenTelemetry + JSON Logs）”。
  - 从“单点直连模型”→“LiteLLM 模型网关（限流/审计/重试/多厂商 Key 轮换）”。
  - 从“本机手动起服务”→“容器化 + Compose 一键起 + CI/CD 安全门禁 + K8s 与 API 网关”。

### 2. 目标架构（分层）

- API 层（FastAPI）：路由/鉴权/限流/审计/可观测；统一对外接口 `/api/v1/answer`。
- 编排层（LangGraph 薄编排，可回退 LangChain/INLINE）：状态清晰、节点可观测，承载“规范化→RAG→后处理→重排→总结→格式化→降级”。
- RAG 层（沿用现有 Qdrant + BCE/BGE 嵌入 + 缓存/增强）：对外 REST，按统一口径提供检索能力与质量。
- 模型网关（LiteLLM 或直连）：统一多厂商、限流/重试/审计；按开关选择网关或直连。
- 可观测性（Prometheus/OTel/结构化日志）：指标 + Trace + JSON 日志三位一体，问题可回溯与容量规划可量化。
- 安全与治理（Secrets 管理/PII 脱敏/内容安全/CORS 白名单）：满足企业安全与合规要求。

### 3. 统一聚合接口（/api/v1/answer）

- 方法：`POST /api/v1/answer`
- 请求体（核心字段）：`query`、`top_k`、`category_filter`、`date_range`、`flags`（策略透传：`use_rerank`、`α/τ`、`context_tokens`、`temperature/max_tokens` 等）
- 响应体（合同化）：
  - `answer`: 严格模板（先结论→要点→注意事项→参考文献）
  - `citations[]`: ≤5，包含 `id/title/url/publish_date/snippet/score`
  - `attachments[]`: 链接 HEAD 校验通过的附件
  - `meta`: `request_id/degrade/cached/rag_latency_ms/model_latency_ms/total_latency_ms/params/version`
- 错误：统一 `status/code/message/request_id`，可观测时关联 TraceId。

### 4. 编排设计（LangGraph 薄编排）

- 节点：`normalize` → `rag_search` → `postprocess`（去重/新鲜度/片段）→ `rerank`（可选 Cohere/Jina）→ `summarize`（模板）→ `format` → `degrade`（降级）。
- 可回退：`ORCH_ENGINE=LANGGRAPH|LANGCHAIN|INLINE`（默认 LangGraph）。
- Windows 友好：仅依赖 Py 包与 HTTP API，避免本地 Torch；重排优先外部 API。
- 统一治理：`httpx` 超时/重试/熔断；阶段耗时写入 `meta` 与指标。

### 5. RAG 质量策略

- 去重：URL 精确 + 标题相似（阈值≈0.9），只做一层（RAG 整形阶段）。
- 新鲜度：`score' = score · (1 + α · e^{-days/τ})`，通知 α∈[0.5,0.8]、τ∈[45,90]；规章 α∈[0.3,0.5]、τ∈[90,120]。
- 片段选取：句级抽取+滑窗，拼接 ≤ `CONTEXT_TOKENS`。
- 重排（可选一层）：Cohere/Jina Reranker API；失败回退原排序。
- 只允许单层重排 & 单处去重；后端缓存 60s；保持行为可解释与可回滚。

### 6. 模型网关（LiteLLM）

- 功能：多厂商 Key 轮换、限流、重试、审计、路由/聚合。
- 策略：
  - `USE_MODEL_GATEWAY=true` 走 LiteLLM（`LITELLM_BASE_URL/LITELLM_API_KEY`），`false` 走直连（`MODEL_BASE_URL/MODEL_API_KEY`）。
  - 失败自动重试与降级；稳定性优先。

### 7. 配置与开关（12-Factor）

- 模式与路由：`ANSWER_MODE={QUICK|CORE}`、`RAG_ENTRY={DIRECT_8000|HYBRID_8002}`、`MODEL_ENTRY={DIRECT|DISABLED}`。
- 编排与重排：`ORCH_ENGINE={LANGGRAPH|LANGCHAIN|INLINE}`、`USE_RERANK={true|false}`、`RERANK_PROVIDER={COHERE|JINA}`。
- 质量参数：`FRESHNESS_ALPHA/TAU_DAYS`、`CONTEXT_TOKENS`、`MODEL_TEMPERATURE/MODEL_MAX_TOKENS`、`MAX_CITATIONS`。
- 超时：`RAG_TIMEOUT_SEC=15`、`MODEL_TIMEOUT_SEC=30`。
- 端点：`RAG_API_URL/HYBRID_API_URL/LITELLM_BASE_URL/MODEL_BASE_URL`；认证：`*_API_KEY`；存储：`DATABASE_URL/REDIS_URL`。
- 观测：`OTEL_EXPORTER_OTLP_ENDPOINT`、`PROM_BIND_ADDR`；安全：`SECRET_KEY`。

### 8. 可观测性

- 指标（Prometheus `/metrics`）：`rag_latency_ms/model_latency_ms/total_latency_ms/rerank_latency_ms/error_rate/hit_at_3/cache_hit_ratio`。
- 追踪（OpenTelemetry）：根 span 绑定 `request_id/user_id/ANSWER_MODE/USE_RERANK`；子 span 覆盖全链路节点。
- 日志（JSON）：字段 `ts/level/request_id/user_id/endpoint/latency_ms/error_code/flags`；产线仅 JSON；可关联 TraceId。

### 9. 安全与合规

- 凭据管理：环境变量或 Secret 管理（Vault/KMS），仓库禁提交明文。
- 鉴权与限流：Bearer/JWT + slowapi（用户/IP/端点配额），熔断与重试统一。
- CORS 白名单；前端安全头（CSP/HSTS/Referrer-Policy）。
- PII 脱敏（邮箱/学号/手机号）；内容安全（NeMo Guardrails/厂商 Moderation 可选）。

### 10. CI/CD 与容器化

- 容器：多阶段 Dockerfile（非 root、只读 FS、健康检查）；`docker-compose` 一键起（后端+RAG+Redis/Qdrant 可选）。
- CI/CD：GitHub Actions（lint/test/build/publish）、安全扫描（`pip-audit/trivy`）、制品落库、版本与变更日志。

### 11. K8s 与 API 网关（可选）

- K8s：Deployment/Service/Ingress（或 Gateway），HPA 基于 Prom 或自定义指标，金丝雀/蓝绿发布，SLO + 告警。
- API 网关：Kong/Traefik/Envoy，提供统一入口、鉴权、配额、限流与可观测聚合。

### 12. 执行路径（D0 → D1 → D2）

- D0（1–2 天，最小闭环）：
  - 上线 `/api/v1/answer`，接入 LangGraph 薄编排，统一 `config.py` 与开关矩阵；新增 `/metrics` 与请求ID中间件；去硬编码；保留 8003 回滚。
  - 验收：接口契约稳定；指标可见；模型失败可降级（RAG 要点+引用）。
- D1（3–5 天，质量/鲁棒性增强）：
  - 引入 LiteLLM 网关、外部重排（Cohere/Jina）、完善 OTel Trace 与日志；A/B（USE_RERANK 与 α/τ 网格）。
  - 验收：`hit@3` 达到目标，trace 完整，回退可用。
- D2（5–10 天，工程化交付）：
  - 容器化 + compose + CI/CD；逐步迁移到 K8s 与 API 网关。
  - 验收：镜像扫描无高危、探针通过、HPA 生效、回滚一键完成。

### 13. 性能指标与 SLO/门禁

- 目标：`p95 total < 3s`（RAG≤800ms，模型≤2s）、错误率 < 1%，可用性 > 99%。
- 回归门禁：金标≥20，RAGAS/DeepEval 指标合格；A/B 报告覆盖 `USE_RERANK` 与 α/τ 网格；日志/Trace 无空洞。

### 14. 风险与回滚

- Torch 安装慢/兼容差：D1 使用外部重排 API，后续再考虑本地 bge。
- HYBRID/8003 不稳定：保留 `ANSWER_MODE=QUICK` 与 `RAG_ENTRY=HYBRID_8002` 回滚路径。
- 模型/第三方 API 波动：限流/重试/熔断 + 降级。
- 回滚方案：环境变量切换即可，严禁手动删改核心链路代码。

### 15. 运维手册（Runbook）

- 启动顺序：RAG(8000) → 后端(8001)。
- 健康检查：`/health`；指标：`/metrics`；OpenAPI：`/openapi.json`（产线禁 swagger 页面）。
- 常见操作：
  - 切换模式：`ANSWER_MODE=QUICK|CORE`
  - 切换编排：`ORCH_ENGINE=LANGGRAPH|LANGCHAIN|INLINE`
  - 开/关重排：`USE_RERANK=true|false`；选择重排器：`RERANK_PROVIDER=COHERE|JINA`
  - 走网关或直连：`USE_MODEL_GATEWAY=true|false`

—— 本方案与《系统整改方案_核心最小闭环.md》28–35 节对齐；当描述存在冲突时，以核心方案为准。


