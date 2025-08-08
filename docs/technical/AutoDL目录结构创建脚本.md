# AutoDL环境目录结构创建脚本

## 🎯 目的
确保AutoDL环境中的目录结构与项目文档完全一致，为模型训练专家提供正确的工作环境。

## 📋 需要创建的目录结构

### 模型训练相关目录
```bash
/root/autodl-tmp/ustb-project/
├── scripts/training/          # 训练脚本目录
├── models/trained/           # 训练好的模型目录
├── reports/                  # 报告目录
├── data/training/            # 训练数据目录
├── logs/training/            # 训练日志目录
├── services/                 # 集成专家服务目录
└── tests/unit/model_training/ # 模型训练测试目录
```

## 🚀 AutoDL环境目录创建命令

请在AutoDL终端中运行以下命令：

```bash
#!/bin/bash
echo "🚀 开始创建USTB项目AutoDL目录结构..."

# 确保在正确的工作目录
cd /root/autodl-tmp/ustb-project

# 创建模型训练相关目录
echo "📁 创建模型训练目录..."
mkdir -p scripts/training
mkdir -p models/trained
mkdir -p reports
mkdir -p data/training
mkdir -p logs/training
mkdir -p services/rag_system
mkdir -p services/model_inference
mkdir -p tests/unit/model_training

# 创建其他必要目录
echo "📁 创建其他必要目录..."
mkdir -p logs/training
mkdir -p configs/training
mkdir -p temp/training

# 验证目录创建
echo "✅ 验证目录结构..."
echo "当前目录结构："
tree -d -L 3 . 2>/dev/null || find . -type d -name ".*" -prune -o -type d -print | head -20

echo ""
echo "🎯 关键目录验证："
echo "训练脚本目录: $(ls -ld scripts/training 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"
echo "模型存储目录: $(ls -ld models/trained 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"
echo "报告目录: $(ls -ld reports 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"
echo "部署目录: $(ls -ld deployment/model 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"
echo "评估数据目录: $(ls -ld data/evaluation 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"
echo "测试目录: $(ls -ld tests/unit/model_training 2>/dev/null && echo "✅ 存在" || echo "❌ 不存在")"

echo ""
echo "📊 目录权限检查..."
echo "当前用户: $(whoami)"
echo "工作目录权限: $(ls -ld . | awk '{print $1, $3, $4}')"

echo ""
echo "🎉 AutoDL目录结构创建完成！"
echo "📍 当前位置: $(pwd)"
echo "📋 可以开始模型训练专家工作"
```

## 📝 目录用途说明

### `/root/autodl-tmp/scripts/training/`
- **用途**: 存放模型训练脚本
- **文件**: 
  - `train_model.py` - 主训练脚本
  - `data_loader.py` - 数据加载器
  - `evaluation.py` - 模型评估脚本
  - `config.yaml` - 训练配置文件

### `/root/autodl-tmp/models/trained/`
- **用途**: 存放训练好的模型文件
- **文件**:
  - `adapter_model.safetensors` - LoRA适配器权重
  - `adapter_config.json` - LoRA配置文件
  - `tokenizer/` - 分词器文件
  - `training_args.json` - 训练参数记录

### `/root/autodl-tmp/reports/`
- **用途**: 存放训练报告和分析结果
- **文件**:
  - `training_report.md` - 训练过程详细记录
  - `performance_metrics.json` - 性能指标记录

### `/root/autodl-tmp/deployment/model/`
- **用途**: 存放模型部署相关文件
- **文件**:
  - `inference_server.py` - 推理服务器
  - `model_loader.py` - 模型加载器
  - `test_inference.py` - 推理测试脚本

### `/root/autodl-tmp/data/evaluation/`
- **用途**: 存放评估数据集
- **文件**:
  - `test_set.json` - 测试数据集
  - `evaluation_results.json` - 评估结果详情

### `/root/autodl-tmp/tests/unit/model_training/`
- **用途**: 存放模型训练相关测试文件
- **文件**:
  - 单元测试脚本
  - 测试数据
  - 测试报告

## ⚠️ 重要注意事项

1. **权限确认**: 确保对所有目录有读写权限
2. **路径一致性**: 所有脚本中的路径必须使用绝对路径
3. **存储空间**: 确保有足够空间存储模型文件 (约10-20GB)
4. **备份策略**: 重要模型文件建议定期备份

## 🔧 故障排除

### 如果目录创建失败
```bash
# 检查权限
ls -la /root/
ls -la /root/autodl-tmp/

# 手动创建
sudo mkdir -p /root/autodl-tmp/models/trained
sudo chown -R $(whoami):$(whoami) /root/autodl-tmp/
```

### 如果空间不足
```bash
# 检查磁盘空间
df -h /root/autodl-tmp/

# 清理缓存
rm -rf /root/autodl-tmp/.cache/huggingface/hub/models--*/.git
```

---
**创建时间**: 2025-08-05  
**适用环境**: AutoDL RTX 4090  
**状态**: 准备就绪
