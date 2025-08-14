# USTB项目 AutoDL环境完整信息

## 📋 基本信息

### SSH连接信息
```bash
Host: connect.bjb1.seetacloud.com
Port: 21020
Username: root
Password: oqpdtTQSuC2B

# 连接命令
ssh -p 21020 root@connect.bjb1.seetacloud.com
```

### 项目路径
```bash
项目根目录: /root/autodl-tmp/ustb-project/
Python环境: /root/miniconda3/envs/unsloth/bin/python
Conda环境: unsloth
```

### 服务端口配置
```bash
- RAG服务：8000 (services/rag_system/)
- LoRA推理：8001 (services/model_inference/ustb_lora_inference_server.py)
- 混合API：8002 (services/model_inference/api_interface.py)  # 重要发现！
- Web API连接器：8003 (system/web_integration/)
- Qdrant向量数据库：6333
- GPU监控：9100 (system/monitoring/)
```

## 🗂️ 目录结构

```
/root/autodl-tmp/ustb-project/
├── services/
│   ├── rag_system/                    # RAG服务 (端口8000)
│   │   ├── rag_service_v2.py         # RAG服务主程序
│   │   ├── vector_store.py           # 向量存储管理
│   │   ├── embedding_service.py      # 嵌入服务
│   │   └── .ipynb_checkpoints/       # Jupyter检查点
│   └── model_inference/              # 模型推理服务 (端口8004)
│       ├── ustb_lora_inference_server.py  # LoRA推理服务器
│       ├── api_interface.py          # API接口
│       └── .ipynb_checkpoints/       # Jupyter检查点
├── system/
│   └── web_integration/              # Web集成 (端口8003)
│       └── web_api_connector.py      # Web API连接器
├── scripts/
│   └── ustb_chat_cli.py             # 聊天CLI工具
├── data/                            # 数据文件
├── logs/                            # 日志文件
└── models/                          # 模型文件
```

## 🚀 服务启动命令

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

### 3. 混合API服务 (端口8002)
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

## 🔧 SSH隧道配置

### 本地PowerShell隧道命令
```powershell
# 完整隧道 (推荐)
ssh -p 21020 -L 8000:localhost:8000 -L 8001:localhost:8001 -L 8002:localhost:8002 -L 8003:localhost:8003 root@connect.bjb1.seetacloud.com

# 分别建立隧道
ssh -p 21020 -L 8000:localhost:8000 root@connect.bjb1.seetacloud.com  # RAG服务
ssh -p 21020 -L 8001:localhost:8001 root@connect.bjb1.seetacloud.com  # LoRA推理服务
ssh -p 21020 -L 8002:localhost:8002 root@connect.bjb1.seetacloud.com  # 混合API服务
ssh -p 21020 -L 8003:localhost:8003 root@connect.bjb1.seetacloud.com  # Web API连接器
```

## ✅ 环境验证

### AutoDL环境内验证
```bash
# 服务健康检查
curl http://localhost:8000/health  # RAG服务
curl http://localhost:8003/health  # Web API连接器
curl http://localhost:8001/health  # LoRA推理服务

# GPU状态检查
nvidia-smi

# Python环境检查
which python
python --version
conda info --envs
```

### 本地环境验证 (需要先建立SSH隧道)
```powershell
# 健康检查
curl.exe http://localhost:8000/health
curl.exe http://localhost:8003/health
curl.exe http://localhost:8001/health

# 功能测试
curl.exe -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query":"测试","top_k":3}'
```

## 📁 重要文件说明

### 核心服务文件
- `services/rag_system/rag_service_v2.py` - RAG服务主程序，处理检索增强生成
- `services/rag_system/vector_store.py` - 向量存储管理，Qdrant集成
- `services/rag_system/embedding_service.py` - 嵌入服务，BCE模型
- `services/model_inference/ustb_lora_inference_server.py` - LoRA微调模型推理服务
- `services/model_inference/api_interface.py` - 模型推理API接口
- `system/web_integration/web_api_connector.py` - Web API连接器，协调各服务

### 工具脚本
- `scripts/ustb_chat_cli.py` - 命令行聊天工具

## 🔍 故障排查

### 常见问题
1. **服务无法启动** - 检查端口占用：`lsof -i :8000`
2. **Python环境错误** - 确保使用unsloth环境：`source /root/miniconda3/bin/activate unsloth`
3. **SSH隧道断开** - 重新建立隧道连接
4. **GPU内存不足** - 检查GPU状态：`nvidia-smi`

### 日志查看
```bash
# 查看服务日志
tail -f /root/autodl-tmp/ustb-project/logs/*.log

# 查看系统日志
journalctl -f
```

## 📊 性能监控

### GPU监控
```bash
# 实时GPU状态
watch -n 1 nvidia-smi

# GPU使用率历史
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,memory.total --format=csv -l 1
```

### 服务监控
```bash
# 进程监控
ps aux | grep python

# 端口监控
lsof -i :8000,8003,8004
```

---

## ⚠️ **重要声明**

**文件准确性说明**：
- 本文档中的代码文件是通过SSH工具从AutoDL实际环境中获取的
- 获取时间：2025-08-14
- 如果AutoDL环境中的文件有更新，本地副本可能不是最新版本
- **建议使用前先通过SSH连接AutoDL验证文件的最新状态**

**验证命令**：
```bash
# 连接AutoDL
ssh -p 21020 root@connect.bjb1.seetacloud.com

# 检查文件修改时间
ls -la /root/autodl-tmp/ustb-project/services/rag_system/rag_service_v2.py
ls -la /root/autodl-tmp/ustb-project/services/model_inference/ustb_lora_inference_server.py
ls -la /root/autodl-tmp/ustb-project/system/web_integration/web_api_connector.py

# 比较文件内容（如有需要）
md5sum /root/autodl-tmp/ustb-project/services/rag_system/rag_service_v2.py
```

**注意**: 此文档包含AutoDL环境的配置信息，请妥善保管SSH凭据。文件内容仅供参考，实际使用时请以AutoDL环境中的最新版本为准。
