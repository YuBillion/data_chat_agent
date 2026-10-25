"""Validated input contracts for deterministic agent tools."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from pydantic import BaseModel, ConfigDict, Field  # 从 pydantic 导入 BaseModel, ConfigDict, Field，供本模块后续代码使用


class SQLTextInput(BaseModel):  # 定义类 SQLTextInput，组织相关状态与行为
    model_config = ConfigDict(extra="forbid")  # 计算 ConfigDict(extra="forbid") 并保存到变量 model_config

    sql: str = Field(min_length=1, max_length=50_000)  # 计算 Field(min_length=1, max_length=50_000) 并保存到变量 sql


class SQLInspectionInput(SQLTextInput):  # 定义类 SQLInspectionInput，组织相关状态与行为
    allowed_tables: list[str] = Field(default_factory=list, max_length=500)  # 计算 Field(default_factory=list, max_length=500) 并保存到变量 allowed_tables
    allowed_columns: list[str] = Field(default_factory=list, max_length=10_000)  # 计算 Field(default_factory=list, max_length=10_000) 并保存到变量 allowed_columns
    corrected: bool = False  # 计算 False 并保存到变量 corrected
    estimated_rows: int | None = Field(default=None, ge=0)  # 计算 Field(default=None, ge=0) 并保存到变量 estimated_rows
