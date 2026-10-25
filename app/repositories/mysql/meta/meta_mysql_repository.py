"""
元数据库 MySQL 仓储

这一层对应文档里的 Meta Repository，负责接收业务实体并落到 Meta MySQL
Repository 自身只关心“如何写入”，而“哪些写操作要放在同一笔事务里”，由 Service 层统一决定

表 字段 指标和字段指标关系都会先以业务实体流转，再在这里统一转成 ORM 模型
问数链路运行时也会从这里读取元数据，用来把召回到的 id 补齐成完整实体
"""

from sqlalchemy import select  # 从 sqlalchemy 导入 select，供本模块后续代码使用
from sqlalchemy.ext.asyncio import AsyncSession  # 从 sqlalchemy.ext.asyncio 导入 AsyncSession，供本模块后续代码使用

from app.entities.column_info import ColumnInfo  # 从 app.entities.column_info 导入 ColumnInfo，供本模块后续代码使用
from app.entities.column_metric import ColumnMetric  # 从 app.entities.column_metric 导入 ColumnMetric，供本模块后续代码使用
from app.entities.metric_info import MetricInfo  # 从 app.entities.metric_info 导入 MetricInfo，供本模块后续代码使用
from app.entities.table_info import TableInfo  # 从 app.entities.table_info 导入 TableInfo，供本模块后续代码使用
from app.models.column_info import ColumnInfoMySQL  # 从 app.models.column_info 导入 ColumnInfoMySQL，供本模块后续代码使用
from app.models.metric_info import MetricInfoMySQL  # 从 app.models.metric_info 导入 MetricInfoMySQL，供本模块后续代码使用
from app.models.table_info import TableInfoMySQL  # 从 app.models.table_info 导入 TableInfoMySQL，供本模块后续代码使用
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper  # 从 app.repositories.mysql.meta.mappers.column_info_mapper 导入 ColumnInfoMapper，供本模块后续代码使用
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper  # 从 app.repositories.mysql.meta.mappers.column_metric_mapper 导入 ColumnMetricMapper，供本模块后续代码使用
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper  # 从 app.repositories.mysql.meta.mappers.metric_info_mapper 导入 MetricInfoMapper，供本模块后续代码使用
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper  # 从 app.repositories.mysql.meta.mappers.table_info_mapper 导入 TableInfoMapper，供本模块后续代码使用


class MetaMySQLRepository:  # 定义类 MetaMySQLRepository，组织相关状态与行为
    """负责把元数据业务实体持久化到 Meta MySQL"""

    def __init__(self, session: AsyncSession):  # 定义函数 __init__，封装该模块的一项明确职责
        self.session = session  # 将 session 保存到实例属性 self.session

    def save_table_infos(self, table_infos: list[TableInfo]):  # 定义函数 save_table_infos，封装该模块的一项明确职责
        """批量保存表元数据。输入仍然是业务实体，而不是 ORM 模型"""
        self.session.add_all(  # 调用 add_all 执行当前步骤：self.session.add_all(
            [TableInfoMapper.to_model(table_info) for table_info in table_infos]  # 调用 目标函数 执行当前步骤：[TableInfoMapper.to_model(table_info) for table_info in table_infos]
        )  # 结束 self.session.add_all 调用参数，得到完整表达式结果

    def save_column_infos(self, column_infos: list[ColumnInfo]):  # 定义函数 save_column_infos，封装该模块的一项明确职责
        """批量保存字段元数据。实体到模型的转换统一通过 Mapper 完成"""
        self.session.add_all(  # 调用 add_all 执行当前步骤：self.session.add_all(
            [ColumnInfoMapper.to_model(column_info) for column_info in column_infos]  # 调用 目标函数 执行当前步骤：[ColumnInfoMapper.to_model(column_info) for column_info in column_infos]
        )  # 结束 self.session.add_all 调用参数，得到完整表达式结果

    def save_metric_infos(self, metric_infos: list[MetricInfo]):  # 定义函数 save_metric_infos，封装该模块的一项明确职责
        """批量保存指标元数据。指标本身和字段关联关系分开写入"""
        self.session.add_all(  # 调用 add_all 执行当前步骤：self.session.add_all(
            [MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos]  # 调用 目标函数 执行当前步骤：[MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos]
        )  # 结束 self.session.add_all 调用参数，得到完整表达式结果

    def save_column_metrics(self, column_metrics: list[ColumnMetric]):  # 定义函数 save_column_metrics，封装该模块的一项明确职责
        """批量保存字段与指标的关联关系"""
        self.session.add_all(  # 调用 add_all 执行当前步骤：self.session.add_all(
            [  # 在函数 save_column_metrics 中执行表达式 [，推进当前业务流程
                ColumnMetricMapper.to_model(column_metric)  # 调用 to_model 执行当前步骤：ColumnMetricMapper.to_model(column_metric)
                for column_metric in column_metrics  # 按迭代条件执行循环：for column_metric in column_metrics
            ]  # 结束上一处多行结构，保持表达式边界清晰
        )  # 结束 self.session.add_all 调用参数，得到完整表达式结果

    async def get_column_info_by_id(self, id: str) -> ColumnInfo | None:  # 定义异步函数 get_column_info_by_id，封装可被事件循环调度的协程逻辑
        """按字段 id 查询字段元数据，供召回信息合并阶段补齐字段上下文"""

        column_info: ColumnInfoMySQL | None = await self.session.get(  # 等待 get 完成，并将其结果保存到 column_info
            ColumnInfoMySQL, id  # 在函数 get_column_info_by_id 中执行表达式 ColumnInfoMySQL, id，推进当前业务流程
        )  # 结束 self.session.get 调用参数，得到完整表达式结果
        if column_info:  # 判断分支条件：if column_info:
            return ColumnInfoMapper.to_entity(column_info)  # 返回 ColumnInfoMapper.to_entity(column_info) 给调用方
        else:  # 进入前面条件均不成立时的兜底分支
            return None  # 返回 None 给调用方

    async def get_table_info_by_id(self, id: str) -> TableInfo | None:  # 定义异步函数 get_table_info_by_id，封装可被事件循环调度的协程逻辑
        """按表 id 查询表元数据，最终组装成提示词里的表结构信息"""

        table_info: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, id)  # 等待 get 完成，并将其结果保存到 table_info
        if table_info:  # 判断分支条件：if table_info:
            return TableInfoMapper.to_entity(table_info)  # 返回 TableInfoMapper.to_entity(table_info) 给调用方
        else:  # 进入前面条件均不成立时的兜底分支
            return None  # 返回 None 给调用方

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:  # 定义异步函数 get_key_columns_by_table_id，封装可被事件循环调度的协程逻辑
        """查询指定表的主外键字段，避免 Join 关键字段被向量召回漏掉"""

        # 主外键字段用于后续生成 join 条件，不能完全依赖向量召回命中
        # 这里走 ORM 查询而不是裸 SQL：column_info 的 examples / alias 是 JSON 列，
        # 只有带上 ORM 列类型信息，SQLAlchemy 才会把 JSON 字符串反序列化成 list，
        # 和 get_column_info_by_id() 保持一致的返回值形态
        stmt = select(ColumnInfoMySQL).where(  # 调用 select 构造结果并保存到 stmt
            ColumnInfoMySQL.table_id == table_id,  # 继续向上一处调用或声明传入 ColumnInfoMySQL.table_id == table_id
            ColumnInfoMySQL.role.in_(("primary_key", "foreign_key")),  # 向多行序列加入元素 ColumnInfoMySQL.role.in_(("primary_key", "foreign_key"))
        )  # 结束 where 调用参数，得到完整表达式结果
        result = await self.session.scalars(stmt)  # 等待 scalars 完成，并将其结果保存到 result
        return [ColumnInfoMapper.to_entity(model) for model in result.all()]  # 返回 [ColumnInfoMapper.to_entity(model) for model in result.all()] 给调用方

    async def list_table_infos(self, limit: int = 100) -> list[TableInfo]:  # 定义异步函数 list_table_infos，封装可被事件循环调度的协程逻辑
        """List catalog tables for metadata-only Agent responses."""

        result = await self.session.scalars(  # 等待 scalars 完成，并将其结果保存到 result
            select(TableInfoMySQL).order_by(TableInfoMySQL.id).limit(limit)  # 调用 select 执行当前步骤：select(TableInfoMySQL).order_by(TableInfoMySQL.id).limit(limit)
        )  # 结束 self.session.scalars 调用参数，得到完整表达式结果
        return [TableInfoMapper.to_entity(model) for model in result.all()]  # 返回 [TableInfoMapper.to_entity(model) for model in result.all()] 给调用方

    async def list_metric_infos(self, limit: int = 100) -> list[MetricInfo]:  # 定义异步函数 list_metric_infos，封装可被事件循环调度的协程逻辑
        """List metric definitions for metadata-only Agent responses."""

        result = await self.session.scalars(  # 等待 scalars 完成，并将其结果保存到 result
            select(MetricInfoMySQL).order_by(MetricInfoMySQL.id).limit(limit)  # 调用 select 执行当前步骤：select(MetricInfoMySQL).order_by(MetricInfoMySQL.id).limit(limit)
        )  # 结束 self.session.scalars 调用参数，得到完整表达式结果
        return [MetricInfoMapper.to_entity(model) for model in result.all()]  # 返回 [MetricInfoMapper.to_entity(model) for model in result.all()] 给调用方

    async def list_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:  # 定义异步函数 list_columns_by_table_id，封装可被事件循环调度的协程逻辑
        """List all columns for one catalog table."""

        result = await self.session.scalars(  # 等待 scalars 完成，并将其结果保存到 result
            select(ColumnInfoMySQL)  # 调用 select 执行当前步骤：select(ColumnInfoMySQL)
            .where(ColumnInfoMySQL.table_id == table_id)  # 调用 目标函数 执行当前步骤：.where(ColumnInfoMySQL.table_id == table_id)
            .order_by(ColumnInfoMySQL.id)  # 调用 目标函数 执行当前步骤：.order_by(ColumnInfoMySQL.id)
        )  # 结束 self.session.scalars 调用参数，得到完整表达式结果
        return [ColumnInfoMapper.to_entity(model) for model in result.all()]  # 返回 [ColumnInfoMapper.to_entity(model) for model in result.all()] 给调用方
