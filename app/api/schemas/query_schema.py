"""
问数接口请求体定义

集中声明 API 层输入输出的数据结构，让路由函数只处理业务流程，
字段校验和 OpenAPI 文档生成交给 Pydantic 与 FastAPI 完成。
"""

from pydantic import BaseModel, Field, field_validator  # 从 pydantic 导入 BaseModel, Field, field_validator，供本模块后续代码使用


class QuerySchema(BaseModel):  # 定义类 QuerySchema，组织相关状态与行为
    """`/api/query` 请求体，承载用户输入的自然语言问题"""

    # 前端请求体中的 query 字段，例如 {"query": "统计华北地区销售额"}
    query: str = Field(min_length=1, max_length=4000)  # 计算 Field(min_length=1, max_length=4000) 并保存到变量 query

    @field_validator("query")  # 应用装饰器 field_validator("query")，为紧随其后的定义附加框架行为
    @classmethod  # 应用装饰器 classmethod，为紧随其后的定义附加框架行为
    def normalize_query(cls, value: str) -> str:  # 定义函数 normalize_query，封装该模块的一项明确职责
        normalized = value.strip()  # 计算 value.strip() 并保存到变量 normalized
        if not normalized:  # 判断分支条件：if not normalized:
            raise ValueError("query must not be blank")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("query must not be blank")
        return normalized  # 返回 normalized 给调用方
