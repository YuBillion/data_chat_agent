"""Application errors with stable, client-safe error semantics."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from dataclasses import dataclass, field  # 从 dataclasses 导入 dataclass, field，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用


@dataclass(slots=True)  # 应用装饰器 dataclass(slots=True)，为紧随其后的定义附加框架行为
class AppError(Exception):  # 定义类 AppError，组织相关状态与行为
    """An expected failure that can be mapped to RFC 9457 Problem Details."""

    code: str  # 声明或继续传入参数 code: str
    message: str  # 声明或继续传入参数 message: str
    status_code: int = 400  # 计算 400 并保存到变量 status_code
    details: dict[str, Any] = field(default_factory=dict)  # 计算 field(default_factory=dict) 并保存到变量 details
    retryable: bool = False  # 计算 False 并保存到变量 retryable

    def __str__(self) -> str:  # 定义函数 __str__，封装该模块的一项明确职责
        return self.message  # 返回 self.message 给调用方


class NotFoundError(AppError):  # 定义类 NotFoundError，组织相关状态与行为
    def __init__(self, resource: str, identifier: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="NOT_FOUND",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=f"{resource} not found",  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=404,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
            details={"resource": resource, "id": identifier},  # 为 __init__ 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体


class ForbiddenError(AppError):  # 定义类 ForbiddenError，组织相关状态与行为
    def __init__(self, message: str = "operation is not permitted") -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(code="FORBIDDEN", message=message, status_code=403)  # 调用 super 执行当前步骤：super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppError):  # 定义类 ConflictError，组织相关状态与行为
    def __init__(self, code: str, message: str, **details: Any) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code=code,  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=message,  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=409,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
            details=details,  # 为 __init__ 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体


class BudgetExceededError(AppError):  # 定义类 BudgetExceededError，组织相关状态与行为
    def __init__(self, limit: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="BUDGET_EXCEEDED",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=f"run budget exceeded: {limit}",  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=409,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
            details={"limit": limit},  # 为 __init__ 设置关键字参数 details，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体


class DependencyUnavailableError(AppError):  # 定义类 DependencyUnavailableError，组织相关状态与行为
    def __init__(self, dependency: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="DEPENDENCY_UNAVAILABLE",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=f"required dependency is unavailable: {dependency}",  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=503,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
            details={"dependency": dependency},  # 为 __init__ 设置关键字参数 details，传入当前行给出的值
            retryable=True,  # 为 __init__ 设置关键字参数 retryable，传入当前行给出的值
        )  # 结束函数 __init__ 的参数及返回类型声明并开始函数体
