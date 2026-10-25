"""
额外上下文补全节点

负责在 SQL 生成前补齐不来自召回结果、但模型必须知道的运行环境信息
当前包括日期信息和数据库方言/版本，后续可继续扩展权限、租户、时区等上下文
"""

from datetime import datetime  # 从 datetime 导入 datetime，供本模块后续代码使用
from zoneinfo import ZoneInfo  # 从 zoneinfo 导入 ZoneInfo，供本模块后续代码使用

from langgraph.runtime import Runtime  # 从 langgraph.runtime 导入 Runtime，供本模块后续代码使用

from app.agent.context import DataAgentContext  # 从 app.agent.context 导入 DataAgentContext，供本模块后续代码使用
from app.agent.state import DataAgentState, DateInfoState, DBInfoState  # 从 app.agent.state 导入 DataAgentState, DateInfoState, DBInfoState，供本模块后续代码使用
from app.core.log import logger  # 从 app.core.log 导入 logger，供本模块后续代码使用


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):  # 定义异步函数 add_extra_context，封装可被事件循环调度的协程逻辑
    """补齐 SQL 生成所需的日期和数据库环境信息"""

    writer = runtime.stream_writer  # 计算 runtime.stream_writer 并保存到变量 writer
    step = "添加额外上下文"  # 计算 "添加额外上下文" 并保存到变量 step
    writer({"type": "progress", "step": step, "status": "running"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "running"})
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        dw_mysql_repository = runtime.context["dw_mysql_repository"]  # 计算 runtime.context["dw_mysql_repository"] 并保存到变量 dw_mysql_repository

        # 当前日期信息会帮助模型处理“今天 本月 本季度 最近 N 天”等相对时间表达
        timezone_name = runtime.context.get("business_timezone", "Asia/Shanghai")  # 计算 runtime.context.get("business_timezone", "Asia/Shanghai") 并保存到变量 timezone_name
        today = datetime.now(ZoneInfo(timezone_name)).date()  # 计算 datetime.now(ZoneInfo(timezone_name)).date() 并保存到变量 today
        date_str = today.strftime("%Y-%m-%d")  # 计算 today.strftime("%Y-%m-%d") 并保存到变量 date_str
        weekday = today.strftime("%A")  # 计算 today.strftime("%A") 并保存到变量 weekday
        quarter = f"Q{(today.month - 1) // 3 + 1}"  # 计算 f"Q{(today.month - 1) // 3 + 1}" 并保存到变量 quarter
        date_info = DateInfoState(date=date_str, weekday=weekday, quarter=quarter)  # 计算 DateInfoState(date=date_str, weekday=weekday, quarter=quarter) 并保存到变量 date_info

        # 数据库方言和版本会影响函数名 日期运算 limit 语法等 SQL 细节
        db = await dw_mysql_repository.get_db_info()  # 等待 get_db_info 完成，并将其结果保存到 db
        db_info = DBInfoState(**db)  # 计算 DBInfoState(**db) 并保存到变量 db_info
        logger.info(f"数据库信息：{db_info}")  # 调用 info 执行当前步骤：logger.info(f"数据库信息：{db_info}")
        logger.info(f"日期信息：{date_info}")  # 调用 info 执行当前步骤：logger.info(f"日期信息：{date_info}")

        writer({"type": "progress", "step": step, "status": "success"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "success"})
        return {"date_info": date_info, "db_info": db_info}  # 返回 {"date_info": date_info, "db_info": db_info} 给调用方

    except Exception as e:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except Exception as e:
        logger.error(f"{step} failed: {e}")  # 调用 error 执行当前步骤：logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})  # 调用 writer 执行当前步骤：writer({"type": "progress", "step": step, "status": "error"})
        raise  # 重新抛出当前异常，保留原始失败上下文
