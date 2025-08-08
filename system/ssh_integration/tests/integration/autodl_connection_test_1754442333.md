# AutoDL连接测试报告

**测试时间**: 2025-08-06T09:05:22.586800 - 2025-08-06T09:05:33.707775
**总测试数**: 12
**通过测试**: 8
**失败测试**: 4
**成功率**: 66.7%
**总耗时**: 11.12秒

## 详细结果

### SSH基础连接 ✅ 通过
- **耗时**: 0.51秒
- **消息**: SSH连接正常
- **详细信息**:
  - host: connect.bjb1.seetacloud.com
  - port: 21020
  - username: root

### 系统命令-basic_connectivity ✅ 通过
- **耗时**: 0.22秒
- **消息**: 命令执行成功
- **详细信息**:
  - command: echo 'SSH连接测试成功'
  - output: Command 'echo 'SSH连接测试成功'' executed successfully

### 系统命令-system_info ✅ 通过
- **耗时**: 0.20秒
- **消息**: 命令执行成功
- **详细信息**:
  - command: uname -a && whoami && pwd
  - output: Command 'uname -a && whoami && pwd' executed successfully

### 系统命令-gpu_status ✅ 通过
- **耗时**: 0.20秒
- **消息**: GPU状态正常
- **详细信息**:
  - command: nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
  - output: NVIDIA GeForce RTX 4090, 24564, 4

### 系统命令-disk_space ✅ 通过
- **耗时**: 0.20秒
- **消息**: 命令执行成功
- **详细信息**:
  - command: df -h /root/autodl-tmp
  - output: Command 'df -h /root/autodl-tmp' executed successfully

### 系统命令-python_env ✅ 通过
- **耗时**: 0.20秒
- **消息**: 命令执行成功
- **详细信息**:
  - command: python --version && which python
  - output: Command 'python --version && which python' executed successfully

### 系统命令-network_test ✅ 通过
- **耗时**: 0.20秒
- **消息**: 网络连接正常
- **详细信息**:
  - command: ping -c 3 8.8.8.8
  - output: 3 packets transmitted, 3 received, 0% packet loss

### 系统命令-process_check ✅ 通过
- **耗时**: 0.20秒
- **消息**: 命令执行成功
- **详细信息**:
  - command: ps aux | grep -E '(python|jupyter|tensorboard)' | head -5
  - output: Command 'ps aux | grep -E '(python|jupyter|tensorboard)' | head -5' executed successfully

### 服务端点-rag_service ❌ 失败
- **耗时**: 2.29秒
- **消息**: 连接失败: Cannot connect to host localhost:8000 ssl:default [远程计算机拒绝网络连接。]
- **详细信息**:
  - endpoint: http://localhost:8000
  - error: Cannot connect to host localhost:8000 ssl:default [远程计算机拒绝网络连接。]

### 服务端点-model_inference ❌ 失败
- **耗时**: 2.29秒
- **消息**: 连接失败: Cannot connect to host localhost:8001 ssl:default [远程计算机拒绝网络连接。]
- **详细信息**:
  - endpoint: http://localhost:8001
  - error: Cannot connect to host localhost:8001 ssl:default [远程计算机拒绝网络连接。]

### 服务端点-tensorboard ❌ 失败
- **耗时**: 2.29秒
- **消息**: 连接失败: Cannot connect to host localhost:6007 ssl:default [远程计算机拒绝网络连接。]
- **详细信息**:
  - endpoint: http://localhost:6007
  - error: Cannot connect to host localhost:6007 ssl:default [远程计算机拒绝网络连接。]

### 服务端点-jupyter ❌ 失败
- **耗时**: 2.30秒
- **消息**: 连接失败: Cannot connect to host localhost:8888 ssl:default [远程计算机拒绝网络连接。]
- **详细信息**:
  - endpoint: http://localhost:8888
  - error: Cannot connect to host localhost:8888 ssl:default [远程计算机拒绝网络连接。]
