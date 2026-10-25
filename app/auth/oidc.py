"""Async OIDC JWT validation with bounded JWKS caching."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

import asyncio  # 导入asyncio，建立本模块需要的外部能力引用
from time import monotonic  # 从 time 导入 monotonic，供本模块后续代码使用
from typing import Annotated, Any  # 从 typing 导入 Annotated, Any，供本模块后续代码使用

import httpx  # 导入httpx，建立本模块需要的外部能力引用
import jwt  # 导入jwt，建立本模块需要的外部能力引用
from fastapi import Depends, HTTPException, Request, status  # 从 fastapi 导入 Depends, HTTPException, Request, status，供本模块后续代码使用
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # 从 fastapi.security 导入 HTTPAuthorizationCredentials, HTTPBearer，供本模块后续代码使用

from app.conf.settings import Settings  # 从 app.conf.settings 导入 Settings，供本模块后续代码使用
from app.core.errors import ForbiddenError  # 从 app.core.errors 导入 ForbiddenError，供本模块后续代码使用
from app.harness.types import Identity  # 从 app.harness.types 导入 Identity，供本模块后续代码使用

ALLOWED_ALGORITHMS = frozenset(  # 调用 frozenset 构造结果并保存到 ALLOWED_ALGORITHMS
    {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}  # 执行源码表达式 {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}，完成本行对应的语义动作
)  # 结束 frozenset 调用参数，得到完整表达式结果


class JWTValidator:  # 定义类 JWTValidator，组织相关状态与行为
    def __init__(  # 定义函数 __init__，封装该模块的一项明确职责
        self,  # 为函数 __init__ 声明参数 self 及其类型或默认值
        settings: Settings,  # 为函数 __init__ 声明参数 settings 及其类型或默认值
        *,  # 为函数 __init__ 声明参数 * 及其类型或默认值
        http_client: httpx.AsyncClient | None = None,  # 为函数 __init__ 声明参数 http_client 及其类型或默认值
    ) -> None:  # 结束 __init__ 的参数列表并声明返回类型
        self.settings = settings  # 将依赖或状态 settings 保存到实例属性 self.settings
        self.http_client = http_client  # 将依赖或状态 http_client 保存到实例属性 self.http_client
        self._owns_http_client = http_client is None  # 将依赖或状态 http_client is None 保存到实例属性 self._owns_http_client
        self._jwks: dict[str, list[dict[str, Any]]] = {}  # 将依赖或状态 {} 保存到实例属性 self._jwks: dict[str, list[dict[str, Any]]]
        self._fetched_at = 0.0  # 将依赖或状态 0.0 保存到实例属性 self._fetched_at
        self._lock = asyncio.Lock()  # 将依赖或状态 asyncio.Lock() 保存到实例属性 self._lock

    async def close(self) -> None:  # 定义异步函数 close，封装可被事件循环调度的协程逻辑
        if self._owns_http_client and self.http_client is not None:  # 判断分支条件：if self._owns_http_client and self.http_client is not None:
            await self.http_client.aclose()  # 等待异步操作完成并取得结果：self.http_client.aclose()

    async def validate(self, token: str) -> Identity:  # 定义异步函数 validate，封装可被事件循环调度的协程逻辑
        if not self.settings.oidc_issuer or not self.settings.oidc_audience:  # 判断分支条件：if not self.settings.oidc_issuer or not self.settings.oidc_audience:
            raise HTTPException(  # 抛出明确异常，阻止错误状态被静默接受：HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # 为 HTTPException 设置关键字参数 status_code，传入当前行给出的值
                detail="OIDC is not configured",  # 为 HTTPException 设置关键字参数 detail，传入当前行给出的值
            )  # 结束函数 validate 的参数及返回类型声明并开始函数体
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            header = jwt.get_unverified_header(token)  # 计算 jwt.get_unverified_header(token) 并保存到变量 header
        except jwt.PyJWTError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except jwt.PyJWTError as exc:
            raise _unauthorized("invalid bearer token") from exc  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("invalid bearer token") from exc
        algorithm = str(header.get("alg", ""))  # 计算 str(header.get("alg", "")) 并保存到变量 algorithm
        if algorithm not in ALLOWED_ALGORITHMS:  # 判断分支条件：if algorithm not in ALLOWED_ALGORITHMS:
            raise _unauthorized("unsupported JWT algorithm")  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("unsupported JWT algorithm")
        key_id = str(header.get("kid", ""))  # 计算 str(header.get("kid", "")) 并保存到变量 key_id
        key = await self._find_key(key_id=key_id, algorithm=algorithm)  # 等待 _find_key 完成，并将其结果保存到 key
        try:  # 开始受保护代码块，捕获其可能抛出的预期异常
            claims = jwt.decode(  # 调用 decode 构造结果并保存到 claims
                token,  # 继续向上一处调用或声明传入 token
                key=key,  # 为 jwt.decode 设置关键字参数 key，传入当前行给出的值
                algorithms=[algorithm],  # 为 jwt.decode 设置关键字参数 algorithms，传入当前行给出的值
                audience=self.settings.oidc_audience,  # 为 jwt.decode 设置关键字参数 audience，传入当前行给出的值
                issuer=self.settings.oidc_issuer,  # 为 jwt.decode 设置关键字参数 issuer，传入当前行给出的值
                options={  # 为 jwt.decode 设置关键字参数 options，传入当前行给出的值
                    "require": ["exp", "iat", "sub"],  # 为多行字典定义键 "require" 及其对应值
                    "verify_signature": True,  # 为多行字典定义键 "verify_signature" 及其对应值
                    "verify_exp": True,  # 为多行字典定义键 "verify_exp" 及其对应值
                    "verify_iat": True,  # 为多行字典定义键 "verify_iat" 及其对应值
                    "verify_aud": True,  # 为多行字典定义键 "verify_aud" 及其对应值
                    "verify_iss": True,  # 为多行字典定义键 "verify_iss" 及其对应值
                },  # 结束上一处多行结构，保持表达式边界清晰
            )  # 结束函数 validate 的参数及返回类型声明并开始函数体
        except jwt.PyJWTError as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except jwt.PyJWTError as exc:
            raise _unauthorized("invalid bearer token claims") from exc  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("invalid bearer token claims") from exc
        return identity_from_claims(claims, self.settings)  # 返回 identity_from_claims(claims, self.settings) 给调用方

    async def _find_key(self, *, key_id: str, algorithm: str) -> Any:  # 定义异步函数 _find_key，封装可被事件循环调度的协程逻辑
        keys = await self._get_jwks()  # 等待 _get_jwks 完成，并将其结果保存到 keys
        for jwk in keys:  # 按迭代条件执行循环：for jwk in keys:
            if key_id and jwk.get("kid") != key_id:  # 判断分支条件：if key_id and jwk.get("kid") != key_id:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                return jwt.PyJWK(jwk, algorithm=algorithm).key  # 返回 jwt.PyJWK(jwk, algorithm=algorithm).key 给调用方
            except jwt.PyJWTError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except jwt.PyJWTError:
                continue  # 跳过本轮剩余逻辑并进入下一轮迭代
        if key_id:  # 判断分支条件：if key_id:
            keys = await self._get_jwks(force=True)  # 等待 _get_jwks 完成，并将其结果保存到 keys
            for jwk in keys:  # 按迭代条件执行循环：for jwk in keys:
                if jwk.get("kid") == key_id:  # 判断分支条件：if jwk.get("kid") == key_id:
                    try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                        return jwt.PyJWK(jwk, algorithm=algorithm).key  # 返回 jwt.PyJWK(jwk, algorithm=algorithm).key 给调用方
                    except jwt.PyJWTError:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except jwt.PyJWTError:
                        continue  # 跳过本轮剩余逻辑并进入下一轮迭代
        raise _unauthorized("JWT signing key is unknown")  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("JWT signing key is unknown")

    async def _get_jwks(self, *, force: bool = False) -> list[dict[str, Any]]:  # 定义异步函数 _get_jwks，封装可被事件循环调度的协程逻辑
        now = monotonic()  # 计算 monotonic() 并保存到变量 now
        if (  # 判断分支条件：if (
            not force  # 在函数 _get_jwks 中执行表达式 not force，推进当前业务流程
            and self._jwks  # 在函数 _get_jwks 中执行表达式 and self._jwks，推进当前业务流程
            and now - self._fetched_at < 300  # 在函数 _get_jwks 中执行表达式 and now - self._fetched_at < 300，推进当前业务流程
        ):  # 结束 _get_jwks 的参数列表并声明返回类型
            return [key for values in self._jwks.values() for key in values]  # 返回 [key for values in self._jwks.values() for key in values] 给调用方
        async with self._lock:  # 进入受管理的上下文 async with self._lock:，确保资源正确获取与释放
            now = monotonic()  # 计算 monotonic() 并保存到变量 now
            if (  # 判断分支条件：if (
                not force  # 在函数 _get_jwks 中执行表达式 not force，推进当前业务流程
                and self._jwks  # 在函数 _get_jwks 中执行表达式 and self._jwks，推进当前业务流程
                and now - self._fetched_at < 300  # 在函数 _get_jwks 中执行表达式 and now - self._fetched_at < 300，推进当前业务流程
            ):  # 结束 _get_jwks 的参数列表并声明返回类型
                return [key for values in self._jwks.values() for key in values]  # 返回 [key for values in self._jwks.values() for key in values] 给调用方
            if not self.settings.oidc_jwks_url:  # 判断分支条件：if not self.settings.oidc_jwks_url:
                raise HTTPException(  # 抛出明确异常，阻止错误状态被静默接受：HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # 为 HTTPException 设置关键字参数 status_code，传入当前行给出的值
                    detail="OIDC JWKS endpoint is not configured",  # 为 HTTPException 设置关键字参数 detail，传入当前行给出的值
                )  # 结束函数 _get_jwks 的参数及返回类型声明并开始函数体
            if self.http_client is None:  # 判断分支条件：if self.http_client is None:
                self.http_client = httpx.AsyncClient(timeout=10.0)  # 将依赖或状态 httpx.AsyncClient(timeout=10.0) 保存到实例属性 self.http_client
            try:  # 开始受保护代码块，捕获其可能抛出的预期异常
                response = await self.http_client.get(self.settings.oidc_jwks_url)  # 等待 get 完成，并将其结果保存到 response
                response.raise_for_status()  # 调用 raise_for_status 执行当前步骤：response.raise_for_status()
                payload = response.json()  # 计算 response.json() 并保存到变量 payload
            except (httpx.HTTPError, ValueError) as exc:  # 捕获匹配的异常并执行明确的恢复或转换逻辑：except (httpx.HTTPError, ValueError) as exc:
                raise HTTPException(  # 抛出明确异常，阻止错误状态被静默接受：HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # 为 HTTPException 设置关键字参数 status_code，传入当前行给出的值
                    detail="OIDC JWKS endpoint is unavailable",  # 为 HTTPException 设置关键字参数 detail，传入当前行给出的值
                ) from exc  # 在函数 _get_jwks 中执行表达式 ) from exc，推进当前业务流程
            keys = payload.get("keys")  # 计算 payload.get("keys") 并保存到变量 keys
            if not isinstance(keys, list):  # 判断分支条件：if not isinstance(keys, list):
                raise HTTPException(  # 抛出明确异常，阻止错误状态被静默接受：HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # 为 HTTPException 设置关键字参数 status_code，传入当前行给出的值
                    detail="OIDC JWKS response is invalid",  # 为 HTTPException 设置关键字参数 detail，传入当前行给出的值
                )  # 结束函数 _get_jwks 的参数及返回类型声明并开始函数体
            self._jwks = {  # 将依赖或状态 { 保存到实例属性 self._jwks
                "keys": [item for item in keys if isinstance(item, dict)]  # 为多行字典定义键 "keys" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
            self._fetched_at = monotonic()  # 将依赖或状态 monotonic() 保存到实例属性 self._fetched_at
            return self._jwks["keys"]  # 返回 self._jwks["keys"] 给调用方


def identity_from_claims(claims: dict[str, Any], settings: Settings) -> Identity:  # 定义函数 identity_from_claims，封装该模块的一项明确职责
    user_id = claims.get(settings.oidc_user_claim)  # 计算 claims.get(settings.oidc_user_claim) 并保存到变量 user_id
    tenant_id = claims.get(settings.oidc_tenant_claim)  # 计算 claims.get(settings.oidc_tenant_claim) 并保存到变量 tenant_id
    raw_roles = claims.get(settings.oidc_roles_claim, [])  # 计算 claims.get(settings.oidc_roles_claim, []) 并保存到变量 raw_roles
    if isinstance(raw_roles, str):  # 判断分支条件：if isinstance(raw_roles, str):
        roles = {item.strip() for item in raw_roles.split(",") if item.strip()}  # 计算 {item.strip() for item in raw_roles.split(",") if item.strip()} 并保存到变量 roles
    elif isinstance(raw_roles, list):  # 在前一条件不成立时继续判断：elif isinstance(raw_roles, list):
        roles = {str(item) for item in raw_roles}  # 计算 {str(item) for item in raw_roles} 并保存到变量 roles
    else:  # 进入前面条件均不成立时的兜底分支
        roles = set()  # 计算 set() 并保存到变量 roles
    if not user_id or not tenant_id:  # 判断分支条件：if not user_id or not tenant_id:
        raise _unauthorized("JWT is missing user or tenant claims")  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("JWT is missing user or tenant claims")
    return Identity(  # 返回 Identity( 给调用方
        user_id=str(user_id),  # 为 str 设置关键字参数 user_id，传入当前行给出的值
        tenant_id=str(tenant_id),  # 为 str 设置关键字参数 tenant_id，传入当前行给出的值
        roles=frozenset(roles),  # 为 frozenset 设置关键字参数 roles，传入当前行给出的值
        raw_claims=claims,  # 为 Identity 设置关键字参数 raw_claims，传入当前行给出的值
    )  # 结束函数 identity_from_claims 的参数及返回类型声明并开始函数体


bearer_scheme = HTTPBearer(auto_error=False)  # 计算 HTTPBearer(auto_error=False) 并保存到变量 bearer_scheme


async def get_identity(  # 定义异步函数 get_identity，封装可被事件循环调度的协程逻辑
    request: Request,  # 为函数 get_identity 声明参数 request 及其类型或默认值
    credentials: Annotated[  # 为函数 get_identity 声明参数 credentials 及其类型或默认值
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)  # 为函数 get_identity 声明参数 HTTPAuthorizationCredentials | None, Depends(bearer_scheme) 及其类型或默认值
    ] = None,  # 为函数 get_identity 声明参数 ] 及其类型或默认值
) -> Identity:  # 结束 get_identity 的参数列表并声明返回类型
    settings: Settings = request.app.state.container.settings  # 计算 request.app.state.container.settings 并保存到变量 settings
    if settings.dev_auth_enabled and not settings.is_production:  # 判断分支条件：if settings.dev_auth_enabled and not settings.is_production:
        return Identity(  # 返回 Identity( 给调用方
            user_id=settings.dev_user_id,  # 为 Identity 设置关键字参数 user_id，传入当前行给出的值
            tenant_id=settings.dev_tenant_id,  # 为 Identity 设置关键字参数 tenant_id，传入当前行给出的值
            roles=frozenset(settings.dev_role_values),  # 为 frozenset 设置关键字参数 roles，传入当前行给出的值
        )  # 结束函数 get_identity 的参数及返回类型声明并开始函数体
    if credentials is None or credentials.scheme.lower() != "bearer":  # 判断分支条件：if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("bearer token is required")  # 抛出明确异常，阻止错误状态被静默接受：_unauthorized("bearer token is required")
    validator: JWTValidator = request.app.state.container.jwt_validator  # 计算 request.app.state.container.jwt_validator 并保存到变量 validator
    return await validator.validate(credentials.credentials)  # 返回 await validator.validate(credentials.credentials) 给调用方


async def require_user(  # 定义异步函数 require_user，封装可被事件循环调度的协程逻辑
    identity: Annotated[Identity, Depends(get_identity)],  # 为函数 require_user 声明参数 identity 及其类型或默认值
) -> Identity:  # 结束 require_user 的参数列表并声明返回类型
    if (  # 判断分支条件：if (
        not identity.has_role("agent:user")  # 调用 目标函数 执行当前步骤：not identity.has_role("agent:user")
        and not identity.has_role("agent:approver")  # 调用 目标函数 执行当前步骤：and not identity.has_role("agent:approver")
        and not identity.has_role("agent:admin")  # 调用 目标函数 执行当前步骤：and not identity.has_role("agent:admin")
    ):  # 结束 require_user 的参数列表并声明返回类型
        raise ForbiddenError("agent:user role is required")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent:user role is required")
    return identity  # 返回 identity 给调用方


async def require_approver(  # 定义异步函数 require_approver，封装可被事件循环调度的协程逻辑
    identity: Annotated[Identity, Depends(get_identity)],  # 为函数 require_approver 声明参数 identity 及其类型或默认值
) -> Identity:  # 结束 require_approver 的参数列表并声明返回类型
    if not identity.has_role("agent:approver"):  # 判断分支条件：if not identity.has_role("agent:approver"):
        raise ForbiddenError("agent:approver role is required")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent:approver role is required")
    return identity  # 返回 identity 给调用方


async def require_admin(  # 定义异步函数 require_admin，封装可被事件循环调度的协程逻辑
    identity: Annotated[Identity, Depends(get_identity)],  # 为函数 require_admin 声明参数 identity 及其类型或默认值
) -> Identity:  # 结束 require_admin 的参数列表并声明返回类型
    if not identity.has_role("agent:admin"):  # 判断分支条件：if not identity.has_role("agent:admin"):
        raise ForbiddenError("agent:admin role is required")  # 抛出明确异常，阻止错误状态被静默接受：ForbiddenError("agent:admin role is required")
    return identity  # 返回 identity 给调用方


def _unauthorized(detail: str) -> HTTPException:  # 定义函数 _unauthorized，封装该模块的一项明确职责
    return HTTPException(  # 返回 HTTPException( 给调用方
        status_code=status.HTTP_401_UNAUTHORIZED,  # 为 HTTPException 设置关键字参数 status_code，传入当前行给出的值
        detail=detail,  # 为 HTTPException 设置关键字参数 detail，传入当前行给出的值
        headers={"WWW-Authenticate": "Bearer"},  # 为 HTTPException 设置关键字参数 headers，传入当前行给出的值
    )  # 结束函数 _unauthorized 的参数及返回类型声明并开始函数体
