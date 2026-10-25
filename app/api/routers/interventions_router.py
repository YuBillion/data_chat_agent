"""Human-in-the-loop response API."""

from typing import Annotated  # 从 typing 导入 Annotated，供本模块后续代码使用
from uuid import UUID  # 从 uuid 导入 UUID，供本模块后续代码使用

from fastapi import APIRouter, Depends  # 从 fastapi 导入 APIRouter, Depends，供本模块后续代码使用

from app.api.dependencies_v1 import get_run_service  # 从 app.api.dependencies_v1 导入 get_run_service，供本模块后续代码使用
from app.api.schemas.v1 import (  # 开始导入下方列出的多个符号，集中声明本模块依赖
    InterventionDecisionRequest,  # 从当前 import 模块导入符号 InterventionDecisionRequest
    InterventionResponse,  # 从当前 import 模块导入符号 InterventionResponse
)  # 结束多符号导入列表
from app.auth.oidc import require_user  # 从 app.auth.oidc 导入 require_user，供本模块后续代码使用
from app.core.errors import ConflictError  # 从 app.core.errors 导入 ConflictError，供本模块后续代码使用
from app.harness.service import RunService  # 从 app.harness.service 导入 RunService，供本模块后续代码使用
from app.harness.types import DecisionAction, Identity  # 从 app.harness.types 导入 DecisionAction, Identity，供本模块后续代码使用

interventions_router = APIRouter(  # 调用 APIRouter 构造结果并保存到 interventions_router
    prefix="/api/v1/interventions", tags=["interventions"]  # 为 APIRouter 设置关键字参数 prefix，传入当前行给出的值
)  # 结束 APIRouter 调用参数，得到完整表达式结果


@interventions_router.post(  # 应用装饰器 interventions_router.post(，为紧随其后的定义附加框架行为
    "/{intervention_id}/respond", response_model=InterventionResponse  # 执行源码表达式 "/{intervention_id}/respond", response_model=InterventionResponse，完成本行对应的语义动作
)  # 结束 interventions_router.post 调用参数，得到完整表达式结果
async def respond_to_intervention(  # 定义异步函数 respond_to_intervention，封装可被事件循环调度的协程逻辑
    intervention_id: UUID,  # 为函数 respond_to_intervention 声明参数 intervention_id 及其类型或默认值
    body: InterventionDecisionRequest,  # 为函数 respond_to_intervention 声明参数 body 及其类型或默认值
    identity: Annotated[Identity, Depends(require_user)],  # 为函数 respond_to_intervention 声明参数 identity 及其类型或默认值
    service: Annotated[RunService, Depends(get_run_service)],  # 为函数 respond_to_intervention 声明参数 service 及其类型或默认值
) -> InterventionResponse:  # 结束 respond_to_intervention 的参数列表并声明返回类型
    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
        action = DecisionAction(body.action)  # 计算 DecisionAction(body.action) 并保存到变量 action
    except ValueError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except ValueError as exc:
        raise ConflictError(  # 抛出明确异常，阻止错误状态被静默接受：ConflictError(
            "INVALID_ACTION", "unknown intervention action"  # 在函数 respond_to_intervention 中执行表达式 "INVALID_ACTION", "unknown intervention action"，推进当前业务流程
        ) from exc  # 在函数 respond_to_intervention 中执行表达式 ) from exc，推进当前业务流程
    record = await service.respond_to_intervention(  # 等待 respond_to_intervention 完成，并将其结果保存到 record
        identity,  # 继续向上一处调用或声明传入 identity
        intervention_id,  # 继续向上一处调用或声明传入 intervention_id
        expected_version=body.expected_version,  # 为 service.respond_to_intervention 设置关键字参数 expected_version，传入当前行给出的值
        action=action,  # 为 service.respond_to_intervention 设置关键字参数 action，传入当前行给出的值
        decision=body.payload(),  # 为 body.payload 设置关键字参数 decision，传入当前行给出的值
    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
    return InterventionResponse(  # 返回 InterventionResponse( 给调用方
        id=record.id,  # 为 InterventionResponse 设置关键字参数 id，传入当前行给出的值
        run_id=record.run_id,  # 为 InterventionResponse 设置关键字参数 run_id，传入当前行给出的值
        kind=record.kind,  # 为 InterventionResponse 设置关键字参数 kind，传入当前行给出的值
        status=record.status,  # 为 InterventionResponse 设置关键字参数 status，传入当前行给出的值
        payload=record.payload,  # 为 InterventionResponse 设置关键字参数 payload，传入当前行给出的值
        version=record.version,  # 为 InterventionResponse 设置关键字参数 version，传入当前行给出的值
        requested_at=record.requested_at,  # 为 InterventionResponse 设置关键字参数 requested_at，传入当前行给出的值
        expires_at=record.expires_at,  # 为 InterventionResponse 设置关键字参数 expires_at，传入当前行给出的值
        decision=record.decision,  # 为 InterventionResponse 设置关键字参数 decision，传入当前行给出的值
        actor_id=record.actor_id,  # 为 InterventionResponse 设置关键字参数 actor_id，传入当前行给出的值
        responded_at=record.responded_at,  # 为 InterventionResponse 设置关键字参数 responded_at，传入当前行给出的值
    )  # 结束函数 respond_to_intervention 的参数及返回类型声明并开始函数体
