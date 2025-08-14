# API 网关专家｜任务执行文档（统筹 v2.0 重构版）

## 1. 基本信息
- 专家：api-gateway-expert
- 统筹版本：v2.0
- 关联：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 收敛 API 目录（保留清单），统一 OpenAI 兼容层契约（SSE/错误体/版本）。

## 3. 依赖与输入
- 设计契约：OpenAI 兼容接口（/v1/models、/v1/chat/completions）
- 配置：HOST/PORT、CORS_ORIGINS、REQUEST_TIMEOUT

## 4. 输出与落点
- 映射清单：docs/project/api-map.md
- 用例：tests/integration/api_contract.test.ts

## 5. 执行SOP（P0 & P1）

### 5.1 AutoDL环境操作（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL（请使用密钥或环境变量注入，禁止明文）
ssh -p <PORT> <USER>@<HOST>

# 2. 进入后端项目目录
cd /root/autodl-tmp/ustb-project/src/backend/

# 3. 激活unsloth环境
source /root/miniconda3/bin/activate unsloth

# 4. 启动API网关服务（示例端口）
/root/miniconda3/envs/unsloth/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8001
```

**本地SSH隧道配置（统一端口）**
```powershell
# 在本地PowerShell中建立隧道（API网关 8001）
ssh -p <PORT> -L 8001:localhost:8001 <USER>@<HOST>
```

**AutoDL环境验证**
```bash
# 在AutoDL上验证服务
curl http://localhost:8001/health
curl http://localhost:8001/v1/models
```

### 5.2 本地环境配置
1) 路由收敛（P0）
- [ ] 仅保留：/v1/models、/v1/chat/completions、/api/v1/search、/api/v1/categories、/api/v1/feedback、/health、/metrics
- [ ] 其它历史路径统一 404/410（响应内附迁移指引），保留 30 天

2) SSE 与错误体统一（P1）
- [ ] SSE：Content-Type:text/event-stream、Cache-Control:no-store、X-Accel-Buffering:no；标准 chunk；结尾 [DONE]
- [ ] 错误体：{ error:{ code, message, request_id } }
- [ ] 版本：路径或 Header（X-API-Version）

3) 鉴权与限流（可选最小版）
- [ ] 访问码/JWT、速率限制（429）

## 6. 验收标准
- API 白名单可用，黑名单路径 404/410
- SSE 正常分块并以 [DONE] 收束
- 错误体统一，含 request_id

## 7. 配置与风险
- CORS 白名单与端口冲突；Edge/代理中间层导致SSE断流（需禁用缓冲/编码冲突）

## 8. 步骤记录（YYYY-MM-DD HH:mm）
- 目标：
- 操作：
- 产物路径：
- 回滚：

## 9. 小结
- 完成项：
- 风险：

---

## 附录A｜接口契约与示例

### 1) GET /v1/models
- 请求：无体
- 响应（200）：
```json
{
  "object": "list",
  "data": [
    { "id": "ustb-rag-assistant", "object": "model" }
  ]
}
```

### 2) POST /v1/chat/completions（非流）
- 请求：
```json
{
  "model": "ustb-rag-assistant",
  "messages": [{"role":"user","content":"我要选课时间"}],
  "stream": false
}
```
- 响应（200 摘要）：
```json
{
  "id":"cmpl_xxx",
  "object":"chat.completion",
  "choices":[{"message":{"role":"assistant","content":"...\n\n参考：1) 标题A URL1 2) 标题B URL2"},"finish_reason":"stop","index":0}],
  "rag_results":[{"title":"标题A","url":"https://..."}],
  "request_id":"${uuid}"
}
```

### 3) POST /v1/chat/completions（SSE）
- 必备响应头：
  - Content-Type: text/event-stream
  - Cache-Control: no-store
  - X-Accel-Buffering: no
- 流格式：
```text
data: {"id":"cmpl_xxx","object":"chat.completion.chunk","choices":[{"delta":{"content":"段落1"},"index":0,"finish_reason":null}],"request_id":"${uuid}"}

data: {"id":"cmpl_xxx","object":"chat.completion.chunk","choices":[{"delta":{"content":"段落2"},"index":0,"finish_reason":null}]}

data: [DONE]
```

### 4) 统一错误体
```json
{
  "error": {
    "code": "BadRequest|Unauthorized|TooManyRequests|UpstreamError",
    "message": "人类可读的错误说明",
    "request_id": "${uuid}"
  }
}
```

### 5) 版本策略与头
- 版本：路径版 /v1/... 或 Header 版 X-API-Version: 1（二选一，优先 Header）
- 贯穿头：X-Request-ID（若请求未提供则服务端生成并回传）

---

## 附录B｜路由白/黑名单与映射
- 白名单（保留）：
  - GET /v1/models
  - POST /v1/chat/completions
  - POST /api/v1/search
  - GET /api/v1/categories
  - GET /api/v1/health 或 /health
  - GET /metrics
- 黑名单（弃用→404/410，30 天迁移期）：
  - 旧版 /chat、/completions、/search*（除 /api/v1/search）等历史路径
- 映射清单产出：docs/project/api-map.md（需在提交时同步更新）

---

## 附录C｜配置清单（环境变量）
- API_HOST, API_PORT
- CORS_ORIGINS（逗号分隔）
- REQUEST_TIMEOUT_MS（默认 60000）
- RATE_LIMIT_RPS（默认 10）
- JWT_SECRET（如启用鉴权）
- ENABLE_SSE=true（默认开启）

---

## 附录D｜验收步骤（Windows PowerShell）
- 注意：PowerShell 中 curl 是别名，需使用 curl.exe 或 iwr

1) models
```powershell
curl.exe http://localhost:8001/v1/models
```

2) chat 非流
```powershell
curl.exe -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"ustb-rag-assistant","messages":[{"role":"user","content":"我要选课时间"}],"stream":false}'
```

3) chat SSE（注意 -N）
```powershell
curl.exe -N -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"ustb-rag-assistant","messages":[{"role":"user","content":"我要选课时间"}],"stream":true}'
```

4) 错误体（示例 400）
```powershell
curl.exe -i -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"","messages":[]}'
```

---

## 附录E｜回滚与降级
- 任一上游失败（Hybrid/外部）→ 返回统一错误体，并在 headers/body 标注 degraded:true（如适用）
- 发现大面积 5xx 或 SSE 断流 → 关闭 SSE（ENABLE_SSE=false）并转为非流；必要时仅保留 /health、/v1/models