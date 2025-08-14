# 可观测性专家｜任务执行文档（统筹 v2.0 重构版）

## 1. 基本信息
- 专家：observability-expert
- 统筹版本：v2.0
- 关联：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 日志 MVP（JSON + X-Request-ID + 关键阶段打点 + 脱敏）与 /metrics 指标集（请求量/耗时/错误率/外部健康/缓存命中）。

## 3. 指标明细
- Counter：http_requests_total{path,status}、upstream_errors_total{service}
- Histogram：http_request_duration_ms_bucket{path}
- Gauge：cache_hit_ratio、external_health{service}

## 4. 执行SOP

### 4.1 AutoDL环境操作（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL
ssh -p <PORT> <USER>@<HOST>

# 2. 进入项目目录
cd /root/autodl-tmp/ustb-project/

# 3. 创建日志目录结构
mkdir -p logs/{rag,api_gateway,hybrid_api,system}
mkdir -p system/monitoring/
```

**AutoDL GPU监控配置**
```bash
# 1. 安装GPU监控工具
pip install nvidia-ml-py3 prometheus-client

# 2. 启动GPU指标收集器
cd /root/autodl-tmp/ustb-project/system/monitoring/
/root/miniconda3/envs/unsloth/bin/python gpu_exporter.py --port 9100

# 3. 验证GPU指标
curl http://localhost:9100/metrics | grep nvidia
nvidia-smi  # 验证GPU状态
```

**AutoDL日志配置**
```bash
# 1. 配置日志路径
export LOG_PATH="/root/autodl-tmp/ustb-project/logs"
export LOG_LEVEL="INFO"

# 2. 验证日志写入权限
touch $LOG_PATH/test.log && rm $LOG_PATH/test.log
```

### 4.2 本地环境配置
### P0 日志 MVP
- [ ] JSON 结构化日志；贯穿 X-Request-ID；检索/重排/生成/降级均打点
- [ ] 日志脱敏：过滤 Authorization、连接串；日志轮转
- [ ] AutoDL日志路径：`/root/autodl-tmp/ustb-project/logs/`
- 交付：docs/project/log-spec.md、logs/samples/

### P2 指标与GPU
- [ ] 暴露 /metrics；整合以上指标
- [ ] 部署 NVIDIA GPU Exporter（AutoDL 环境端口9100）；Grafana 面板导入
- [ ] AutoDL GPU监控：`nvidia-smi`、GPU利用率、显存使用率
- 交付：system/monitoring/**、docs/project/metrics.md

## 5. 验收标准
- 任一 request_id 可在日志中还原全链路
- /metrics 返回上述指标；Grafana 可视化正常

## 6. 步骤记录（YYYY-MM-DD HH:mm）
- 目标：
- 操作：
- 产物路径：
- 回滚：

## 7. 小结
- 完成项：
- 风险：

---

## 附录A｜日志 JSON 结构约定
```json
{
  "timestamp":"2025-01-01T12:00:00Z",
  "level":"INFO|ERROR",
  "request_id":"${uuid}",
  "event":"retrieval_finished",
  "latency_ms":123,
  "top_k":5,
  "hit_count":4,
  "upstream_status":200,
  "user_ip":"0.0.0.0"
}
```
- 脱敏：Authorization、password、connection_string 一律不落盘

## 附录B｜/metrics 暴露示例
```text
http_requests_total{path="/v1/chat/completions",status="200"} 1234
http_request_duration_ms_bucket{le="0.5",path="/v1/chat/completions"} 10
cache_hit_ratio 0.62
external_health{service="qdrant"} 1
```

## 附录C｜Grafana 面板建议
- 请求量/耗时/错误率 3 合 1
- Upstream 健康与降级占比
- GPU 利用率与显存
