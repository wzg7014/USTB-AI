#!/usr/bin/env python3
"""
Mem0 Memory Handler for PromptX
处理Mem0记忆系统的Python后端
"""

import sys
import json
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from enhanced_mem0_system import CompleteMem0System

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Mem0MemoryHandler:
    """Mem0记忆处理器"""
    
    def __init__(self, user_id: str = "luoxiaohan"):
        """初始化处理器"""
        self.user_id = user_id
        self.memory_system = CompleteMem0System(user_id=user_id)
        
    def add_memory(self, content: str, metadata: dict = None) -> dict:
        """添加记忆"""
        try:
            result = self.memory_system.add_memory(content, metadata)
            return {
                "success": True,
                "action": "add_memory",
                "result": result,
                "message": f"Memory added: {content[:50]}..."
            }
        except Exception as e:
            return {
                "success": False,
                "action": "add_memory", 
                "error": str(e)
            }
    
    def search_memories(self, query: str, limit: int = 10, threshold: float = 0.7) -> dict:
        """搜索记忆"""
        try:
            results = self.memory_system.search_memories(query, limit, threshold)
            return {
                "success": True,
                "action": "search_memories",
                "query": query,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {
                "success": False,
                "action": "search_memories",
                "error": str(e)
            }
    
    def get_all_memories(self, limit: int = 100) -> dict:
        """获取所有记忆"""
        try:
            memories = self.memory_system.get_all_memories(limit)
            return {
                "success": True,
                "action": "get_all_memories",
                "count": len(memories),
                "memories": memories
            }
        except Exception as e:
            return {
                "success": False,
                "action": "get_all_memories",
                "error": str(e)
            }
    
    def update_memory(self, memory_id: str, content: str) -> dict:
        """更新记忆"""
        try:
            result = self.memory_system.update_memory(memory_id, content)
            return {
                "success": True,
                "action": "update_memory",
                "memory_id": memory_id,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "update_memory",
                "error": str(e)
            }
    
    def delete_memory(self, memory_id: str) -> dict:
        """删除记忆"""
        try:
            result = self.memory_system.delete_memory(memory_id)
            return {
                "success": True,
                "action": "delete_memory",
                "memory_id": memory_id,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "delete_memory",
                "error": str(e)
            }
    
    def get_memory_history(self, memory_id: str) -> dict:
        """获取记忆历史"""
        try:
            history = self.memory_system.get_memory_history(memory_id)
            return {
                "success": True,
                "action": "get_memory_history",
                "memory_id": memory_id,
                "history": history
            }
        except Exception as e:
            return {
                "success": False,
                "action": "get_memory_history",
                "error": str(e)
            }
    
    def reset_memories(self) -> dict:
        """重置所有记忆"""
        try:
            result = self.memory_system.reset_memories()
            return {
                "success": True,
                "action": "reset_memories",
                "result": result,
                "message": f"All memories reset for user {self.user_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "reset_memories",
                "error": str(e)
            }
    
    def get_stats(self) -> dict:
        """获取记忆统计信息"""
        try:
            all_memories = self.memory_system.get_all_memories()
            
            # 统计信息
            total_count = len(all_memories)
            
            # 按类别统计
            categories = {}
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                category = metadata.get('category', 'uncategorized')
                categories[category] = categories.get(category, 0) + 1
            
            return {
                "success": True,
                "action": "get_stats",
                "user_id": self.user_id,
                "stats": {
                    "total_memories": total_count,
                    "categories": categories,
                    "memory_system_type": type(self.memory_system.memory).__name__
                }
            }
        except Exception as e:
            return {
                "success": False,
                "action": "get_stats",
                "error": str(e)
            }
    
    def execute_action(self, action: str, params: dict) -> dict:
        """执行指定动作"""
        try:
            if action == "add_memory":
                content = params.get("content", "")
                metadata = params.get("metadata", {})
                return self.add_memory(content, metadata)
            
            elif action == "search_memories":
                query = params.get("query", "")
                limit = params.get("limit", 10)
                threshold = params.get("threshold", 0.7)
                return self.search_memories(query, limit, threshold)
            
            elif action == "get_all_memories":
                limit = params.get("limit", 100)
                return self.get_all_memories(limit)
            
            elif action == "update_memory":
                memory_id = params.get("memory_id", "")
                content = params.get("content", "")
                return self.update_memory(memory_id, content)
            
            elif action == "delete_memory":
                memory_id = params.get("memory_id", "")
                return self.delete_memory(memory_id)
            
            elif action == "get_memory_history":
                memory_id = params.get("memory_id", "")
                return self.get_memory_history(memory_id)
            
            elif action == "reset_memories":
                return self.reset_memories()
            
            elif action == "get_stats":
                return self.get_stats()

            elif action == "analyze_memories":
                user_id = params.get("target_user_id", self.user_id)
                return self.analyze_memories(user_id)

            elif action == "find_related_memories":
                memory_id = params.get("memory_id", "")
                limit = params.get("limit", 5)
                return self.find_related_memories(memory_id, limit)

            elif action == "export_memories":
                user_id = params.get("target_user_id", self.user_id)
                format_type = params.get("format", "json")
                return self.export_memories(user_id, format_type)

            elif action == "health_check":
                return self.health_check()

            elif action == "backup_memories":
                filepath = params.get("filepath", "")
                user_id = params.get("target_user_id", self.user_id)
                return self.backup_memories(filepath, user_id)

            elif action == "restore_memories":
                filepath = params.get("filepath", "")
                user_id = params.get("target_user_id", self.user_id)
                return self.restore_memories(filepath, user_id)

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "available_actions": [
                        "add_memory", "search_memories", "get_all_memories",
                        "update_memory", "delete_memory", "get_memory_history",
                        "reset_memories", "get_stats", "analyze_memories",
                        "find_related_memories", "export_memories", "health_check",
                        "backup_memories", "restore_memories"
                    ]
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }

    def analyze_memories(self, user_id: str) -> dict:
        """分析记忆"""
        try:
            result = self.memory_system.analyze_memories(user_id)
            return {
                "success": True,
                "action": "analyze_memories",
                "user_id": user_id,
                "analysis": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "analyze_memories",
                "error": str(e)
            }

    def find_related_memories(self, memory_id: str, limit: int) -> dict:
        """查找相关记忆"""
        try:
            results = self.memory_system.find_related_memories(memory_id, limit)
            return {
                "success": True,
                "action": "find_related_memories",
                "memory_id": memory_id,
                "count": len(results),
                "related_memories": results
            }
        except Exception as e:
            return {
                "success": False,
                "action": "find_related_memories",
                "error": str(e)
            }

    def export_memories(self, user_id: str, format_type: str) -> dict:
        """导出记忆"""
        try:
            result = self.memory_system.export_memories(user_id, format_type)
            return {
                "success": True,
                "action": "export_memories",
                "user_id": user_id,
                "format": format_type,
                "export_data": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "export_memories",
                "error": str(e)
            }

    def health_check(self) -> dict:
        """健康检查"""
        try:
            result = self.memory_system.health_check()
            return {
                "success": True,
                "action": "health_check",
                "health_status": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "health_check",
                "error": str(e)
            }

    def backup_memories(self, filepath: str, user_id: str) -> dict:
        """备份记忆"""
        try:
            result = self.memory_system.backup_memories(filepath, user_id)
            return {
                "success": True,
                "action": "backup_memories",
                "backup_result": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "backup_memories",
                "error": str(e)
            }

    def restore_memories(self, filepath: str, user_id: str) -> dict:
        """恢复记忆"""
        try:
            result = self.memory_system.restore_memories(filepath, user_id)
            return {
                "success": True,
                "action": "restore_memories",
                "restore_result": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": "restore_memories",
                "error": str(e)
            }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Mem0 Memory Handler')
    parser.add_argument('--action', required=True, help='Action to perform')
    parser.add_argument('--user_id', default='luoxiaohan', help='User ID')
    parser.add_argument('--params', default='{}', help='Parameters as JSON string')
    
    args = parser.parse_args()
    
    try:
        # 解析参数
        params = json.loads(args.params)
        
        # 创建处理器
        handler = Mem0MemoryHandler(user_id=args.user_id)
        
        # 执行动作
        result = handler.execute_action(args.action, params)
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"Invalid JSON parameters: {e}"
        }
        print(json.dumps(error_result))
        sys.exit(1)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
