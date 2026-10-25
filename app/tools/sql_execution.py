"""Read-oriented MySQL execution with deterministic size and time limits."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
import json  # 导入json，建立本模块需要的外部能力引用
from dataclasses import dataclass  # 从 dataclasses 导入 dataclass，供本模块后续代码使用
from datetime import date, datetime  # 从 datetime 导入 date, datetime，供本模块后续代码使用
from decimal import Decimal  # 从 decimal 导入 Decimal，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from sqlalchemy import text  # 从 sqlalchemy 导入 text，供本模块后续代码使用
from sqlalchemy.ext.asyncio import AsyncEngine  # 从 sqlalchemy.ext.asyncio 导入 AsyncEngine，供本模块后续代码使用
from sqlglot import expressions as exp  # 从 sqlglot 导入 expressions as exp，供本模块后续代码使用
from sqlglot import parse  # 从 sqlglot 导入 parse，供本模块后续代码使用

from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.tools.contracts import SQLTextInput  # 从 app.tools.contracts 导入 SQLTextInput，供本模块后续代码使用


class SQLExecutionError(AppError):  # 定义类 SQLExecutionError，组织相关状态与行为
    def __init__(self, message: str, code: str = "SQL_EXECUTION_FAILED") -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(code=code, message=message, status_code=422)  # 调用 super 执行当前步骤：super().__init__(code=code, message=message, status_code=422)


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class SQLExecutionResult:  # 定义类 SQLExecutionResult，组织相关状态与行为
    columns: list[str]  # 声明或继续传入参数 columns: list[str]
    rows: list[dict[str, Any]]  # 声明或继续传入参数 rows: list[dict[str, Any]]
    row_count: int  # 声明或继续传入参数 row_count: int
    truncated: bool  # 声明或继续传入参数 truncated: bool
    duration_ms: int  # 声明或继续传入参数 duration_ms: int


class MySQLReadTool:  # 定义类 MySQLReadTool，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        engine: AsyncEngine,  # 为函数 __init__ 声明参数 engine 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        timeout_ms: int,  # 为函数 __init__ 声明参数 timeout_ms 及其类型或默认值
        max_rows: int,  # 为函数 __init__ 声明参数 max_rows 及其类型或默认值
        max_bytes: int,  # 为函数 __init__ 声明参数 max_bytes 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.engine = engine  # 将 engine 保存到实例属性 self.engine
        self.timeout_ms = timeout_ms  # 将 timeout_ms 保存到实例属性 self.timeout_ms
        self.max_rows = max_rows  # 将 max_rows 保存到实例属性 self.max_rows
        self.max_bytes = max_bytes  # 将 max_bytes 保存到实例属性 self.max_bytes

    async def explain(self, sql: str) -> tuple[str, int | None]:  # 定义异步函数 explain，封装可被事件循环调度的协程逻辑
        guarded = SQLTextInput(sql=sql).sql.rstrip().rstrip(";")  # 计算 SQLTextInput(sql=sql).sql.rstrip().rstrip(";") 并保存到变量 guarded
        _validate_read_only_sql(guarded)  # 调用 _validate_read_only_sql 执行当前步骤：_validate_read_only_sql(guarded)
        timeout_seconds = max(self.timeout_ms / 1000 + 1, 2)  # 计算 max(self.timeout_ms / 1000 + 1, 2) 并保存到变量 timeout_seconds
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            async with asyncio.timeout(timeout_seconds):  # 进入受管理的上下文 async with asyncio.timeout(timeout_seconds):，确保资源正确获取与释放
                async with self.engine.connect() as connection:  # 进入受管理的上下文 async with self.engine.connect() as connection:，确保资源正确获取与释放
                    await connection.exec_driver_sql(  # 等待异步操作完成并取得结果：connection.exec_driver_sql(
                        f"SET SESSION MAX_EXECUTION_TIME={self.timeout_ms}"  # 在函数 explain 中执行表达式 f"SET SESSION MAX_EXECUTION_TIME={self.timeout_ms}"，推进当前业务流程
                    )  # 结束 connection.exec_driver_sql 调用参数，得到完整表达式结果
                    await connection.exec_driver_sql(  # 等待异步操作完成并取得结果：connection.exec_driver_sql(
                        "SET SESSION TRANSACTION READ ONLY"  # 在函数 explain 中执行表达式 "SET SESSION TRANSACTION READ ONLY"，推进当前业务流程
                    )  # 结束 connection.exec_driver_sql 调用参数，得到完整表达式结果
                    await connection.commit()  # 等待异步操作完成并取得结果：connection.commit()
                    result = await connection.execute(text(f"EXPLAIN {guarded}"))  # 等待 execute 完成，并将其结果保存到 result
                    rows = [dict(row) for row in result.mappings().all()]  # 计算 [dict(row) for row in result.mappings().all()] 并保存到变量 rows
                    await connection.rollback()  # 等待异步操作完成并取得结果：connection.rollback()
        except TimeoutError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError as exc:
            raise SQLExecutionError("SQL validation timed out", "SQL_TIMEOUT") from exc  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError("SQL validation timed out", "SQL_TIMEOUT") from exc
        except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
            raise SQLExecutionError(_safe_db_error(exc), "SQL_VALIDATION_FAILED") from exc  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError(_safe_db_error(exc), "SQL_VALIDATION_FAILED") from exc
        plan = "\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in rows)  # 计算 "\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in r… 并保存到变量 plan
        estimates = [  # 计算 [ 并保存到变量 estimates
            int(row["rows"])  # 调用 int 执行当前步骤：int(row["rows"])
            for row in rows  # 按迭代条件执行循环：for row in rows
            if isinstance(row.get("rows"), (int, float, Decimal))  # 判断分支条件：if isinstance(row.get("rows"), (int, float, Decimal))
        ]  # 结束上一处多行结构，保持表达式边界清晰
        return plan[:20_000], (sum(estimates) if estimates else None)  # 返回 plan[:20_000], (sum(estimates) if estimates else None) 给调用方

    async def execute(self, sql: str) -> SQLExecutionResult:  # 定义异步函数 execute，封装可被事件循环调度的协程逻辑
        guarded = SQLTextInput(sql=sql).sql.rstrip().rstrip(";")  # 计算 SQLTextInput(sql=sql).sql.rstrip().rstrip(";") 并保存到变量 guarded
        statements = _validate_read_only_sql(guarded)  # 计算 _validate_read_only_sql(guarded) 并保存到变量 statements
        expression = statements[0]  # 计算 statements[0] 并保存到变量 expression
        existing_limit = expression.args.get("limit")  # 计算 expression.args.get("limit") 并保存到变量 existing_limit
        should_set_limit = True  # 计算 True 并保存到变量 should_set_limit
        if isinstance(existing_limit, exp.Limit):  # 判断分支条件：if isinstance(existing_limit, exp.Limit):
            limit_expression = existing_limit.expression  # 计算 existing_limit.expression 并保存到变量 limit_expression
            if isinstance(limit_expression, exp.Literal) and limit_expression.is_int:  # 判断分支条件：if isinstance(limit_expression, exp.Literal) and limit_expression.is_in…
                should_set_limit = int(limit_expression.this) > self.max_rows + 1  # 计算 int(limit_expression.this) > self.max_rows + 1 并保存到变量 should_set_limit
        if should_set_limit:  # 判断分支条件：if should_set_limit:
            expression = expression.limit(self.max_rows + 1)  # 计算 expression.limit(self.max_rows + 1) 并保存到变量 expression
        limited_sql = expression.sql(dialect="mysql")  # 计算 expression.sql(dialect="mysql") 并保存到变量 limited_sql
        timeout_seconds = max(self.timeout_ms / 1000 + 1, 2)  # 计算 max(self.timeout_ms / 1000 + 1, 2) 并保存到变量 timeout_seconds
        started = asyncio.get_running_loop().time()  # 计算 asyncio.get_running_loop().time() 并保存到变量 started
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            async with asyncio.timeout(timeout_seconds):  # 进入受管理的上下文 async with asyncio.timeout(timeout_seconds):，确保资源正确获取与释放
                async with self.engine.connect() as connection:  # 进入受管理的上下文 async with self.engine.connect() as connection:，确保资源正确获取与释放
                    await connection.exec_driver_sql(  # 等待异步操作完成并取得结果：connection.exec_driver_sql(
                        f"SET SESSION MAX_EXECUTION_TIME={self.timeout_ms}"  # 在函数 execute 中执行表达式 f"SET SESSION MAX_EXECUTION_TIME={self.timeout_ms}"，推进当前业务流程
                    )  # 结束 connection.exec_driver_sql 调用参数，得到完整表达式结果
                    await connection.exec_driver_sql(  # 等待异步操作完成并取得结果：connection.exec_driver_sql(
                        "SET SESSION TRANSACTION READ ONLY"  # 在函数 execute 中执行表达式 "SET SESSION TRANSACTION READ ONLY"，推进当前业务流程
                    )  # 结束 connection.exec_driver_sql 调用参数，得到完整表达式结果
                    await connection.commit()  # 等待异步操作完成并取得结果：connection.commit()
                    result = await connection.execute(text(limited_sql))  # 等待 execute 完成，并将其结果保存到 result
                    mappings = result.mappings()  # 计算 result.mappings() 并保存到变量 mappings
                    columns = [str(key) for key in result.keys()]  # 计算 [str(key) for key in result.keys()] 并保存到变量 columns
                    rows = [  # 计算 [ 并保存到变量 rows
                        _json_safe(dict(row))  # 调用 _json_safe 执行当前步骤：_json_safe(dict(row))
                        for row in mappings.fetchmany(self.max_rows + 1)  # 按迭代条件执行循环：for row in mappings.fetchmany(self.max_rows + 1)
                    ]  # 结束上一处多行结构，保持表达式边界清晰
                    await connection.rollback()  # 等待异步操作完成并取得结果：connection.rollback()
        except TimeoutError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except TimeoutError as exc:
            raise SQLExecutionError("SQL execution timed out", "SQL_TIMEOUT") from exc  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError("SQL execution timed out", "SQL_TIMEOUT") from exc
        except Exception as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as exc:
            raise SQLExecutionError(_safe_db_error(exc)) from exc  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError(_safe_db_error(exc)) from exc

        truncated = len(rows) > self.max_rows  # 计算 len(rows) > self.max_rows 并保存到变量 truncated
        rows = rows[: self.max_rows]  # 计算 rows[: self.max_rows] 并保存到变量 rows
        encoded_bytes = 0  # 计算 0 并保存到变量 encoded_bytes
        accepted: list[dict[str, Any]] = []  # 计算 [] 并保存到变量 accepted
        for row in rows:  # 按迭代条件执行循环：for row in rows:
            row_bytes = len(  # 调用 len 构造结果并保存到 row_bytes
                json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")  # 调用 dumps 执行当前步骤：json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")
            )  # 结束 len 调用参数，得到完整表达式结果
            if encoded_bytes + row_bytes > self.max_bytes:  # 判断分支条件：if encoded_bytes + row_bytes > self.max_bytes:
                truncated = True  # 计算 True 并保存到变量 truncated
                break  # 提前结束当前循环并继续后续控制流
            accepted.append(row)  # 调用 append 执行当前步骤：accepted.append(row)
            encoded_bytes += row_bytes  # 计算 row_bytes 并保存到变量 encoded_bytes +
        columns = columns  # 计算 columns 并保存到变量 columns
        duration_ms = int((asyncio.get_running_loop().time() - started) * 1000)  # 计算 int((asyncio.get_running_loop().time() - started) * 1000) 并保存到变量 duration_ms
        return SQLExecutionResult(  # 返回 SQLExecutionResult( 给调用方
            columns=columns,  # 为 SQLExecutionResult 设置关键字参数 columns，传入当前行给出的值
            rows=accepted,  # 为 SQLExecutionResult 设置关键字参数 rows，传入当前行给出的值
            row_count=len(accepted),  # 为 len 设置关键字参数 row_count，传入当前行给出的值
            truncated=truncated,  # 为 SQLExecutionResult 设置关键字参数 truncated，传入当前行给出的值
            duration_ms=duration_ms,  # 为 SQLExecutionResult 设置关键字参数 duration_ms，传入当前行给出的值
        )  # 结束 SQLExecutionResult 调用参数，得到完整表达式结果


def _json_safe(value: Any) -> Any:  # 定义函数 _json_safe，封装该模块的一项明确职责
    if isinstance(value, dict):  # 判断分支条件：if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}  # 返回 {str(key): _json_safe(item) for key, item in value.items()} 给调用方
    if isinstance(value, list):  # 判断分支条件：if isinstance(value, list):
        return [_json_safe(item) for item in value]  # 返回 [_json_safe(item) for item in value] 给调用方
    if isinstance(value, Decimal):  # 判断分支条件：if isinstance(value, Decimal):
        return str(value)  # 返回 str(value) 给调用方
    if isinstance(value, (datetime, date)):  # 判断分支条件：if isinstance(value, (datetime, date)):
        return value.isoformat()  # 返回 value.isoformat() 给调用方
    if isinstance(value, (str, int, float, bool)) or value is None:  # 判断分支条件：if isinstance(value, (str, int, float, bool)) or value is None:
        return value  # 返回 value 给调用方
    return str(value)  # 返回 str(value) 给调用方


def _safe_db_error(exc: Exception) -> str:  # 定义函数 _safe_db_error，封装该模块的一项明确职责
    message = str(exc).splitlines()[0]  # 计算 str(exc).splitlines()[0] 并保存到变量 message
    return message[:500] if message else "database operation failed"  # 返回 message[:500] if message else "database operation failed" 给调用方


def _validate_read_only_sql(sql: str) -> list[exp.Expression]:  # 定义函数 _validate_read_only_sql，封装该模块的一项明确职责
    statements = parse(sql, read="mysql")  # 计算 parse(sql, read="mysql") 并保存到变量 statements
    if len(statements) != 1 or not isinstance(  # 判断分支条件：if len(statements) != 1 or not isinstance(
        statements[0], (exp.Select, exp.Union)  # 调用 目标函数 执行当前步骤：statements[0], (exp.Select, exp.Union)
    ):  # 结束 _validate_read_only_sql 的参数列表并声明返回类型
        raise SQLExecutionError(  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError(
            "only one read-only query may be executed",  # 继续向上一处调用或声明传入 "only one read-only query may be executed"
            "SQL_POLICY_VIOLATION",  # 继续向上一处调用或声明传入 "SQL_POLICY_VIOLATION"
        )  # 结束 SQLExecutionError 调用参数，得到完整表达式结果
    for node_type in (  # 按迭代条件执行循环：for node_type in (
        exp.Insert,  # 向多行序列加入元素 exp.Insert
        exp.Update,  # 向多行序列加入元素 exp.Update
        exp.Delete,  # 向多行序列加入元素 exp.Delete
        exp.Create,  # 向多行序列加入元素 exp.Create
        exp.Drop,  # 向多行序列加入元素 exp.Drop
        exp.Alter,  # 向多行序列加入元素 exp.Alter
        exp.Merge,  # 向多行序列加入元素 exp.Merge
        exp.Command,  # 向多行序列加入元素 exp.Command
    ):  # 结束 _validate_read_only_sql 的参数列表并声明返回类型
        if statements[0].find(node_type) is not None:  # 判断分支条件：if statements[0].find(node_type) is not None:
            raise SQLExecutionError(  # 抛出明确异常，阻止错误状态被静默接受：SQLExecutionError(
                "data-changing statements are forbidden",  # 继续向上一处调用或声明传入 "data-changing statements are forbidden"
                "SQL_POLICY_VIOLATION",  # 继续向上一处调用或声明传入 "SQL_POLICY_VIOLATION"
            )  # 结束 SQLExecutionError 调用参数，得到完整表达式结果
    return statements  # 返回 statements 给调用方
