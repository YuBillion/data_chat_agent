"""
MetricInfo 映射器

虽然本章重点是表与字段入库，但指标元数据也沿用同样的分层约定：
先以业务实体表达，再通过 Mapper 转成 ORM 模型
"""

from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用

from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用
from app.models.metric_info import MetricInfoMySQL  # 从 app.models.metric_info 导入 MetricInfoMySQL，供本模块后续代码使用


class MetricInfoMapper:  # 定义类 MetricInfoMapper，组织相关状态与行为
    """负责 `MetricInfo` 与 `MetricInfoMySQL` 之间的双向转换"""

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_entity(model: MetricInfoMySQL) -> MetricInfo:  # 定义函数 to_entity，封装该模块的一项明确职责
        """把指标 ORM 模型转换为业务实体"""
        return MetricInfo(  # 返回 MetricInfo( 给调用方
            id=model.id,  # 为 MetricInfo 设置关键字参数 id，传入当前行给出的值
            name=model.name,  # 为 MetricInfo 设置关键字参数 name，传入当前行给出的值
            description=model.description,  # 为 MetricInfo 设置关键字参数 description，传入当前行给出的值
            relevant_columns=model.relevant_columns,  # 为 MetricInfo 设置关键字参数 relevant_columns，传入当前行给出的值
            alias=model.alias,  # 为 MetricInfo 设置关键字参数 alias，传入当前行给出的值
        )  # 结束 MetricInfo 调用参数，得到完整表达式结果

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_model(entity: MetricInfo) -> MetricInfoMySQL:  # 定义函数 to_model，封装该模块的一项明确职责
        """把指标业务实体转换为 ORM 模型"""
        return MetricInfoMySQL(**asdict(entity))  # 返回 MetricInfoMySQL(**asdict(entity)) 给调用方
