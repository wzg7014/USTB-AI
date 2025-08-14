#!/usr/bin/env python3
"""
USTB AI教务助手 - 命令行聊天客户端
直接与LoRA推理服务交互的命令行工具

使用方法:
  python ustb_chat_cli.py                    # 交互式聊天
  python ustb_chat_cli.py "你的问题"          # 单次问答
  python ustb_chat_cli.py --help             # 查看帮助

创建时间: 2025-08-07
作者: AI助手
"""

import requests
import json
import sys
import argparse
from datetime import datetime

class USTBChatCLI:
    def __init__(self, server_url="http://localhost:8001"):
        self.server_url = server_url
        self.session = requests.Session()
        
    def check_server(self):
        """检查服务器状态"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                if health.get("model_loaded"):
                    return True, "服务正常"
                else:
                    return False, "模型未加载"
            else:
                return False, f"服务异常: {response.status_code}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def ask_question(self, question, max_tokens=300, temperature=0.1):
        """向模型提问"""
        try:
            payload = {
                "query": question,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = self.session.post(
                f"{self.server_url}/api/v1/inference",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return True, result
            else:
                return False, f"请求失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"请求异常: {str(e)}"
    
    def print_response(self, result):
        """格式化打印响应"""
        print(f"\n🤖 USTB AI教务助手回答:")
        print(f"{'='*60}")
        print(f"{result['response']}")
        print(f"{'='*60}")
        print(f"⏱️  推理时间: {result['inference_time']:.2f}秒")
        print(f"📊 生成tokens: {result['tokens_generated']}个")
        print(f"🎯 置信度: {result['confidence']:.2f}")
        print(f"🕐 时间: {result['timestamp']}")
        print()
    
    def interactive_chat(self):
        """交互式聊天模式"""
        print("🎓 USTB AI教务助手 - 命令行版")
        print("="*50)
        
        # 检查服务状态
        is_ok, message = self.check_server()
        if not is_ok:
            print(f"❌ 服务检查失败: {message}")
            print("请确保推理服务正在运行在 http://localhost:8001")
            return
        
        print(f"✅ {message}")
        print("\n💡 使用说明:")
        print("  - 直接输入您的USTB教务相关问题")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("  - 输入 'help' 查看帮助")
        print("  - 输入 'stats' 查看服务统计")
        print()
        
        while True:
            try:
                # 获取用户输入
                question = input("🙋 您的问题: ").strip()
                
                if not question:
                    continue
                
                # 处理特殊命令
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！感谢使用USTB AI教务助手")
                    break
                
                if question.lower() == 'help':
                    self.show_help()
                    continue
                
                if question.lower() == 'stats':
                    self.show_stats()
                    continue
                
                # 发送问题到模型
                print("🤔 正在思考...")
                success, result = self.ask_question(question)
                
                if success:
                    self.print_response(result)
                else:
                    print(f"❌ 请求失败: {result}")
                    
            except KeyboardInterrupt:
                print("\n👋 再见！感谢使用USTB AI教务助手")
                break
            except Exception as e:
                print(f"❌ 发生错误: {str(e)}")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n📖 USTB AI教务助手帮助:")
        print("-" * 40)
        print("🎯 功能: 为USTB学生提供教务相关咨询")
        print("💬 支持问题类型:")
        print("  • 选课相关: 如何选课、选课时间、选课流程")
        print("  • 考试相关: 考试安排、补考申请、成绩查询")
        print("  • 学籍相关: 转专业、休学、毕业要求")
        print("  • 政策相关: 学分要求、奖学金、学术规定")
        print("\n🔧 命令:")
        print("  help  - 显示此帮助")
        print("  stats - 显示服务统计")
        print("  quit  - 退出程序")
        print()
    
    def show_stats(self):
        """显示服务统计"""
        try:
            response = self.session.get(f"{self.server_url}/api/v1/stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                print("\n📊 服务统计:")
                print("-" * 30)
                print(f"请求总数: {stats.get('request_count', 0)}")
                print(f"平均响应时间: {stats.get('average_response_time', 0):.2f}秒")
                print(f"总生成tokens: {stats.get('total_tokens_generated', 0)}")
                print(f"服务运行时间: {stats.get('uptime_seconds', 0):.1f}秒")
                print(f"模型: {stats.get('model_name', 'Unknown')}")
                print()
            else:
                print("❌ 无法获取服务统计")
        except Exception as e:
            print(f"❌ 获取统计失败: {str(e)}")
    
    def single_question(self, question):
        """单次问答模式"""
        # 检查服务状态
        is_ok, message = self.check_server()
        if not is_ok:
            print(f"❌ 服务检查失败: {message}")
            return False
        
        # 发送问题
        success, result = self.ask_question(question)
        
        if success:
            self.print_response(result)
            return True
        else:
            print(f"❌ 请求失败: {result}")
            return False

def main():
    parser = argparse.ArgumentParser(description="USTB AI教务助手命令行客户端")
    parser.add_argument("question", nargs="?", help="要询问的问题（可选，不提供则进入交互模式）")
    parser.add_argument("--server", default="http://localhost:8001", help="推理服务地址")
    parser.add_argument("--max-tokens", type=int, default=300, help="最大生成token数")
    parser.add_argument("--temperature", type=float, default=0.1, help="生成温度")
    
    args = parser.parse_args()
    
    # 创建客户端
    client = USTBChatCLI(server_url=args.server)
    
    if args.question:
        # 单次问答模式
        success = client.single_question(args.question)
        sys.exit(0 if success else 1)
    else:
        # 交互式聊天模式
        client.interactive_chat()

if __name__ == "__main__":
    main()

"""
使用示例:

1. 交互式聊天:
cd /root/autodl-tmp/ustb-project/scripts/
python ustb_chat_cli.py

2. 单次问答:
python ustb_chat_cli.py "请问如何选课？"

3. 指定服务器:
python ustb_chat_cli.py --server http://localhost:8001 "考试时间是什么时候？"

4. 调整参数:
python ustb_chat_cli.py --max-tokens 500 --temperature 0.2 "毕业要求是什么？"

注意：需要确保LoRA推理服务正在运行在指定端口（默认8001）
"""
