#!/usr/bin/env python3
"""
端口转发配置管理器 - USTB混合云架构集成
负责管理SSH隧道的端口转发配置和动态调整
"""

import json
import logging
import socket
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PortMapping:
    """端口映射配置"""
    service_name: str
    local_port: int
    remote_port: int
    protocol: str = "tcp"
    description: str = ""
    enabled: bool = True
    auto_start: bool = True

@dataclass
class ForwardingRule:
    """转发规则"""
    name: str
    mappings: List[PortMapping]
    priority: int = 0
    conditions: Dict = None

class PortForwardingConfig:
    """端口转发配置管理器"""
    
    def __init__(self, config_file: str = "system/ssh_integration/port_config.yaml"):
        self.config_file = Path(config_file)
        self.port_mappings: Dict[str, PortMapping] = {}
        self.forwarding_rules: Dict[str, ForwardingRule] = {}
        self.reserved_ports: set = set()
        
        # 初始化默认配置
        self._setup_default_config()
        
        # 加载配置文件（如果存在）
        self.load_config()
    
    def _setup_default_config(self):
        """设置默认端口转发配置"""
        default_mappings = [
            PortMapping(
                service_name="rag_service",
                local_port=8000,
                remote_port=8000,
                description="GPU加速RAG检索服务",
                auto_start=True
            ),
            PortMapping(
                service_name="model_inference",
                local_port=8001,
                remote_port=8001,
                description="LoRA微调模型推理服务",
                auto_start=True
            ),
            PortMapping(
                service_name="tensorboard",
                local_port=6007,
                remote_port=6007,
                description="TensorBoard监控服务",
                enabled=False,
                auto_start=False
            ),
            PortMapping(
                service_name="jupyter",
                local_port=8888,
                remote_port=8888,
                description="Jupyter Lab开发环境",
                enabled=False,
                auto_start=False
            )
        ]
        
        for mapping in default_mappings:
            self.port_mappings[mapping.service_name] = mapping
        
        # 默认转发规则
        self.forwarding_rules["ustb_services"] = ForwardingRule(
            name="USTB教务助手核心服务",
            mappings=[
                self.port_mappings["rag_service"],
                self.port_mappings["model_inference"]
            ],
            priority=1
        )
        
        self.forwarding_rules["development_tools"] = ForwardingRule(
            name="开发工具服务",
            mappings=[
                self.port_mappings["tensorboard"],
                self.port_mappings["jupyter"]
            ],
            priority=2
        )
    
    def add_port_mapping(self, mapping: PortMapping) -> bool:
        """添加端口映射"""
        # 检查端口是否已被占用
        if self.is_port_in_use(mapping.local_port):
            logger.error(f"本地端口 {mapping.local_port} 已被占用")
            return False
        
        # 检查是否与现有映射冲突
        for existing_name, existing_mapping in self.port_mappings.items():
            if (existing_mapping.local_port == mapping.local_port and 
                existing_name != mapping.service_name):
                logger.error(f"端口 {mapping.local_port} 已被服务 {existing_name} 使用")
                return False
        
        self.port_mappings[mapping.service_name] = mapping
        logger.info(f"添加端口映射: {mapping.service_name} "
                   f"{mapping.local_port} -> {mapping.remote_port}")
        return True
    
    def remove_port_mapping(self, service_name: str) -> bool:
        """移除端口映射"""
        if service_name in self.port_mappings:
            mapping = self.port_mappings.pop(service_name)
            logger.info(f"移除端口映射: {service_name} "
                       f"{mapping.local_port} -> {mapping.remote_port}")
            return True
        else:
            logger.warning(f"未找到服务的端口映射: {service_name}")
            return False
    
    def update_port_mapping(self, service_name: str, **kwargs) -> bool:
        """更新端口映射"""
        if service_name not in self.port_mappings:
            logger.error(f"未找到服务: {service_name}")
            return False
        
        mapping = self.port_mappings[service_name]
        
        # 如果要更新本地端口，检查新端口是否可用
        if 'local_port' in kwargs:
            new_port = kwargs['local_port']
            if new_port != mapping.local_port and self.is_port_in_use(new_port):
                logger.error(f"新端口 {new_port} 已被占用")
                return False
        
        # 更新映射属性
        for key, value in kwargs.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)
                logger.info(f"更新 {service_name} 的 {key}: {value}")
        
        return True
    
    def get_enabled_mappings(self) -> List[PortMapping]:
        """获取启用的端口映射"""
        return [mapping for mapping in self.port_mappings.values() if mapping.enabled]
    
    def get_auto_start_mappings(self) -> List[PortMapping]:
        """获取自动启动的端口映射"""
        return [mapping for mapping in self.port_mappings.values() 
                if mapping.enabled and mapping.auto_start]
    
    def is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def find_available_port(self, start_port: int = 8000, end_port: int = 9000) -> Optional[int]:
        """查找可用端口"""
        for port in range(start_port, end_port + 1):
            if not self.is_port_in_use(port) and port not in self.reserved_ports:
                return port
        return None
    
    def reserve_port(self, port: int):
        """预留端口"""
        self.reserved_ports.add(port)
    
    def release_port(self, port: int):
        """释放端口"""
        self.reserved_ports.discard(port)
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        used_local_ports = set()
        used_remote_ports = set()
        
        for service_name, mapping in self.port_mappings.items():
            # 检查端口范围
            if not (1 <= mapping.local_port <= 65535):
                errors.append(f"{service_name}: 本地端口 {mapping.local_port} 超出有效范围")
            
            if not (1 <= mapping.remote_port <= 65535):
                errors.append(f"{service_name}: 远程端口 {mapping.remote_port} 超出有效范围")
            
            # 检查端口冲突
            if mapping.local_port in used_local_ports:
                errors.append(f"{service_name}: 本地端口 {mapping.local_port} 与其他服务冲突")
            used_local_ports.add(mapping.local_port)
            
            if mapping.remote_port in used_remote_ports:
                errors.append(f"{service_name}: 远程端口 {mapping.remote_port} 与其他服务冲突")
            used_remote_ports.add(mapping.remote_port)
            
            # 检查系统保留端口
            if mapping.local_port < 1024:
                errors.append(f"{service_name}: 本地端口 {mapping.local_port} 是系统保留端口")
        
        return len(errors) == 0, errors
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "port_mappings": {
                    name: asdict(mapping) 
                    for name, mapping in self.port_mappings.items()
                },
                "forwarding_rules": {
                    name: {
                        "name": rule.name,
                        "priority": rule.priority,
                        "conditions": rule.conditions,
                        "mappings": [mapping.service_name for mapping in rule.mappings]
                    }
                    for name, rule in self.forwarding_rules.items()
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self) -> bool:
        """从文件加载配置"""
        if not self.config_file.exists():
            logger.info("配置文件不存在，使用默认配置")
            return True
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 加载端口映射
            if 'port_mappings' in config_data:
                self.port_mappings.clear()
                for name, mapping_data in config_data['port_mappings'].items():
                    mapping = PortMapping(**mapping_data)
                    self.port_mappings[name] = mapping
            
            # 加载转发规则
            if 'forwarding_rules' in config_data:
                self.forwarding_rules.clear()
                for name, rule_data in config_data['forwarding_rules'].items():
                    mappings = [
                        self.port_mappings[mapping_name] 
                        for mapping_name in rule_data.get('mappings', [])
                        if mapping_name in self.port_mappings
                    ]
                    
                    rule = ForwardingRule(
                        name=rule_data.get('name', name),
                        mappings=mappings,
                        priority=rule_data.get('priority', 0),
                        conditions=rule_data.get('conditions')
                    )
                    self.forwarding_rules[name] = rule
            
            logger.info(f"配置已从 {self.config_file} 加载")
            return True
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False
    
    def get_config_summary(self) -> Dict:
        """获取配置摘要"""
        enabled_count = len(self.get_enabled_mappings())
        auto_start_count = len(self.get_auto_start_mappings())
        
        return {
            "total_mappings": len(self.port_mappings),
            "enabled_mappings": enabled_count,
            "auto_start_mappings": auto_start_count,
            "forwarding_rules": len(self.forwarding_rules),
            "reserved_ports": list(self.reserved_ports),
            "config_file": str(self.config_file),
            "mappings": {
                name: {
                    "local_port": mapping.local_port,
                    "remote_port": mapping.remote_port,
                    "enabled": mapping.enabled,
                    "auto_start": mapping.auto_start,
                    "description": mapping.description
                }
                for name, mapping in self.port_mappings.items()
            }
        }
    
    def export_ssh_commands(self) -> List[str]:
        """导出SSH隧道命令"""
        commands = []
        
        for mapping in self.get_enabled_mappings():
            command = (
                f"ssh -N -L {mapping.local_port}:localhost:{mapping.remote_port} "
                f"-p 21020 root@connect.bjb1.seetacloud.com"
            )
            commands.append(f"# {mapping.description}")
            commands.append(command)
            commands.append("")
        
        return commands

# 使用示例
def main():
    """主函数示例"""
    config = PortForwardingConfig()
    
    # 验证配置
    is_valid, errors = config.validate_config()
    print(f"配置验证: {'通过' if is_valid else '失败'}")
    if errors:
        for error in errors:
            print(f"  错误: {error}")
    
    # 获取配置摘要
    summary = config.get_config_summary()
    print("\n配置摘要:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # 导出SSH命令
    commands = config.export_ssh_commands()
    print("\nSSH隧道命令:")
    for command in commands:
        print(command)
    
    # 保存配置
    config.save_config()

if __name__ == "__main__":
    main()
