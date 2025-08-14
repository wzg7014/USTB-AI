# API 映射与保留/弃用清单（v2.0）

## 1. 保留（白名单）
- GET /v1/models
- POST /v1/chat/completions
- POST /api/v1/search
- GET /api/v1/categories
- GET /health
- GET /metrics

## 2. 弃用（黑名单 → 404/410，迁移期 30 天）
- /chat、/completions、/search*（除 /api/v1/search）等历史路径

响应示例（410 Gone）：
```json
{
  "error": {
    "code": "Gone",
    "message": "接口已弃用，请迁移至 /v1/chat/completions 或 /api/v1/search",
    "request_id": "${uuid}"
  }
}
```

## 3. 版本策略
- Header：X-API-Version: 1（优先）
- 或路径：/v1/…

## 4. 约定
- 所有响应携带 X-Request-ID；错误体统一为 { error:{ code, message, request_id } }

## 5. AutoDL环境API配置（统一口径 + 脱敏）

### 5.1 AutoDL服务端口映射
```bash
# AutoDL环境内部端口（统一）
- RAG服务：http://localhost:8000
- LoRA推理：http://localhost:8001
- 混合API：http://localhost:8002
- Web连接器：http://localhost:8003
- GPU监控：http://localhost:9100
```

### 5.2 SSH隧道端口映射（脱敏示例）
```powershell
# 本地PowerShell隧道配置（一次性映射四个服务）
ssh -p <PORT> -L 8000:localhost:8000 -L 8001:localhost:8001 -L 8002:localhost:8002 -L 8003:localhost:8003 <USER>@<HOST>
```

### 5.3 AutoDL环境API验证
```bash
# 在AutoDL环境内验证（API网关或Web连接器按实际部署选择）
curl http://localhost:8001/health             # LoRA
curl http://localhost:8000/health             # RAG
curl http://localhost:8002/health             # 混合API
curl http://localhost:8003/health             # Web连接器
```

### 5.4 本地环境API访问（通过SSH隧道）
```powershell
# 本地PowerShell验证（需要先建立SSH隧道）
curl.exe http://localhost:8000/health
curl.exe http://localhost:8001/health
curl.exe http://localhost:8002/health
curl.exe http://localhost:8003/health
```

### 5.5 AutoDL环境配置文件路径
- 后端配置：`/root/autodl-tmp/ustb-project/src/backend/.env`
- RAG配置：`/root/autodl-tmp/ustb-project/services/rag_system/.env`
- 混合API配置：`/root/autodl-tmp/ustb-project/system/web_integration/.env`

