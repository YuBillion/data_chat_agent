"""
TableInfo 映射器

负责在表元数据业务实体和 ORM 模型之间做双向转换，让 Service/Repository
不需要直接操作 SQLAlchemy 模型
"""

from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用

from app.entities.table_info import TableInfo  # 从 app.entities.table_info 导入 TableInfo，供本模块后续代码使用
from app.models.table_info import TableInfoMySQL  # 从 app.models.table_info 导入 TableInfoMySQL，供本模块后续代码使用


class TableInfoMapper:  # 定义类 TableInfoMapper，组织相关状态与行为
    """负责 `TableInfo` 与 `TableInfoMySQL` 之间的双向转换"""

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_entity(table_info_mysql: TableInfoMySQL) -> TableInfo:  # 定义函数 to_entity，封装该模块的一项明确职责
        """把 ORM 模型还原成业务实体，便于上层业务逻辑继续流转"""
        return TableInfo(  # 返回 TableInfo( 给调用方
            id=table_info_mysql.id,  # 为 TableInfo 设置关键字参数 id，传入当前行给出的值
            name=table_info_mysql.name,  # 为 TableInfo 设置关键字参数 name，传入当前行给出的值
            role=table_info_mysql.role,  # 为 TableInfo 设置关键字参数 role，传入当前行给出的值
            description=table_info_mysql.description,  # 为 TableInfo 设置关键字参数 description，传入当前行给出的值
        )  # 结束 TableInfo 调用参数，得到完整表达式结果

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_model(table_info: TableInfo) -> TableInfoMySQL:  # 定义函数 to_model，封装该模块的一项明确职责
        """把业务实体转换成 ORM 模型，交给 SQLAlchemy 托管"""
        return TableInfoMySQL(**asdict(table_info))  # 返回 TableInfoMySQL(**asdict(table_info)) 给调用方
