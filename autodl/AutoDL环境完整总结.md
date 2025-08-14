# USTB项目 AutoDL环境完整总结

## 🎯 **重要发现和修正记录**

### ⚠️ **关键端口配置修正**
在深度检查过程中发现并修正了多个端口配置错误：

1. **LoRA推理服务端口**：
   - ❌ 错误：8004端口
   - ✅ 正确：8001端口

2. **混合API服务端口**：
   - 🆕 新发现：8002端口（api_interface.py）
   - 📝 说明：这是一个重要的混合推理服务，之前未包含在文档中

3. **完整端口映射**：
   ```bash
   - RAG服务：8000 (services/rag_system/rag_service_v2.py)
   - LoRA推理：8001 (services/model_inference/ustb_lora_inference_server.py)
   - 混合API：8002 (services/model_inference/api_interface.py)
   - Web API连接器：8003 (system/web_integration/web_api_connector.py)
   - Qdrant向量数据库：6333
   - GPU监控：9100
   ```

## 📁 **完整文件清单（已验证）**

### 核心服务文件
```
/root/autodl-tmp/ustb-project/
├── services/
│   ├── rag_system/
│   │   └── rag_service_v2.py                    # 334行，RAG检索服务，端口8000
│   └── model_inference/
│       ├── ustb_lora_inference_server.py        # 353行，LoRA推理服务，端口8001
│       └── api_interface.py                     # 839行，混合API服务，端口8002
├── system/
│   └── web_integration/
│       └── web_api_connector.py                 # Web API连接器，端口8003
└── scripts/
    ├── ustb_chat_cli.py                         # 命令行聊天客户端
    └── ustb_chat.sh                             # Shell启动脚本
```

### 文件大小和行数验证
- ✅ **rag_service_v2.py**: 334行，完整版本
- ✅ **ustb_lora_inference_server.py**: 353行，完整版本，端口8001
- ✅ **api_interface.py**: 839行，混合API服务，端口8002
- ✅ **web_api_connector.py**: 完整版本，端口8003
- ✅ **ustb_chat_cli.py**: 完整版本，命令行工具

## 🚀 **正确的服务启动顺序**

### 1. RAG服务 (端口8000)
```bash
cd /root/autodl-tmp/ustb-project/services/rag_system/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python rag_service_v2.py
```

### 2. LoRA推理服务 (端口8001)
```bash
cd /root/autodl-tmp/ustb-project/services/model_inference/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python ustb_lora_inference_server.py --port 8001
```

### 3. 混合API服务 (端口8002) - 重要发现！
```bash
cd /root/autodl-tmp/ustb-project/services/model_inference/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python api_interface.py --port 8002
```

### 4. Web API连接器 (端口8003)
```bash
cd /root/autodl-tmp/ustb-project/system/web_integration/
source /root/miniconda3/bin/activate unsloth
/root/miniconda3/envs/unsloth/bin/python web_api_connector.py --hybrid-url http://localhost:8002
```

## 🔗 **正确的SSH隧道配置**

### 完整隧道（推荐）
```powershell
ssh -p 21020 -L 8000:localhost:8000 -L 8001:localhost:8001 -L 8002:localhost:8002 -L 8003:localhost:8003 root@connect.bjb1.seetacloud.com
```

### 分别建立隧道
```powershell
ssh -p 21020 -L 8000:localhost:8000 root@connect.bjb1.seetacloud.com  # RAG服务
ssh -p 21020 -L 8001:localhost:8001 root@connect.bjb1.seetacloud.com  # LoRA推理服务
ssh -p 21020 -L 8002:localhost:8002 root@connect.bjb1.seetacloud.com  # 混合API服务
ssh -p 21020 -L 8003:localhost:8003 root@connect.bjb1.seetacloud.com  # Web API连接器
```

## ✅ **服务验证命令**

### AutoDL环境内验证
```bash
curl http://localhost:8000/health  # RAG服务
curl http://localhost:8001/health  # LoRA推理服务
curl http://localhost:8002/health  # 混合API服务
curl http://localhost:8003/health  # Web API连接器
```

### 本地环境验证（通过SSH隧道）
```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8001/health
curl.exe http://localhost:8002/health
curl.exe http://localhost:8003/health
```

### 功能测试
```bash
# LoRA推理测试
curl -X POST http://localhost:8001/api/v1/inference -H "Content-Type: application/json" -d '{"query":"请问如何选课？","max_tokens":256}'

# 混合API测试
curl -X POST http://localhost:8002/api/v1/hybrid_inference -H "Content-Type: application/json" -d '{"query":"请问如何选课？","strategy":"parallel_merge"}'

# RAG搜索测试
curl -X POST http://localhost:8000/api/v1/search -H "Content-Type: application/json" -d '{"query":"选课","top_k":5}'
```

## 🔧 **工具使用**

### 命令行聊天工具
```bash
cd /root/autodl-tmp/ustb-project/scripts/
python ustb_chat_cli.py  # 交互式聊天
python ustb_chat_cli.py "请问如何选课？"  # 单次问答
```

## 📊 **系统架构图**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端/用户     │    │  Web API连接器  │    │    混合API      │
│                 │◄──►│   (端口8003)    │◄──►│   (端口8002)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                              ▼                        ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
                    │   RAG服务       │    │  LoRA推理服务   │    │   Qdrant数据库  │
                    │  (端口8000)     │    │  (端口8001)     │    │   (端口6333)    │
                    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ⚠️ **重要注意事项**

1. **文件准确性**：所有文件都已通过SSH工具从AutoDL实际环境获取并验证
2. **端口配置**：经过深度检查，所有端口配置已确认准确
3. **服务依赖**：混合API服务依赖RAG和LoRA服务，需要按顺序启动
4. **环境要求**：所有服务都需要在unsloth conda环境中运行

## 📝 **项目管理经验总结**

1. **深度验证的重要性**：用户的质疑帮助发现了关键的端口配置错误
2. **文件完整性检查**：必须验证文件行数和大小，确保获取完整内容
3. **系统性检查**：不能只关注单个文件，要检查整个系统的一致性
4. **持续更新**：AutoDL环境可能有更新，需要定期验证文件准确性

---

**最后更新时间**: 2025-08-14
**验证状态**: ✅ 已通过SSH工具深度验证
**准确性**: 🎯 与AutoDL环境完全一致
