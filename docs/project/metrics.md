# 指标与暴露规范（v2.0）

## 1. 暴露端点
- GET /metrics（Prometheus 格式）

## 2. 指标清单
- Counter：http_requests_total{path,status}
- Histogram：http_request_duration_ms_bucket{path}
- Gauge：cache_hit_ratio、external_health{service}

示例：
```text
http_requests_total{path="/v1/chat/completions",status="200"} 1234
http_request_duration_ms_bucket{le="0.5",path="/v1/chat/completions"} 10
cache_hit_ratio 0.62
external_health{service="qdrant"} 1
```

## 3. GPU（AutoDL）
- NVIDIA GPU Exporter 启用，Grafana 导入标准面板

## 4. AutoDL环境指标配置

### 4.1 AutoDL环境指标端点（统一）
```bash
# AutoDL环境内部指标端点
- RAG服务指标：http://localhost:8000/metrics
- LoRA推理指标：http://localhost:8001/metrics
- 混合API指标：http://localhost:8002/metrics
- Web连接器指标：http://localhost:8003/metrics
- GPU监控指标：http://localhost:9100/metrics
```

### 4.2 AutoDL GPU监控配置（脱敏示例）
```bash
# 1. SSH连接AutoDL
ssh -p <PORT> <USER>@<HOST>

# 2. 进入监控目录
cd /root/autodl-tmp/ustb-project/system/monitoring/

# 3. 激活unsloth环境
source /root/miniconda3/bin/activate unsloth

# 4. 安装GPU监控依赖
pip install nvidia-ml-py3 prometheus-client

# 5. 启动GPU指标收集器
/root/miniconda3/envs/unsloth/bin/python gpu_exporter.py --port 9100

# 6. 验证GPU指标
curl http://localhost:9100/metrics | grep nvidia
nvidia-smi  # 验证GPU状态
```

### 4.3 AutoDL环境指标验证
```bash
# 在AutoDL环境内验证所有指标端点
curl http://localhost:8001/metrics | head -20
curl http://localhost:8000/metrics | head -20
curl http://localhost:8003/metrics | head -20
curl http://localhost:9100/metrics | grep -E "(nvidia|gpu)" | head -10
```

### 4.4 本地SSH隧道指标访问（脱敏示例）
```powershell
# 在本地PowerShell中建立指标隧道
ssh -p <PORT> -L 8001:localhost:8001 -L 8000:localhost:8000 -L 9100:localhost:9100 <USER>@<HOST>

# 本地访问指标（需要先建立SSH隧道）
curl.exe http://localhost:8001/metrics
curl.exe http://localhost:8000/metrics
curl.exe http://localhost:9100/metrics
```

### 4.5 AutoDL GPU指标示例
```text
# GPU利用率指标
nvidia_gpu_utilization_percent{gpu="0"} 85.5
nvidia_gpu_memory_used_bytes{gpu="0"} 8589934592
nvidia_gpu_memory_total_bytes{gpu="0"} 25769803776
nvidia_gpu_temperature_celsius{gpu="0"} 72.0
nvidia_gpu_power_watts{gpu="0"} 220.5

# 模型推理指标
model_inference_duration_seconds{model="qwen2.5-7b"} 2.34
model_tokens_generated_total{model="qwen2.5-7b"} 15678
model_memory_usage_bytes{model="qwen2.5-7b"} 7516192768
```

### 4.6 AutoDL监控目录结构
```bash
# AutoDL环境监控文件结构
/root/autodl-tmp/ustb-project/system/monitoring/
├── gpu_exporter.py           # GPU指标收集器
├── prometheus.yml            # Prometheus配置
├── grafana/                  # Grafana配置
│   ├── dashboards/          # 仪表板配置
│   └── provisioning/        # 自动配置
└── alerts/                   # 告警规则
```

### 4.7 AutoDL环境Prometheus配置
```yaml
# /root/autodl-tmp/ustb-project/system/monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ustb-api-gateway'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'

  - job_name: 'ustb-rag-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'ustb-gpu-exporter'
    static_configs:
      - targets: ['localhost:9100']
    metrics_path: '/metrics'
```

