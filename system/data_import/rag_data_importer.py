#!/usr/bin/env python3
"""
RAG数据导入器 - 将本地RAG数据导入到AutoDL的Qdrant向量数据库
"""

import json
import os
import sys
import time
import logging
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
sys.path.append('/root/autodl-tmp/ustb-project/services/rag_system')

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"❌ 导入依赖失败: {e}")
    print("请确保在unsloth环境中运行此脚本")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/autodl-tmp/ustb-project/logs/rag_data_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RAGDataImporter:
    """RAG数据导入器"""
    
    def __init__(self):
        # Qdrant配置
        self.qdrant_path = "/root/autodl-tmp/ustb-project/data/vectors"
        self.collection_name = "ustb_documents"
        
        # 嵌入模型配置
        self.model_path = "/root/autodl-tmp/ustb-project/models/bce-embedding-base_v1"
        
        # 数据文件路径
        self.data_file = "/root/autodl-tmp/ustb-project/data/processed/rag_data.json"
        
        # 初始化客户端和模型
        self.client = None
        self.model = None
        
    def initialize(self):
        """初始化Qdrant客户端和嵌入模型"""
        try:
            # 初始化Qdrant客户端
            logger.info("初始化Qdrant客户端...")
            self.client = QdrantClient(path=self.qdrant_path)
            
            # 初始化嵌入模型
            logger.info(f"加载嵌入模型: {self.model_path}")
            self.model = SentenceTransformer(self.model_path)
            
            logger.info("✅ 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {str(e)}")
            return False
    
    def load_rag_data(self) -> List[Dict]:
        """加载RAG数据"""
        try:
            logger.info(f"加载RAG数据: {self.data_file}")
            
            if not os.path.exists(self.data_file):
                logger.error(f"❌ 数据文件不存在: {self.data_file}")
                return []
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✅ 成功加载 {len(data)} 条记录")
            return data
            
        except Exception as e:
            logger.error(f"❌ 加载数据失败: {str(e)}")
            return []
    
    def create_collection(self):
        """创建或重置Qdrant集合"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)
            
            if collection_exists:
                logger.info(f"删除现有集合: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            
            # 创建新集合
            logger.info(f"创建新集合: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=768,  # BCE模型的向量维度
                    distance=Distance.COSINE
                )
            )
            
            logger.info("✅ 集合创建成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建集合失败: {str(e)}")
            return False
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        try:
            logger.info(f"生成 {len(texts)} 个文本的嵌入向量...")
            embeddings = self.model.encode(texts, show_progress_bar=True)
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"❌ 生成嵌入向量失败: {str(e)}")
            return []
    
    def import_data(self, data: List[Dict], batch_size: int = 100):
        """导入数据到Qdrant"""
        try:
            total_records = len(data)
            logger.info(f"开始导入 {total_records} 条记录，批次大小: {batch_size}")
            
            # 分批处理
            for i in range(0, total_records, batch_size):
                batch = data[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_records + batch_size - 1) // batch_size
                
                logger.info(f"处理批次 {batch_num}/{total_batches} ({len(batch)} 条记录)")
                
                # 准备文本用于嵌入
                texts = []
                points = []
                
                for record in batch:
                    # 组合标题和内容用于嵌入
                    text = f"{record['title']}\n{record['content']}"
                    texts.append(text)
                
                # 生成嵌入向量
                embeddings = self.generate_embeddings(texts)
                
                if not embeddings:
                    logger.error(f"❌ 批次 {batch_num} 嵌入向量生成失败")
                    continue
                
                # 创建Qdrant点
                for j, (record, embedding) in enumerate(zip(batch, embeddings)):
                    point = PointStruct(
                        id=i + j + 1,  # 从1开始的ID
                        vector=embedding,
                        payload={
                            "ustb_id": record["id"],
                            "title": record["title"],
                            "content": record["content"][:1000],  # 限制内容长度
                            "url": record["url"],
                            "category": record["category"],
                            "publish_date": record["publish_date"],
                            "attachments": record.get("attachments", []),
                            "qwen_score": record.get("qwen_score", 0),
                            "data_category": record.get("data_category", "")
                        }
                    )
                    points.append(point)
                
                # 批量插入到Qdrant
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logger.info(f"✅ 批次 {batch_num} 导入完成")
                
                # 短暂休息避免过载
                time.sleep(1)
            
            logger.info(f"🎉 数据导入完成！总计 {total_records} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据导入失败: {str(e)}")
            return False
    
    def verify_import(self):
        """验证导入结果"""
        try:
            # 获取集合信息
            collection_info = self.client.get_collection(self.collection_name)
            point_count = collection_info.points_count
            
            logger.info(f"📊 集合统计:")
            logger.info(f"   - 集合名称: {self.collection_name}")
            logger.info(f"   - 文档数量: {point_count}")
            logger.info(f"   - 向量维度: {collection_info.config.params.vectors.size}")
            logger.info(f"   - 距离度量: {collection_info.config.params.vectors.distance}")
            
            # 测试搜索功能
            test_query = "如何查询成绩"
            logger.info(f"🔍 测试搜索: '{test_query}'")
            
            query_embedding = self.model.encode([test_query])[0].tolist()
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=3
            )
            
            logger.info(f"📋 搜索结果 ({len(search_results)} 条):")
            for i, result in enumerate(search_results, 1):
                logger.info(f"   {i}. {result.payload['title'][:50]}... (相似度: {result.score:.3f})")
            
            if point_count > 0 and len(search_results) > 0:
                logger.info("✅ 导入验证成功！RAG系统已就绪")
                return True
            else:
                logger.error("❌ 导入验证失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 验证失败: {str(e)}")
            return False
    
    def run(self):
        """执行完整的导入流程"""
        logger.info("🚀 开始RAG数据导入流程")
        
        # 1. 初始化
        if not self.initialize():
            return False
        
        # 2. 加载数据
        data = self.load_rag_data()
        if not data:
            return False
        
        # 3. 创建集合
        if not self.create_collection():
            return False
        
        # 4. 导入数据
        if not self.import_data(data):
            return False
        
        # 5. 验证结果
        if not self.verify_import():
            return False
        
        logger.info("🎉 RAG数据导入流程完成！")
        return True

def main():
    """主函数"""
    importer = RAGDataImporter()
    
    try:
        success = importer.run()
        if success:
            print("\n" + "="*60)
            print("🎉 RAG数据导入成功！")
            print("✅ Qdrant向量数据库已就绪")
            print("✅ RAG搜索功能可以正常使用")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ RAG数据导入失败！")
            print("请检查日志文件获取详细错误信息")
            print("="*60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断导入流程")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 导入流程异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
