# 数据治理专家｜任务执行文档（统筹 v2.0 重构版）

## 1. 基本信息
- 专家：data-governance-expert
- 统筹版本：v2.0
- 关联：docs/technical/USTB项目技术架构设计文档v3.0.md

## 2. 目标与范围
- 近 3 年数据清洗、时间纠偏、索引重建（稳定 doc_id/哈希）；周期化更新与质量报告。

## 3. 输入与输出
- 输入：原始/处理数据集 data/processed/rag_data.json
- 输出：
  - 清洗脚本 scripts/data/clean_recent.py
  - 质量报告 data/governance/reports/data_quality_report.md
  - 新索引（Qdrant）与快照

## 4. 执行SOP（P0 & P2）

### 4.1 AutoDL环境操作（脱敏示例）
**SSH连接与环境准备**
```bash
# 1. SSH连接AutoDL
ssh -p <PORT> <USER>@<HOST>

# 2. 进入项目目录
cd /root/autodl-tmp/ustb-project/

# 3. 激活unsloth环境
source /root/miniconda3/bin/activate unsloth

# 4. 创建数据治理目录结构
mkdir -p data/governance/reports/
mkdir -p scripts/data/
mkdir -p data/snapshots/
```

**AutoDL数据处理**
```bash
# 1. 检查原始数据
ls -la /root/autodl-tmp/ustb-project/data/processed/rag_data.json
wc -l /root/autodl-tmp/ustb-project/data/processed/rag_data.json

# 2. 运行数据清洗脚本
cd /root/autodl-tmp/ustb-project/scripts/data/
/root/miniconda3/envs/unsloth/bin/python clean_recent.py --input ../../data/processed/rag_data.json --output ../../data/governance/cleaned_data.json

# 3. 生成质量报告
/root/miniconda3/envs/unsloth/bin/python generate_quality_report.py --data ../../data/governance/cleaned_data.json --output ../../data/governance/reports/data_quality_report.md
```

**AutoDL向量索引重建**
```bash
# 1. 备份现有索引
cd /root/autodl-tmp/ustb-project/
curl -X POST "http://localhost:6333/collections/ustb_documents/snapshots" -H "Content-Type: application/json"

# 2. 重建向量索引
cd services/rag_system/
/root/miniconda3/envs/unsloth/bin/python rebuild_index.py --data ../../data/governance/cleaned_data.json

# 3. 验证索引状态
curl "http://localhost:6333/collections/ustb_documents"
```

### 4.2 本地环境配置
- [ ] 过滤 publish_date < now-3y 的文档
- [ ] 缺失/错误时间字段纠偏（标题/正文正则解析）
- [ ] 去重与字段完整性校验（>90%）
- [ ] 生成质量报告；未过项单独列表并拦截
- [ ] 重建向量索引（稳定 doc_id/哈希）；导出快照
- [ ] 周期化更新任务与告警（P2）

## 5. 验收标准
- 报告通过（近3年、完整性、重复率<5%）
- 检索按时间过滤命中正确

## 6. 步骤记录（YYYY-MM-DD HH:mm）
- 目标：
- 操作：
- 产物路径：
- 回滚：

## 7. 小结
- 完成项：
- 风险：

---

## 附录A｜数据字段规范与质量规则
- 关键字段：id、title、url、content、publish_date、source、category
- 时间格式：ISO8601（YYYY-MM-DD 或 YYYY-MM-DDTHH:mm:ssZ）
- 去重键：hash(title+url) 或稳定 doc_id
- 严格规则：
  - publish_date 必须存在且在近 3 年；缺失需通过正文/标题规则补齐
  - url 必须为 http(s) 且可访问（采样 5% 做可达性探测）
  - content 长度下限 80 字

## 附录B｜清洗脚本示例入口
```bash
python scripts/data/clean_recent.py --input data/processed/rag_data.json --output data/processed/rag_data.cleaned.json --window_years 3 --min_len 80 --dedup
```

## 附录C｜Qdrant 索引与集合约定
- 集合：ustb_documents
- 向量维度：768；度量：COSINE
- 元数据字段：doc_id、title、url、publish_date、category、source
- 索引重建：
```bash
python src/services/rag_system/vector_store.py --rebuild --collection ustb_documents --input data/processed/rag_data.cleaned.json
```

## 附录D｜验收命令（Windows PowerShell）
1) 时间窗口校验
```powershell
python scripts/data/clean_recent.py --dry-run --input data/processed/rag_data.json --window_years 3 | Select-String "violations"
```
2) 搜索接口按时间过滤
```powershell
curl.exe -X POST http://localhost:8001/api/v1/search -H "Content-Type: application/json" -d '{"query":"选课","date_range":{"since":"2022-09-01"}}'
```

## 附录E｜回滚策略
- 清洗失败或质量显著下降：回滚至上一个快照；放宽过滤阈值并记录原因
- 发现日期错误批量事件：启用人工白名单并在下一周期修复
