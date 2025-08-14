# 集成测试专家｜任务执行文档（统筹 v2.0 重构版）

## 1. 基本信息
- 专家：integration-test-expert
- 统筹版本：v2.0
- 关联：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 覆盖 health/models/chat/search 最小集；SSE/错误体合同测试；性能基准与瓶颈报告。

## 3. 用例范围
- 功能：/health、/v1/models、/api/v1/search、/v1/chat/completions（非流+SSE）
- 合同：错误体结构一致、SSE分块与 [DONE]
- 性能：P95、错误率、并发

## 4. 输出与落点
- 测试：tests/integration/**
- 合同：tests/integration/api_contract.test.ts
- 性能脚本：tests/performance/**
- 报告：tests/reports/M0_baseline.json、M2_lc_eval.json、M3_perf.json

## 4.1 AutoDL环境测试配置（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL
ssh -p <PORT> <USER>@<HOST>

# 2. 进入项目目录
cd /root/autodl-tmp/ustb-project/

# 3. 创建测试报告目录
mkdir -p tests/reports/
```

**AutoDL环境服务验证**
```bash
# 1. 验证所有服务状态
curl http://localhost:8000/health  # RAG服务
curl http://localhost:8001/health  # API网关
curl http://localhost:8003/health  # 混合API（可选）

# 2. 验证端口监听状态
lsof -i :8000  # RAG服务端口
lsof -i :8001  # API网关端口
lsof -i :8003  # 混合API端口
```

**本地SSH隧道测试配置（统一端口）**
```powershell
# 在本地PowerShell中建立完整隧道（RAG/LoRA/Hybrid/Web）
ssh -p <PORT> -L 8000:localhost:8000 -L 8001:localhost:8001 -L 8002:localhost:8002 -L 8003:localhost:8003 <USER>@<HOST>
```

**AutoDL环境性能测试**
```bash
# 1. 安装性能测试工具
pip install locust

# 2. 在AutoDL上运行性能测试
cd /root/autodl-tmp/ustb-project/tests/performance/
/root/miniconda3/envs/unsloth/bin/python -m locust -f locust_load_test.py --host=http://localhost:8001 --users=5 --spawn-rate=1 --run-time=60s --headless
```

## 5. 步骤记录（YYYY-MM-DD HH:mm）
- 目标：
- 操作：
- 产物路径：
- 回滚：

## 6. 小结
- 完成项：
- 风险：

---

## 附录A｜测试约定
- 断言库：jest/playwright 或 pytest
- 生成报告：tests/reports/*.json；覆盖率≥90%
- Windows CI 注意：使用 curl.exe，避免 PowerShell alias

## 附录B｜功能用例（示例断言）
```ts
// tests/integration/api_contract.test.ts 片段
test('models should return ustb models', async () => {
  const res = await fetch('http://localhost:8001/v1/models');
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(Array.isArray(body.data)).toBe(true);
});
```

## 附录C｜SSE 用例（伪代码）
```ts
// 读取流直到 [DONE]
```

## 附录D｜性能脚本要点
- 指标：P95、错误率、并发（50）
- 输出：tests/reports/M3_perf.json
