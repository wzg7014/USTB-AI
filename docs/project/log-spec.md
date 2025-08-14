# 日志结构化规范（v2.0）

## 1. 输出格式
- JSON 每行（.jsonl），UTF-8
- 必备字段：timestamp、level、request_id、event
- 建议字段：latency_ms、path、status、top_k、hit_count、upstream_status、degraded

示例：
```json
{"timestamp":"2025-01-01T12:00:00Z","level":"INFO","request_id":"uuid","event":"retrieval_finished","latency_ms":123,"top_k":5,"hit_count":4,"upstream_status":200}
```

## 2. 脱敏规则
- 过滤：Authorization、password、connection_string
- 日志轮转：大小或按日切分

## 3. 目录
- 运行日志：logs/rag_flow/*.log
- 样例日志：logs/samples/*.jsonl

## 4. AutoDL环境日志配置（脱敏示例）

### 4.1 AutoDL日志目录结构
```bash
# AutoDL环境日志路径
/root/autodl-tmp/ustb-project/logs/
├── rag/                    # RAG服务日志
├── api_gateway/           # API网关日志
├── hybrid_api/            # 混合API日志
├── system/                # 系统日志
└── samples/               # 样例日志
```

### 4.2 AutoDL环境日志配置
```bash
# 1. SSH连接AutoDL（占位示例）
ssh -p <PORT> <USER>@<HOST>

# 2. 创建日志目录
cd /root/autodl-tmp/ustb-project/
mkdir -p logs/{rag,api_gateway,hybrid_api,system,samples}

# 3. 设置日志环境变量
export LOG_PATH="/root/autodl-tmp/ustb-project/logs"
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"

# 4. 验证日志写入权限
touch $LOG_PATH/test.log && rm $LOG_PATH/test.log
```

### 4.3 AutoDL服务日志配置
```bash
# RAG服务日志配置
cd /root/autodl-tmp/ustb-project/services/rag_system/
export RAG_LOG_PATH="/root/autodl-tmp/ustb-project/logs/rag"

# API网关日志配置
cd /root/autodl-tmp/ustb-project/src/backend/
export API_LOG_PATH="/root/autodl-tmp/ustb-project/logs/api_gateway"

# 混合API日志配置
cd /root/autodl-tmp/ustb-project/system/web_integration/
export HYBRID_LOG_PATH="/root/autodl-tmp/ustb-project/logs/hybrid_api"
```

### 4.4 AutoDL日志查看命令
```bash
# 实时查看日志
tail -f /root/autodl-tmp/ustb-project/logs/rag/*.log
tail -f /root/autodl-tmp/ustb-project/logs/api_gateway/*.log

# 按request_id查询日志
grep "request_id_value" /root/autodl-tmp/ustb-project/logs/*/*.log

# 日志统计分析
grep "ERROR" /root/autodl-tmp/ustb-project/logs/*/*.log | wc -l
grep "latency_ms" /root/autodl-tmp/ustb-project/logs/*/*.log | jq '.latency_ms' | sort -n
```

### 4.5 AutoDL日志轮转配置
```bash
# 安装logrotate（如果需要）
# 配置日志轮转规则
cat > /etc/logrotate.d/ustb-project << EOF
/root/autodl-tmp/ustb-project/logs/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF
```

