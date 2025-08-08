"""
USTB RAG系统部署脚本
自动化部署和初始化RAG系统
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from loguru import logger

class RAGDeployer:
    """RAG系统部署器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.rag_service_dir = Path(__file__).parent
        self.data_dir = self.project_root / "data"
        self.vector_dir = self.data_dir / "vectors"
        
    def check_prerequisites(self) -> bool:
        """检查部署前置条件"""
        logger.info("检查部署前置条件...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            logger.error("需要Python 3.8或更高版本")
            return False
        
        # 检查RAG数据文件
        rag_data_file = self.data_dir / "processed" / "rag_data.json"
        if not rag_data_file.exists():
            logger.error(f"RAG数据文件不存在: {rag_data_file}")
            return False
        
        # 检查数据文件大小
        file_size = rag_data_file.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"RAG数据文件大小: {file_size:.2f}MB")
        
        if file_size < 1:
            logger.warning("RAG数据文件过小，可能不完整")
        
        # 创建必要目录
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ 前置条件检查通过")
        return True
    
    def install_dependencies(self) -> bool:
        """安装依赖包"""
        logger.info("安装Python依赖包...")
        
        requirements_file = self.rag_service_dir / "requirements.txt"
        if not requirements_file.exists():
            logger.error("requirements.txt文件不存在")
            return False
        
        try:
            # 安装依赖
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.rag_service_dir)
            
            if result.returncode != 0:
                logger.error(f"依赖安装失败: {result.stderr}")
                return False
            
            logger.info("✅ 依赖包安装完成")
            return True
            
        except Exception as e:
            logger.error(f"依赖安装异常: {str(e)}")
            return False
    
    def initialize_vector_database(self) -> bool:
        """初始化向量数据库"""
        logger.info("初始化向量数据库...")
        
        try:
            # 导入RAG组件
            sys.path.append(str(self.rag_service_dir))
            from vector_store import vector_store
            from embedding_service import embedding_service
            from retrieval_engine import retrieval_engine
            
            # 创建向量集合
            vector_store.create_collection()
            logger.info("✅ 向量集合创建完成")
            
            # 加载并索引文档
            doc_count = retrieval_engine.load_and_index_documents()
            logger.info(f"✅ 成功索引 {doc_count} 个文档")
            
            return True
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {str(e)}")
            return False
    
    def test_system_functionality(self) -> bool:
        """测试系统功能"""
        logger.info("测试系统功能...")
        
        try:
            sys.path.append(str(self.rag_service_dir))
            from retrieval_engine import retrieval_engine
            from embedding_service import embedding_service
            from vector_store import vector_store
            
            # 测试嵌入服务
            test_embedding = embedding_service.encode_text("测试文本")
            if len(test_embedding) != 768:
                logger.error("嵌入服务测试失败")
                return False
            
            # 测试向量存储
            if not vector_store.health_check():
                logger.error("向量存储健康检查失败")
                return False
            
            # 测试检索功能
            results = retrieval_engine.search("选课通知", top_k=3)
            if not isinstance(results, list):
                logger.error("检索功能测试失败")
                return False
            
            logger.info(f"✅ 系统功能测试通过，检索到 {len(results)} 个结果")
            return True
            
        except Exception as e:
            logger.error(f"系统功能测试失败: {str(e)}")
            return False
    
    def create_service_config(self) -> bool:
        """创建服务配置文件"""
        logger.info("创建服务配置文件...")
        
        config = {
            "service": {
                "name": "ustb-rag-system",
                "version": "1.0.0",
                "host": "0.0.0.0",
                "port": 8000
            },
            "qdrant": {
                "collection_name": "ustb_documents",
                "vector_size": 768,
                "storage_path": str(self.vector_dir)
            },
            "embedding": {
                "model_name": "maidalun1020/bce-embedding-base_v1",
                "device": "cpu",
                "batch_size": 32
            },
            "performance": {
                "max_concurrent_requests": 50,
                "request_timeout": 30,
                "similarity_threshold": 0.7
            }
        }
        
        config_file = self.rag_service_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 配置文件已创建: {config_file}")
        return True
    
    def create_startup_script(self) -> bool:
        """创建启动脚本"""
        logger.info("创建启动脚本...")
        
        # Windows启动脚本
        windows_script = f"""@echo off
echo Starting USTB RAG System...
cd /d "{self.rag_service_dir}"
python app.py
pause
"""
        
        windows_file = self.rag_service_dir / "start_rag_system.bat"
        with open(windows_file, 'w', encoding='utf-8') as f:
            f.write(windows_script)
        
        # Linux/Mac启动脚本
        unix_script = f"""#!/bin/bash
echo "Starting USTB RAG System..."
cd "{self.rag_service_dir}"
python app.py
"""
        
        unix_file = self.rag_service_dir / "start_rag_system.sh"
        with open(unix_file, 'w', encoding='utf-8') as f:
            f.write(unix_script)
        
        # 设置执行权限
        try:
            os.chmod(unix_file, 0o755)
        except:
            pass  # Windows环境忽略
        
        logger.info("✅ 启动脚本已创建")
        return True
    
    def generate_deployment_report(self) -> bool:
        """生成部署报告"""
        logger.info("生成部署报告...")
        
        report = f"""# USTB RAG系统部署报告

## 部署信息
- **部署时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **部署路径**: {self.rag_service_dir}
- **数据路径**: {self.data_dir}
- **向量数据库**: {self.vector_dir}

## 系统配置
- **Python版本**: {sys.version}
- **服务端口**: 8000
- **嵌入模型**: BCE-embedding-base_v1
- **向量维度**: 768

## 服务启动
### Windows
```cmd
cd "{self.rag_service_dir}"
start_rag_system.bat
```

### Linux/Mac
```bash
cd "{self.rag_service_dir}"
./start_rag_system.sh
```

## 服务访问
- **健康检查**: http://localhost:8000/health
- **API文档**: http://localhost:8000/docs
- **检索接口**: POST http://localhost:8000/api/v1/search

## 测试命令
```python
import requests

# 健康检查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 检索测试
response = requests.post("http://localhost:8000/api/v1/search", json={{
    "query": "选课通知",
    "top_k": 3
}})
print(response.json())
```

## 部署状态
✅ 部署成功完成
✅ 系统功能正常
✅ 准备投入使用

---
**部署完成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        report_file = self.project_root / "reports" / "rag_deployment_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ 部署报告已生成: {report_file}")
        return True
    
    def deploy(self) -> bool:
        """执行完整部署流程"""
        logger.info("🚀 开始USTB RAG系统部署")
        
        steps = [
            ("检查前置条件", self.check_prerequisites),
            ("安装依赖包", self.install_dependencies),
            ("初始化向量数据库", self.initialize_vector_database),
            ("测试系统功能", self.test_system_functionality),
            ("创建服务配置", self.create_service_config),
            ("创建启动脚本", self.create_startup_script),
            ("生成部署报告", self.generate_deployment_report)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"执行步骤: {step_name}")
            if not step_func():
                logger.error(f"❌ 步骤失败: {step_name}")
                return False
            logger.info(f"✅ 步骤完成: {step_name}")
        
        logger.info("🎉 USTB RAG系统部署成功完成!")
        logger.info("📋 请查看部署报告了解详细信息")
        logger.info("🌐 服务将在 http://localhost:8000 启动")
        
        return True

def main():
    """主函数"""
    deployer = RAGDeployer()
    success = deployer.deploy()
    
    if success:
        print("\n" + "="*60)
        print("🎉 USTB RAG系统部署成功!")
        print("="*60)
        print("📋 下一步操作:")
        print("1. 运行启动脚本启动服务")
        print("2. 访问 http://localhost:8000/health 检查服务状态")
        print("3. 访问 http://localhost:8000/docs 查看API文档")
        print("4. 使用 POST /api/v1/search 进行文档检索")
        print("="*60)
        return 0
    else:
        print("\n❌ RAG系统部署失败，请检查错误日志")
        return 1

if __name__ == "__main__":
    exit(main())
