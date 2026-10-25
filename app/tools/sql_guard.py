"""Deterministic SQL policy enforcement independent from model decisions."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import hashlib  # 导入hashlib，建立本模块需要的外部能力引用
from dataclasses import dataclass, field  # 从 dataclasses 导入 dataclass, field，供本模块后续代码使用
from typing import Iterable  # 从 typing 导入 Iterable，供本模块后续代码使用

from sqlglot import exp, parse  # 从 sqlglot 导入 exp, parse，供本模块后续代码使用
from sqlglot.errors import ParseError  # 从 sqlglot.errors 导入 ParseError，供本模块后续代码使用

from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用
from app.tools.contracts import SQLInspectionInput  # 从 app.tools.contracts 导入 SQLInspectionInput，供本模块后续代码使用

DANGEROUS_FUNCTIONS = frozenset(  # 调用 frozenset 构造结果并保存到 DANGEROUS_FUNCTIONS
    {  # 执行源码表达式 {，完成本行对应的语义动作
        "benchmark",  # 向多行序列加入元素 "benchmark"
        "get_lock",  # 向多行序列加入元素 "get_lock"
        "load_file",  # 向多行序列加入元素 "load_file"
        "release_lock",  # 向多行序列加入元素 "release_lock"
        "sleep",  # 向多行序列加入元素 "sleep"
        "sys_exec",  # 向多行序列加入元素 "sys_exec"
        "sys_eval",  # 向多行序列加入元素 "sys_eval"
    }  # 结束上一处多行结构，保持表达式边界清晰
)  # 结束 frozenset 调用参数，得到完整表达式结果


class SQLPolicyError(AppError):  # 定义类 SQLPolicyError，组织相关状态与行为
    def __init__(self, reason: str, code: str = "SQL_POLICY_VIOLATION") -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(code=code, message=reason, status_code=422)  # 调用 super 执行当前步骤：super().__init__(code=code, message=reason, status_code=422)


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class SQLRiskAssessment:  # 定义类 SQLRiskAssessment，组织相关状态与行为
    allowed: bool  # 声明或继续传入参数 allowed: bool
    normalized_sql: str  # 声明或继续传入参数 normalized_sql: str
    sql_hash: str  # 声明或继续传入参数 sql_hash: str
    tables: list[str] = field(default_factory=list)  # 计算 field(default_factory=list) 并保存到变量 tables
    columns: list[str] = field(default_factory=list)  # 计算 field(default_factory=list) 并保存到变量 columns
    reasons: list[str] = field(default_factory=list)  # 计算 field(default_factory=list) 并保存到变量 reasons
    high_risk: bool = False  # 计算 False 并保存到变量 high_risk
    approval_required: bool = False  # 计算 False 并保存到变量 approval_required


class SQLGuard:  # 定义类 SQLGuard，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        sensitive_columns: Iterable[str] = (),  # 为函数 __init__ 声明参数 sensitive_columns 及其类型或默认值
        approval_scan_rows: int = 100_000,  # 为函数 __init__ 声明参数 approval_scan_rows 及其类型或默认值
        high_risk_scan_rows: int = 1_000_000,  # 为函数 __init__ 声明参数 high_risk_scan_rows 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.sensitive_columns = frozenset(  # 调用 frozenset 构造结果并保存到 self.sensitive_columns
            item.lower() for item in sensitive_columns  # 调用 lower 执行当前步骤：item.lower() for item in sensitive_columns
        )  # 结束 frozenset 调用参数，得到完整表达式结果
        self.approval_scan_rows = approval_scan_rows  # 将 approval_scan_rows 保存到实例属性 self.approval_scan_rows
        self.high_risk_scan_rows = high_risk_scan_rows  # 将 high_risk_scan_rows 保存到实例属性 self.high_risk_scan_rows

    def inspect(  # 定义函数 inspect，封装该模块的一项明确职责
        self,  # 为函数 inspect 声明参数 self 及其类型或默认值
        sql: str,  # 为函数 inspect 声明参数 sql 及其类型或默认值
        *,  # 为函数 inspect 声明参数 * 及其类型或默认值
        allowed_tables: Iterable[str],  # 为函数 inspect 声明参数 allowed_tables 及其类型或默认值
        allowed_columns: Iterable[str],  # 为函数 inspect 声明参数 allowed_columns 及其类型或默认值
        corrected: bool = False,  # 为函数 inspect 声明参数 corrected 及其类型或默认值
        estimated_rows: int | None = None,  # 为函数 inspect 声明参数 estimated_rows 及其类型或默认值
    ) -> SQLRiskAssessment:  # 结束 inspect 的参数列表并声明返回类型
        request = SQLInspectionInput(  # 调用 SQLInspectionInput 构造结果并保存到 request
            sql=sql,  # 为 SQLInspectionInput 设置关键字参数 sql，传入当前行给出的值
            allowed_tables=list(allowed_tables),  # 为 list 设置关键字参数 allowed_tables，传入当前行给出的值
            allowed_columns=list(allowed_columns),  # 为 list 设置关键字参数 allowed_columns，传入当前行给出的值
            corrected=corrected,  # 为 SQLInspectionInput 设置关键字参数 corrected，传入当前行给出的值
            estimated_rows=estimated_rows,  # 为 SQLInspectionInput 设置关键字参数 estimated_rows，传入当前行给出的值
        )  # 结束 SQLInspectionInput 调用参数，得到完整表达式结果
        raw = request.sql.strip()  # 计算 request.sql.strip() 并保存到变量 raw
        if raw.endswith(";"):  # 判断分支条件：if raw.endswith(";"):
            raw = raw[:-1].rstrip()  # 计算 raw[:-1].rstrip() 并保存到变量 raw
        if not raw:  # 判断分支条件：if not raw:
            raise SQLPolicyError("SQL is empty")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError("SQL is empty")
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            statements = parse(raw, read="mysql")  # 计算 parse(raw, read="mysql") 并保存到变量 statements
        except ParseError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except ParseError as exc:
            raise SQLPolicyError(  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(
                "SQL cannot be parsed for MySQL", code="SQL_PARSE_ERROR"  # 在函数 inspect 中执行表达式 "SQL cannot be parsed for MySQL", code="SQL_PARSE_ERROR"，推进当前业务流程
            ) from exc  # 在函数 inspect 中执行表达式 ) from exc，推进当前业务流程
        if len(statements) != 1:  # 判断分支条件：if len(statements) != 1:
            raise SQLPolicyError("only one SQL statement is allowed")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError("only one SQL statement is allowed")
        expression = statements[0]  # 计算 statements[0] 并保存到变量 expression
        if not isinstance(expression, (exp.Select, exp.Union)):  # 判断分支条件：if not isinstance(expression, (exp.Select, exp.Union)):
            raise SQLPolicyError("only SELECT/UNION/CTE queries are allowed")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError("only SELECT/UNION/CTE queries are allowed")
        forbidden_nodes = (  # 调用 目标函数 构造结果并保存到 forbidden_nodes
            exp.Insert,  # 向多行序列加入元素 exp.Insert
            exp.Update,  # 向多行序列加入元素 exp.Update
            exp.Delete,  # 向多行序列加入元素 exp.Delete
            exp.Create,  # 向多行序列加入元素 exp.Create
            exp.Drop,  # 向多行序列加入元素 exp.Drop
            exp.Alter,  # 向多行序列加入元素 exp.Alter
            exp.Merge,  # 向多行序列加入元素 exp.Merge
            exp.Command,  # 向多行序列加入元素 exp.Command
            exp.Transaction,  # 向多行序列加入元素 exp.Transaction
        )  # 结束函数 inspect 的调用或声明结构
        if any(expression.find(node_type) is not None for node_type in forbidden_nodes):  # 判断分支条件：if any(expression.find(node_type) is not None for node_type in forbidde…
            raise SQLPolicyError("data-changing statements are forbidden")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError("data-changing statements are forbidden")
        if expression.find(exp.Into) or expression.find(exp.Lock):  # 判断分支条件：if expression.find(exp.Into) or expression.find(exp.Lock):
            raise SQLPolicyError("SELECT INTO and row locking are forbidden")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError("SELECT INTO and row locking are forbidden")
        for function in expression.find_all(exp.Func):  # 按迭代条件执行循环：for function in expression.find_all(exp.Func):
            function_name = function.sql_name().lower()  # 计算 function.sql_name().lower() 并保存到变量 function_name
            if function_name in DANGEROUS_FUNCTIONS:  # 判断分支条件：if function_name in DANGEROUS_FUNCTIONS:
                raise SQLPolicyError(f"function is forbidden: {function_name}")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(f"function is forbidden: {function_name}")
        for function in expression.find_all(exp.Anonymous):  # 按迭代条件执行循环：for function in expression.find_all(exp.Anonymous):
            function_name = str(function.name).lower()  # 计算 str(function.name).lower() 并保存到变量 function_name
            if function_name in DANGEROUS_FUNCTIONS:  # 判断分支条件：if function_name in DANGEROUS_FUNCTIONS:
                raise SQLPolicyError(f"function is forbidden: {function_name}")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(f"function is forbidden: {function_name}")

        allowed_table_set = {name.lower() for name in request.allowed_tables}  # 计算 {name.lower() for name in request.allowed_tables} 并保存到变量 allowed_table_set
        allowed_column_set = {name.lower() for name in request.allowed_columns}  # 计算 {name.lower() for name in request.allowed_columns} 并保存到变量 allowed_column_set
        allowed_column_names = {  # 计算 { 并保存到变量 allowed_column_names
            item.split(".", maxsplit=1)[1]  # 调用 split 执行当前步骤：item.split(".", maxsplit=1)[1]
            for item in allowed_column_set  # 按迭代条件执行循环：for item in allowed_column_set
            if "." in item  # 判断分支条件：if "." in item
        }  # 结束上一处多行结构，保持表达式边界清晰
        columns_by_name: dict[str, set[str]] = {}  # 计算 {} 并保存到变量 columns_by_name
        for item in allowed_column_set:  # 按迭代条件执行循环：for item in allowed_column_set:
            if "." not in item:  # 判断分支条件：if "." not in item:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            _, column_name = item.split(".", maxsplit=1)  # 计算 item.split(".", maxsplit=1) 并保存到变量 _, column_name
            columns_by_name.setdefault(column_name, set()).add(item)  # 调用 setdefault 执行当前步骤：columns_by_name.setdefault(column_name, set()).add(item)

        cte_names = {  # 计算 { 并保存到变量 cte_names
            cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)  # 调用 lower 执行当前步骤：cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)
        }  # 结束上一处多行结构，保持表达式边界清晰
        table_aliases: dict[str, str] = {}  # 计算 {} 并保存到变量 table_aliases
        tables: list[str] = []  # 计算 [] 并保存到变量 tables
        for table in expression.find_all(exp.Table):  # 按迭代条件执行循环：for table in expression.find_all(exp.Table):
            if table.catalog or table.db:  # 判断分支条件：if table.catalog or table.db:
                qualified = ".".join(  # 调用 目标函数 构造结果并保存到 qualified
                    part for part in (table.catalog, table.db, table.name) if part  # 调用 目标函数 执行当前步骤：part for part in (table.catalog, table.db, table.name) if part
                )  # 结束 join 调用参数，得到完整表达式结果
            else:  # 进入前面条件均不成立时的兜底分支
                qualified = table.name  # 计算 table.name 并保存到变量 qualified
            lowered = qualified.lower()  # 计算 qualified.lower() 并保存到变量 lowered
            if not table.catalog and not table.db and lowered in cte_names:  # 判断分支条件：if not table.catalog and not table.db and lowered in cte_names:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            if lowered not in allowed_table_set:  # 判断分支条件：if lowered not in allowed_table_set:
                raise SQLPolicyError(f"table is not in the resolved catalog: {qualified}")  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(f"table is not in the resolved catalog: {qualified}")
            tables.append(lowered)  # 调用 append 执行当前步骤：tables.append(lowered)
            table_aliases[lowered] = lowered  # 计算 lowered 并保存到变量 table_aliases[lowered]
            if table.alias:  # 判断分支条件：if table.alias:
                table_aliases[table.alias.lower()] = lowered  # 计算 lowered 并保存到变量 table_aliases[table.alias.lower()]

        columns: list[str] = []  # 计算 [] 并保存到变量 columns
        for column in expression.find_all(exp.Column):  # 按迭代条件执行循环：for column in expression.find_all(exp.Column):
            table_alias = column.table.lower()  # 计算 column.table.lower() 并保存到变量 table_alias
            table_name = table_aliases.get(table_alias, table_alias)  # 计算 table_aliases.get(table_alias, table_alias) 并保存到变量 table_name
            column_name = column.name.lower()  # 计算 column.name.lower() 并保存到变量 column_name
            if column_name == "*":  # 判断分支条件：if column_name == "*":
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            qualified = f"{table_name}.{column_name}" if table_name else column_name  # 计算 f"{table_name}.{column_name}" if table_name else column_name 并保存到变量 qualified
            if table_alias:  # 判断分支条件：if table_alias:
                if qualified not in allowed_column_set:  # 判断分支条件：if qualified not in allowed_column_set:
                    raise SQLPolicyError(  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(
                        f"column is not in the resolved catalog: {qualified}"  # 在函数 inspect 中执行表达式 f"column is not in the resolved catalog: {qualified}"，推进当前业务流程
                    )  # 结束 SQLPolicyError 调用参数，得到完整表达式结果
            elif column_name not in allowed_column_names:  # 在前一条件不成立时继续判断：elif column_name not in allowed_column_names:
                raise SQLPolicyError(  # 抛出明确异常，阻止错误状态被静默接受：SQLPolicyError(
                    f"unqualified column is outside the resolved catalog: {column_name}"  # 在函数 inspect 中执行表达式 f"unqualified column is outside the resolved catalog: {column_name}"，推进当前业务流程
                )  # 结束 SQLPolicyError 调用参数，得到完整表达式结果
            elif len(columns_by_name.get(column_name, set())) == 1:  # 在前一条件不成立时继续判断：elif len(columns_by_name.get(column_name, set())) == 1:
                qualified = next(iter(columns_by_name[column_name]))  # 计算 next(iter(columns_by_name[column_name])) 并保存到变量 qualified
            columns.append(qualified)  # 调用 append 执行当前步骤：columns.append(qualified)

        normalized = expression.sql(dialect="mysql")  # 计算 expression.sql(dialect="mysql") 并保存到变量 normalized
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()  # 计算 hashlib.sha256(normalized.encode("utf-8")).hexdigest() 并保存到变量 digest
        sensitive_hits = sorted(set(columns).intersection(self.sensitive_columns))  # 计算 sorted(set(columns).intersection(self.sensitive_columns)) 并保存到变量 sensitive_hits
        reasons: list[str] = []  # 计算 [] 并保存到变量 reasons
        high_risk = False  # 计算 False 并保存到变量 high_risk
        if request.corrected:  # 判断分支条件：if request.corrected:
            reasons.append("corrected_sql")  # 调用 append 执行当前步骤：reasons.append("corrected_sql")
        if sensitive_hits:  # 判断分支条件：if sensitive_hits:
            reasons.append("sensitive_columns")  # 调用 append 执行当前步骤：reasons.append("sensitive_columns")
            high_risk = True  # 计算 True 并保存到变量 high_risk
        if request.estimated_rows is not None:  # 判断分支条件：if request.estimated_rows is not None:
            if request.estimated_rows > self.high_risk_scan_rows:  # 判断分支条件：if request.estimated_rows > self.high_risk_scan_rows:
                reasons.append("high_scan_estimate")  # 调用 append 执行当前步骤：reasons.append("high_scan_estimate")
                high_risk = True  # 计算 True 并保存到变量 high_risk
            elif request.estimated_rows > self.approval_scan_rows:  # 在前一条件不成立时继续判断：elif request.estimated_rows > self.approval_scan_rows:
                reasons.append("scan_estimate_exceeds_threshold")  # 调用 append 执行当前步骤：reasons.append("scan_estimate_exceeds_threshold")
        return SQLRiskAssessment(  # 返回 SQLRiskAssessment( 给调用方
            allowed=True,  # 为 SQLRiskAssessment 设置关键字参数 allowed，传入当前行给出的值
            normalized_sql=normalized,  # 为 SQLRiskAssessment 设置关键字参数 normalized_sql，传入当前行给出的值
            sql_hash=digest,  # 为 SQLRiskAssessment 设置关键字参数 sql_hash，传入当前行给出的值
            tables=sorted(set(tables)),  # 为 sorted 设置关键字参数 tables，传入当前行给出的值
            columns=sorted(set(columns)),  # 为 sorted 设置关键字参数 columns，传入当前行给出的值
            reasons=reasons,  # 为 SQLRiskAssessment 设置关键字参数 reasons，传入当前行给出的值
            high_risk=high_risk,  # 为 SQLRiskAssessment 设置关键字参数 high_risk，传入当前行给出的值
            approval_required=bool(reasons),  # 为 bool 设置关键字参数 approval_required，传入当前行给出的值
        )  # 结束 SQLRiskAssessment 调用参数，得到完整表达式结果


def catalog_allowlist(  # 定义函数 catalog_allowlist，封装该模块的一项明确职责
    table_infos: list[dict], extra_columns: Iterable[str] = ()  # 为函数 catalog_allowlist 声明参数 table_infos 及其类型或默认值
) -> tuple[list[str], list[str]]:  # 结束 catalog_allowlist 的参数列表并声明返回类型
    tables: list[str] = []  # 计算 [] 并保存到变量 tables
    columns: list[str] = list(extra_columns)  # 计算 list(extra_columns) 并保存到变量 columns
    for table in table_infos:  # 按迭代条件执行循环：for table in table_infos:
        table_name = str(table.get("name", "")).lower()  # 计算 str(table.get("name", "")).lower() 并保存到变量 table_name
        if table_name:  # 判断分支条件：if table_name:
            tables.append(table_name)  # 调用 append 执行当前步骤：tables.append(table_name)
        for column in table.get("columns", []):  # 按迭代条件执行循环：for column in table.get("columns", []):
            column_name = str(column.get("name", "")).lower()  # 计算 str(column.get("name", "")).lower() 并保存到变量 column_name
            if table_name and column_name:  # 判断分支条件：if table_name and column_name:
                columns.append(f"{table_name}.{column_name}")  # 调用 append 执行当前步骤：columns.append(f"{table_name}.{column_name}")
    return tables, columns  # 返回 tables, columns 给调用方
