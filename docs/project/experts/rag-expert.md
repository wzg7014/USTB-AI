# RAG 专家｜任务执行文档（统筹 v2.0 重构版）

## 1. 基本信息
- 专家：rag-expert
- 统筹版本：v2.0（重构版）
- 关联文档：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 建立稳定的“检索→重排→生成→后处理”链路，生成阶段仅使用检索上下文。
- 回答尾部必须列出 Top-K 文档（标题+URL）；`ChatResponse.rag_results` 必须非空；空召回给出改写建议。
- 数据仅保留近 3 年，时间字段准确；索引使用稳定 doc_id/哈希，避免覆盖/冲突。

## 3. 依赖与输入
- 来自数据治理（data-governance-expert）的清洗数据与报告：
  - data/governance/reports/data_quality_report.md（需通过）
  - 近 3 年数据集；缺失时间已纠偏
- 配置环境变量：`RAG_API_URL`、`CACHE_TTL`、`SIMILARITY_THRESHOLD`、`TOP_K`、`MIN_CONFIDENCE`
- 外部/本地 Qdrant 集合：`ustb_documents`（vector_size=768，COSINE）

## 4. 输出与落点
- 代码：
  - src/services/rag_system/retrieval_engine.py（检索/重排/融合/后处理）
  - src/backend/routes/chat.py（组合上下文、降级策略、OpenAI兼容层对接）
- 测试：tests/integration/rag_flow.test.ts（或 .py）
- 日志：logs/rag_flow/*.log（含 request_id 全链路）
- 评测报告（P1.5）：tests/reports/M2_lc_eval.json

## 5. 执行SOP（P0 合规与统一）

### 5.1 AutoDL环境操作（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL（请使用密钥或环境变量注入，禁止明文）
ssh -p <PORT> <USER>@<HOST>

# 2. 进入项目目录
cd /root/autodl-tmp/ustb-project/

# 3. 激活unsloth环境
source /root/miniconda3/bin/activate unsloth

# 4. 确认Python路径
which python  # 期望: /root/miniconda3/envs/unsloth/bin/python
```

**RAG服务启动（AutoDL端口8000）**
```bash
# 1. 进入RAG服务目录
cd /root/autodl-tmp/ustb-project/services/rag_system/

# 2. 启动RAG服务
/root/miniconda3/envs/unsloth/bin/python app.py

# 3. 验证服务状态
curl http://localhost:8000/health
```

**本地SSH隧道配置（统一端口）**
```powershell
# 在本地PowerShell中建立隧道（RAG服务 8000）
ssh -p <PORT> -L 8000:localhost:8000 <USER>@<HOST>
```

### 5.2 本地环境配置
1) 环境与配置
- [ ] 清理本地硬编码；仅通过 `.env` 设置 `RAG_API_URL=http://localhost:8000` 等参数
- [ ] 确认 Qdrant 集合存在、向量维度与度量一致

2) 检索与重排
- [ ] retrieval_engine.search：支持 `top_k`、`category_filter`、`date_range`、`similarity_threshold`
- [ ] 候选数≥2*top_k；重排：相似度(0.6)+关键词(0.3)+质量(0.1)

3) 生成与后处理
- [ ] 生成阶段只注入检索上下文；PromptTemplate 禁止“无依据生成”
- [ ] 后处理：文本末尾列出附件与链接；空召回给出改写建议

4) 路由整合（chat）
- [ ] `/v1/chat/completions` 非流：整合 RAG 结果与文本
- [ ] Hybrid 不可用→自动降级 RAG，并在响应内标记 `degraded: true`

5) 日志打点（JSON）
- [ ] request_received、retrieval_started/finished、rerank_finished、generate_finished、postprocess_finished、response_sent
- [ ] 字段：request_id、latency_ms、top_k、hit_count、attachments_count、upstream_status

6) 自测与断言
**AutoDL环境测试**
- [ ] AutoDL RAG服务健康检查：`curl http://localhost:8000/health`
- [ ] AutoDL RAG搜索测试：`curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d "{\"query\":\"选课\",\"top_k\":3}"`

**本地环境测试（通过SSH隧道）**
- [ ] `curl -X POST http://localhost:8001/api/v1/search -H "Content-Type: application/json" -d "{\"query\":\"选课\",\"top_k\":3}"`
- [ ] `curl -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"ustb-rag-assistant\",\"messages\":[{\"role\":\"user\",\"content\":\"我要选课时间\"}],\"stream\":false}"`
- [ ] 断言：rag_results 非空；文本尾部包含 ≥1 个 http(s) 链接；日志可按 request_id 串起全链路

## 6. 验收标准（P0）
- 功能：检索→重排→生成→后处理链路稳定；空召回给出改写建议
- 数据：search 结果 `publish_date` 均在近 3 年
- 日志：覆盖率≥95%，5xx 含上游状态与降级决策
- 合同：`/v1/chat/completions` 返回体含 `rag_results` 与附件链接

## 7. LangChain 最小链路（P1.5）
- 组件：Retriever → Reranker → PromptTemplate → LLM（Qwen）
- 指标：召回@k、NDCG、回答置信度、端到端延迟
- 产物：tests/performance/lc_eval.*、tests/reports/M2_lc_eval.json

## 8. 配置参数建议（可按环境覆盖）
- TOP_K：5（P0），可根据延迟调优
- SIMILARITY_THRESHOLD：0.3（检索）/ 0.6（语义）
- CACHE_TTL：1800s（检索结果），7200s（向量化查询）
- MIN_CONFIDENCE：0.7（低于则提示核验）

## 9. 风险与回滚
- 隧道/网络不稳 → 默认直连 RAG，Hybrid 降级
- 质量下降 → 临时白名单补偿；回滚至上一个稳定版本
- 日志量大 → 采样/分级；日志轮转

## 10. 步骤记录（逐步填写，带时间戳）
### 步骤N（YYYY-MM-DD HH:mm）
- 目标：
- 操作（含联网检索要点）：
- 产物路径：
- 接口/配置变更：
- 日志关键ID/截图：
- 风险与回滚：

## 11. 阶段小结
- 完成项：
- 待办与风险：

---

## 附录A｜请求/响应契约片段
### /api/v1/search 请求
```json
{ "query":"选课", "top_k":5, "date_range": {"since":"2022-09-01"}}
```
### /v1/chat/completions 响应片段
```json
{
  "choices":[{"message":{"content":"...\n\n参考：1) 标题A URL1 2) 标题B URL2"}}],
  "rag_results":[{"title":"标题A","url":"https://..."}],
  "request_id":"${uuid}"
}
```

## 附录B｜调参建议
- rerank 权重：相似度0.6 / 关键词0.3 / 质量0.1
- top_k：5 起步，观察 P95 与命中率权衡
- similarity_threshold：0.3-0.6 区间

## 附录C｜PowerShell 验收命令
```powershell
curl.exe -X POST http://localhost:8001/api/v1/search -H "Content-Type: application/json" -d '{"query":"选课","top_k":3}'
curl.exe -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"ustb-rag-assistant","messages":[{"role":"user","content":"我要选课时间"}],"stream":false}'
```

## 附录D｜回滚与降级
- 命中率异常下降：切回上一个索引快照；放宽阈值并记录原因
- 上游不稳：禁用 Hybrid，直连 RAG；响应体携带 degraded:true
