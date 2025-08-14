# Hybrid API 专家｜任务执行文档（统筹 v2.0 重构版，可选）

## 1. 基本信息
- 专家：hybrid-api-expert
- 统筹版本：v2.0
- 关联：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 将 Hybrid 从强依赖改为“可选依赖”，失败自动降级 RAG；隧道/反代打通 AutoDL。

## 3. 执行SOP（P1）

### 3.1 AutoDL环境操作（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL
ssh -p <PORT> <USER>@<HOST>

# 2. 进入服务目录
cd /root/autodl-tmp/ustb-project/services/model_inference/

# 3. 激活unsloth环境
source /root/miniconda3/bin/activate unsloth

# 4. 启动混合API服务（统一端口：8002）
/root/miniconda3/envs/unsloth/bin/python api_interface.py --port 8002
```

**本地SSH隧道配置（统一端口）**
```powershell
# 在本地PowerShell中建立隧道（混合API 8002）
ssh -p <PORT> -L 8002:localhost:8002 <USER>@<HOST>
```

**AutoDL环境验证（统一端口）**
```bash
# 在AutoDL上验证混合API服务
curl http://localhost:8002/health
curl -X POST http://localhost:8002/api/v1/hybrid_inference -H "Content-Type: application/json" -d '{"query":"测试","strategy":"parallel_merge"}'
```

### 3.2 本地环境配置
- [ ] HYBRID_API_URL 配置化为 `http://localhost:8002`；后端默认直连 RAG，Hybrid 失败自动降级（响应附 degraded:true）
- [ ] 隧道/反向代理脚本与运行手册（端口、心跳、重连）

## 4. 验收标准
- 关闭 Hybrid 后，/v1/chat/completions 仍可用；错误体/降级标记正确

## 5. 步骤记录（YYYY-MM-DD HH:mm）
- 目标：
- 操作：
- 产物路径：
- 回滚：

## 6. 小结
- 完成项：
- 风险：

---

## 附录A｜配置与降级开关
- HYBRID_API_URL（留空即禁用）
- HYBRID_TIMEOUT_MS（默认 15000）
- HYBRID_RETRY=1（失败重试次数）
- HYBRID_DEGRADED_HEADER: X-Hybrid-Degraded: true

## 附录B｜健康检查与隧道脚本要点
- 隧道保活：心跳/自动重连；固定本地端口
- Windows/PowerShell 示例：
```powershell
Test-NetConnection localhost -Port 9000
```

## 附录C｜验收命令
1) 关闭 Hybrid（留空 HYBRID_API_URL）
```powershell
$env:HYBRID_API_URL=""
curl.exe -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"ustb-rag-assistant","messages":[{"role":"user","content":"我要选课时间"}],"stream":false}'
```
期望：正常返回；响应头或体含 degraded:true

2) 打开 Hybrid，模拟上游 5xx
期望：自动降级；错误体统一且含 request_id
