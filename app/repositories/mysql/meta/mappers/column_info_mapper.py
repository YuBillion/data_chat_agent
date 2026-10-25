"""
ColumnInfo 映射器

负责在字段元数据业务实体和 ORM 模型之间做转换，使字段入库过程保持
“业务实体 -> Mapper -> ORM 模型”的清晰分层
"""

from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用

from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用
from app.models.column_info import ColumnInfoMySQL  # 从 app.models.column_info 导入 ColumnInfoMySQL，供本模块后续代码使用


class ColumnInfoMapper:  # 定义类 ColumnInfoMapper，组织相关状态与行为
    """负责 `ColumnInfo` 与 `ColumnInfoMySQL` 之间的双向转换"""

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_entity(column_info_mysql: ColumnInfoMySQL) -> ColumnInfo:  # 定义函数 to_entity，封装该模块的一项明确职责
        """把 ORM 模型转换回字段业务实体"""
        return ColumnInfo(  # 返回 ColumnInfo( 给调用方
            id=column_info_mysql.id,  # 为 ColumnInfo 设置关键字参数 id，传入当前行给出的值
            name=column_info_mysql.name,  # 为 ColumnInfo 设置关键字参数 name，传入当前行给出的值
            type=column_info_mysql.type,  # 为 ColumnInfo 设置关键字参数 type，传入当前行给出的值
            role=column_info_mysql.role,  # 为 ColumnInfo 设置关键字参数 role，传入当前行给出的值
            examples=column_info_mysql.examples,  # 为 ColumnInfo 设置关键字参数 examples，传入当前行给出的值
            description=column_info_mysql.description,  # 为 ColumnInfo 设置关键字参数 description，传入当前行给出的值
            alias=column_info_mysql.alias,  # 为 ColumnInfo 设置关键字参数 alias，传入当前行给出的值
            table_id=column_info_mysql.table_id,  # 为 ColumnInfo 设置关键字参数 table_id，传入当前行给出的值
        )  # 结束 ColumnInfo 调用参数，得到完整表达式结果

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_model(column_info: ColumnInfo) -> ColumnInfoMySQL:  # 定义函数 to_model，封装该模块的一项明确职责
        """把字段业务实体转换成 ORM 模型用于持久化"""
        return ColumnInfoMySQL(**asdict(column_info))  # 返回 ColumnInfoMySQL(**asdict(column_info)) 给调用方
