"""
应用主配置

定义 conf/app_config.yaml 在程序中的结构化配置对象
项目启动后会在这里一次性完成配置文件加载和类型化转换，其他模块只需要导入 app_config
就可以按属性方式读取日志 MySQL Qdrant Embedding Elasticsearch 和 LLM 配置
"""

from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from pathlib import Path  # 从 pathlib 导入 Path，供本模块后续代码使用

from dotenv import load_dotenv  # 从 dotenv 导入 load_dotenv，供本模块后续代码使用
from omegaconf import OmegaConf  # 从 omegaconf 导入 OmegaConf，供本模块后续代码使用


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class File:  # 定义类 File，组织相关状态与行为
    """文件日志配置"""

    enable: bool  # 声明或继续传入参数 enable: bool
    level: str  # 声明或继续传入参数 level: str
    path: str  # 声明或继续传入参数 path: str
    rotation: str  # 声明或继续传入参数 rotation: str
    retention: str  # 声明或继续传入参数 retention: str


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class Console:  # 定义类 Console，组织相关状态与行为
    """控制台日志配置"""

    enable: bool  # 声明或继续传入参数 enable: bool
    level: str  # 声明或继续传入参数 level: str


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class LoggingConfig:  # 定义类 LoggingConfig，组织相关状态与行为
    """日志总配置"""

    file: File  # 声明或继续传入参数 file: File
    console: Console  # 声明或继续传入参数 console: Console


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class DBConfig:  # 定义类 DBConfig，组织相关状态与行为
    """MySQL 连接配置"""

    host: str  # 声明或继续传入参数 host: str
    port: int  # 声明或继续传入参数 port: int
    user: str  # 声明或继续传入参数 user: str
    password: str  # 声明或继续传入参数 password: str
    database: str  # 声明或继续传入参数 database: str
    pool_size: int  # 声明或继续传入参数 pool_size: int


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class QdrantConfig:  # 定义类 QdrantConfig，组织相关状态与行为
    """Qdrant 连接与向量维度配置"""

    host: str  # 声明或继续传入参数 host: str
    port: int  # 声明或继续传入参数 port: int
    embedding_size: int  # 声明或继续传入参数 embedding_size: int


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class EmbeddingConfig:  # 定义类 EmbeddingConfig，组织相关状态与行为
    """Embedding 服务配置"""

    host: str  # 声明或继续传入参数 host: str
    port: int  # 声明或继续传入参数 port: int
    model: str  # 声明或继续传入参数 model: str


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class ESConfig:  # 定义类 ESConfig，组织相关状态与行为
    """Elasticsearch 配置"""

    host: str  # 声明或继续传入参数 host: str
    port: int  # 声明或继续传入参数 port: int
    index_name: str  # 声明或继续传入参数 index_name: str


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class LLMConfig:  # 定义类 LLMConfig，组织相关状态与行为
    """大模型调用配置"""

    model_name: str  # 声明或继续传入参数 model_name: str
    api_key: str  # 声明或继续传入参数 api_key: str
    base_url: str  # 声明或继续传入参数 base_url: str


@dataclass  # 应用装饰器 dataclass，为紧随其后的定义附加框架行为
class AppConfig:  # 定义类 AppConfig，组织相关状态与行为
    """项目级总配置入口"""

    logging: LoggingConfig  # 声明或继续传入参数 logging: LoggingConfig
    db_meta: DBConfig  # 声明或继续传入参数 db_meta: DBConfig
    db_dw: DBConfig  # 声明或继续传入参数 db_dw: DBConfig
    qdrant: QdrantConfig  # 声明或继续传入参数 qdrant: QdrantConfig
    embedding: EmbeddingConfig  # 声明或继续传入参数 embedding: EmbeddingConfig
    es: ESConfig  # 声明或继续传入参数 es: ESConfig
    llm: LLMConfig  # 声明或继续传入参数 llm: LLMConfig


# 从当前文件位置回到项目根目录，再定位到 conf/app_config.yaml
project_root = Path(__file__).parents[2]  # 计算 Path(__file__).parents[2] 并保存到变量 project_root
config_file = project_root / "conf" / "app_config.yaml"  # 计算 project_root / "conf" / "app_config.yaml" 并保存到变量 config_file

# 先读取本地 .env，让 YAML 中的 ${oc.env:...} 可以解析到敏感配置
load_dotenv(project_root / ".env")  # 调用 load_dotenv 执行当前步骤：load_dotenv(project_root / ".env")

# 读取 YAML 配置内容
context = OmegaConf.load(config_file)  # 计算 OmegaConf.load(config_file) 并保存到变量 context

# 根据 AppConfig 生成结构化配置 schema
schema = OmegaConf.structured(AppConfig)  # 计算 OmegaConf.structured(AppConfig) 并保存到变量 schema

# 把配置结构和配置值合并，再转换成可以直接按属性访问的对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))  # 计算 OmegaConf.to_object(OmegaConf.merge(schema, context)) 并保存到变量 app_config

if __name__ == "__main__":  # 仅在脚本被直接执行时运行本地验证入口
    # 简单测试：验证配置是否能正常读取
    print(app_config.es.host)  # 调用 print 执行当前步骤：print(app_config.es.host)
