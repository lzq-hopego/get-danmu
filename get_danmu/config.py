import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # 配置文件路径
        self.config_dir = Path.home() / ".get_danmu"
        self.config_file = self.config_dir / "config.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 初始化配置文件
        if not self.config_file.exists():
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def load_config(self):
        """加载配置文件"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, config):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def save_proxy(self, proxy):
        """保存代理配置"""
        config = self.load_config()
        config['proxy'] = proxy
        self.save_config(config)
    
    def get_proxy(self):
        """获取保存的代理配置"""
        config = self.load_config()
        return config.get('proxy')
    
    def clear_proxy(self):
        """清理代理配置"""
        config = self.load_config()
        if 'proxy' in config:
            del config['proxy']
            self.save_config(config)

    # 新增：数据库路径配置
    def save_db_path(self, db_path):
        if not isinstance(db_path, str) or not db_path.strip():
            raise ValueError("数据库路径必须是有效的字符串")
        abs_db_path = str(Path(db_path.strip()).absolute())
        config = self.load_config()
        config['db_path'] = abs_db_path
        self.save_config(config)

    def get_db_path(self):
        return self.load_config().get('db_path')

    def clear_db_path(self):
        """清理db配置"""
        config = self.load_config()
        if 'db_path' in config:
            del config['db_path']
            self.save_config(config)

    def clear_all_config(self):
        """清理所有配置"""
        if self.config_file.exists():
            os.remove(self.config_file)
        # 重新创建空配置文件
        self.__init__()
