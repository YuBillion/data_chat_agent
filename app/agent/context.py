"""Backward-compatible alias for the harness runtime context."""

from app.harness.context import HarnessContext  # 从 app.harness.context 导入 HarnessContext，供本模块后续代码使用

DataAgentContext = HarnessContext  # 计算 HarnessContext 并保存到变量 DataAgentContext
