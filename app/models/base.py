"""
ORM 基类

定义项目中所有 SQLAlchemy ORM 模型共享的声明式基类
后续 table_info column_info metric_info 和 column_metric 都会继承这里的 Base
"""

from sqlalchemy.orm import DeclarativeBase  # 从 sqlalchemy.orm 导入 DeclarativeBase，供本模块后续代码使用


class Base(DeclarativeBase):  # 定义类 Base，组织相关状态与行为
    """项目统一的 SQLAlchemy 声明式基类"""

    pass  # 使用空语句保持当前语法块完整，不执行额外业务动作
