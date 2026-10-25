"""Structured application logging with request, run, and trace correlation."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import json  # 导入json，建立本模块需要的外部能力引用
import sys  # 导入sys，建立本模块需要的外部能力引用
from pathlib import Path  # 从 pathlib 导入 Path，供本模块后续代码使用
from typing import Any  # 从 typing 导入 Any，供本模块后续代码使用

from loguru import logger  # 从 loguru 导入 logger，供本模块后续代码使用
from opentelemetry import trace  # 从 opentelemetry 导入 trace，供本模块后续代码使用

from app.conf.settings import get_settings  # 从 app.conf.settings 导入 get_settings，供本模块后续代码使用
from app.core.context import request_id_ctx_var, run_id_ctx_var  # 从 app.core.context 导入 request_id_ctx_var, run_id_ctx_var，供本模块后续代码使用

settings = get_settings()  # 计算 get_settings() 并保存到变量 settings


def inject_context(record: dict[str, Any]) -> None:  # 定义函数 inject_context，封装该模块的一项明确职责
    span_context = trace.get_current_span().get_span_context()  # 计算 trace.get_current_span().get_span_context() 并保存到变量 span_context
    record["extra"].setdefault("request_id", request_id_ctx_var.get())  # 调用 目标函数 执行当前步骤：record["extra"].setdefault("request_id", request_id_ctx_var.get())
    record["extra"].setdefault("run_id", run_id_ctx_var.get())  # 调用 目标函数 执行当前步骤：record["extra"].setdefault("run_id", run_id_ctx_var.get())
    record["extra"].setdefault(  # 调用 目标函数 执行当前步骤：record["extra"].setdefault(
        "trace_id",  # 继续向上一处调用或声明传入 "trace_id"
        format(span_context.trace_id, "032x") if span_context.is_valid else "-",  # 继续向上一处调用或声明传入 format(span_context.trace_id, "032x") if span_context.is_valid else "-"
    )  # 结束函数 inject_context 的参数及返回类型声明并开始函数体


def json_sink(message: Any) -> None:  # 定义函数 json_sink，封装该模块的一项明确职责
    record = message.record  # 计算 message.record 并保存到变量 record
    payload = {  # 计算 { 并保存到变量 payload
        "timestamp": record["time"].isoformat(),  # 为多行字典定义键 "timestamp" 及其对应值
        "level": record["level"].name,  # 为多行字典定义键 "level" 及其对应值
        "message": record["message"],  # 为多行字典定义键 "message" 及其对应值
        "logger": record["name"],  # 为多行字典定义键 "logger" 及其对应值
        "function": record["function"],  # 为多行字典定义键 "function" 及其对应值
        "line": record["line"],  # 为多行字典定义键 "line" 及其对应值
        "request_id": record["extra"].get("request_id", "-"),  # 为多行字典定义键 "request_id" 及其对应值
        "run_id": record["extra"].get("run_id", "-"),  # 为多行字典定义键 "run_id" 及其对应值
        "trace_id": record["extra"].get("trace_id", "-"),  # 为多行字典定义键 "trace_id" 及其对应值
    }  # 结束上一处多行结构，保持表达式边界清晰
    if record["exception"]:  # 判断分支条件：if record["exception"]:
        payload["exception"] = str(record["exception"])  # 计算 str(record["exception"]) 并保存到变量 payload["exception"]
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")  # 调用 write 执行当前步骤：sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) +…
    sys.stdout.flush()  # 调用 flush 执行当前步骤：sys.stdout.flush()


def text_sink(message: Any) -> None:  # 定义函数 text_sink，封装该模块的一项明确职责
    sys.stdout.write(message)  # 调用 write 执行当前步骤：sys.stdout.write(message)
    sys.stdout.flush()  # 调用 flush 执行当前步骤：sys.stdout.flush()


logger.remove()  # 调用 remove 执行当前步骤：logger.remove()
logger = logger.patch(inject_context)  # 计算 logger.patch(inject_context) 并保存到变量 logger
if settings.log_json:  # 判断分支条件：if settings.log_json:
    logger.add(  # 调用 add 执行当前步骤：logger.add(
        json_sink,  # 继续向上一处调用或声明传入 json_sink
        level=settings.log_level.upper(),  # 为 settings.log_level.upper 设置关键字参数 level，传入当前行给出的值
        enqueue=False,  # 为 logger.add 设置关键字参数 enqueue，传入当前行给出的值
        backtrace=False,  # 为 logger.add 设置关键字参数 backtrace，传入当前行给出的值
        diagnose=False,  # 为 logger.add 设置关键字参数 diagnose，传入当前行给出的值
    )  # 结束 logger.add 调用参数，得到完整表达式结果
else:  # 进入前面条件均不成立时的兜底分支
    logger.add(  # 调用 add 执行当前步骤：logger.add(
        text_sink,  # 继续向上一处调用或声明传入 text_sink
        level=settings.log_level.upper(),  # 为 settings.log_level.upper 设置关键字参数 level，传入当前行给出的值
        format=(  # 为 logger.add 设置关键字参数 format，传入当前行给出的值
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "  # 执行源码表达式 "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "，完成本行对应的语义动作
            "request_id={extra[request_id]} run_id={extra[run_id]} "  # 执行源码表达式 "request_id={extra[request_id]} run_id={extra[run_id]} "，完成本行对应的语义动作
            "trace_id={extra[trace_id]} | {name}:{function}:{line} - {message}\n"  # 执行源码表达式 "trace_id={extra[trace_id]} | {name}:{function}:{line} - {message}\n"，完成本行对应的语义动作
        ),  # 结束上一处多行结构，保持表达式边界清晰
        backtrace=False,  # 为 logger.add 设置关键字参数 backtrace，传入当前行给出的值
        diagnose=False,  # 为 logger.add 设置关键字参数 diagnose，传入当前行给出的值
    )  # 结束 logger.add 调用参数，得到完整表达式结果

if settings.log_to_file and not settings.is_production:  # 判断分支条件：if settings.log_to_file and not settings.is_production:
    path = Path(settings.log_file_path)  # 计算 Path(settings.log_file_path) 并保存到变量 path
    path.mkdir(parents=True, exist_ok=True)  # 调用 mkdir 执行当前步骤：path.mkdir(parents=True, exist_ok=True)
    logger.add(  # 调用 add 执行当前步骤：logger.add(
        path / "app.log",  # 继续向上一处调用或声明传入 path / "app.log"
        level=settings.log_level.upper(),  # 为 settings.log_level.upper 设置关键字参数 level，传入当前行给出的值
        rotation="10 MB",  # 为 logger.add 设置关键字参数 rotation，传入当前行给出的值
        retention="7 days",  # 为 logger.add 设置关键字参数 retention，传入当前行给出的值
        encoding="utf-8",  # 为 logger.add 设置关键字参数 encoding，传入当前行给出的值
        backtrace=False,  # 为 logger.add 设置关键字参数 backtrace，传入当前行给出的值
        diagnose=False,  # 为 logger.add 设置关键字参数 diagnose，传入当前行给出的值
    )  # 结束 logger.add 调用参数，得到完整表达式结果
