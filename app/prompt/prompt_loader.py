"""Prompt loading constrained to the repository's prompts directory."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import hashlib  # 导入hashlib，建立本模块需要的外部能力引用
from functools import lru_cache  # 从 functools 导入 lru_cache，供本模块后续代码使用
from pathlib import Path  # 从 pathlib 导入 Path，供本模块后续代码使用

from app.core.errors import AppError  # 从 app.core.errors 导入 AppError，供本模块后续代码使用

PROMPT_ROOT = (Path(__file__).parents[2] / "prompts").resolve()  # 计算 (Path(__file__).parents[2] / "prompts").resolve() 并保存到变量 PROMPT_ROOT


class PromptSecurityError(AppError):  # 定义类 PromptSecurityError，组织相关状态与行为
    def __init__(self, message: str) -> None:  # 定义函数 __init__，封装该模块的一项明确职责
        super().__init__(  # 调用 super 执行当前步骤：super().__init__(
            code="INVALID_PROMPT_PATH",  # 为 __init__ 设置关键字参数 code，传入当前行给出的值
            message=message,  # 为 __init__ 设置关键字参数 message，传入当前行给出的值
            status_code=500,  # 为 __init__ 设置关键字参数 status_code，传入当前行给出的值
        )  # 结束 __init__ 调用参数，得到完整表达式结果


@lru_cache(maxsize=128)  # 应用装饰器 lru_cache(maxsize=128)，为紧随其后的定义附加框架行为
def load_prompt(name: str) -> str:  # 定义函数 load_prompt，封装该模块的一项明确职责
    """Read a prompt by logical name without allowing filesystem escape."""

    if not name or "/" in name or "\\" in name or ".." in Path(name).parts:  # 判断分支条件：if not name or "/" in name or "\\" in name or ".." in Path(name).parts:
        raise PromptSecurityError("prompt name must be a relative logical identifier")  # 抛出明确异常，阻止错误状态被静默接受：PromptSecurityError("prompt name must be a relative logical identifier")
    prompt_path = (PROMPT_ROOT / f"{name}.prompt").resolve()  # 计算 (PROMPT_ROOT / f"{name}.prompt").resolve() 并保存到变量 prompt_path
    if not prompt_path.is_relative_to(PROMPT_ROOT):  # 判断分支条件：if not prompt_path.is_relative_to(PROMPT_ROOT):
        raise PromptSecurityError("prompt path escapes the prompts directory")  # 抛出明确异常，阻止错误状态被静默接受：PromptSecurityError("prompt path escapes the prompts directory")
    if not prompt_path.is_file():  # 判断分支条件：if not prompt_path.is_file():
        raise PromptSecurityError(f"prompt does not exist: {name}")  # 抛出明确异常，阻止错误状态被静默接受：PromptSecurityError(f"prompt does not exist: {name}")
    return prompt_path.read_text(encoding="utf-8")  # 返回 prompt_path.read_text(encoding="utf-8") 给调用方


def prompt_digest(name: str) -> str:  # 定义函数 prompt_digest，封装该模块的一项明确职责
    return hashlib.sha256(load_prompt(name).encode("utf-8")).hexdigest()  # 返回 hashlib.sha256(load_prompt(name).encode("utf-8")).hexdigest() 给调用方
