"""
ColumnMetric 映射器

负责字段与指标关联关系的实体/模型转换，延续元数据模块统一的 Mapper
分层做法，避免上层直接依赖 ORM 细节
"""

from dataclasses import asdict  # 从 dataclasses 导入 asdict，供本模块后续代码使用

from app.entities.column_metric import ColumnMetric  # 从 app.entities.column_metric 导入 ColumnMetric，供本模块后续代码使用
from app.models.column_metric import ColumnMetricMySQL  # 从 app.models.column_metric 导入 ColumnMetricMySQL，供本模块后续代码使用


class ColumnMetricMapper:  # 定义类 ColumnMetricMapper，组织相关状态与行为
    """负责 `ColumnMetric` 与 `ColumnMetricMySQL` 之间的双向转换"""

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_entity(column_metric_mysql: ColumnMetricMySQL) -> ColumnMetric:  # 定义函数 to_entity，封装该模块的一项明确职责
        """把关联关系 ORM 模型转换为业务实体"""
        return ColumnMetric(  # 返回 ColumnMetric( 给调用方
            column_id=column_metric_mysql.column_id,  # 为 ColumnMetric 设置关键字参数 column_id，传入当前行给出的值
            metric_id=column_metric_mysql.metric_id,  # 为 ColumnMetric 设置关键字参数 metric_id，传入当前行给出的值
        )  # 结束 ColumnMetric 调用参数，得到完整表达式结果

    @staticmethod  # 应用装饰器 staticmethod，为紧随其后的定义附加框架行为
    def to_model(column_metric: ColumnMetric) -> ColumnMetricMySQL:  # 定义函数 to_model，封装该模块的一项明确职责
        """把关联关系业务实体转换为 ORM 模型"""
        return ColumnMetricMySQL(**asdict(column_metric))  # 返回 ColumnMetricMySQL(**asdict(column_metric)) 给调用方
