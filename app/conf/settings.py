"""Typed runtime configuration shared by the API and worker processes."""

from __future__ import annotations  # 启用未来语法特性，统一当前模块的注解与类型解析行为

from functools import lru_cache  # 从 functools 导入 lru_cache，供本模块后续代码使用
from typing import Literal  # 从 typing 导入 Literal，供本模块后续代码使用
from urllib.parse import urlparse  # 从 urllib.parse 导入 urlparse，供本模块后续代码使用

from pydantic import AliasChoices, Field, SecretStr, model_validator  # 从 pydantic 导入 AliasChoices, Field, SecretStr, model_validator，供本模块后续代码使用
from pydantic_settings import BaseSettings, SettingsConfigDict  # 从 pydantic_settings 导入 BaseSettings, SettingsConfigDict，供本模块后续代码使用


class Settings(BaseSettings):  # 定义类 Settings，组织相关状态与行为
    """Environment-backed production configuration.

    Business catalog configuration remains in ``conf/app_config.yaml`` and
    ``conf/meta_config.yaml``. Values that differ between deployments, control
    safety boundaries, or contain credentials live here.
    """

    model_config = SettingsConfigDict(  # 调用 SettingsConfigDict 构造结果并保存到 model_config
        env_file=".env",  # 为 SettingsConfigDict 设置关键字参数 env_file，传入当前行给出的值
        env_file_encoding="utf-8",  # 为 SettingsConfigDict 设置关键字参数 env_file_encoding，传入当前行给出的值
        case_sensitive=False,  # 为 SettingsConfigDict 设置关键字参数 case_sensitive，传入当前行给出的值
        extra="ignore",  # 为 SettingsConfigDict 设置关键字参数 extra，传入当前行给出的值
        populate_by_name=True,  # 为 SettingsConfigDict 设置关键字参数 populate_by_name，传入当前行给出的值
    )  # 结束 SettingsConfigDict 调用参数，得到完整表达式结果

    app_name: str = "data-chat-agent"  # 计算 "data-chat-agent" 并保存到变量 app_name
    app_version: str = "0.2.0"  # 计算 "0.2.0" 并保存到变量 app_version
    environment: Literal["development", "test", "staging", "production"] = Field(  # 调用 Field 构造结果并保存到 environment
        default="development",  # 为 Field 设置关键字参数 default，传入当前行给出的值
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),  # 为 AliasChoices 设置关键字参数 validation_alias，传入当前行给出的值
    )  # 结束 Field 调用参数，得到完整表达式结果
    api_host: str = "0.0.0.0"  # 计算 "0.0.0.0" 并保存到变量 api_host
    api_port: int = Field(default=8000, ge=1, le=65535)  # 计算 Field(default=8000, ge=1, le=65535) 并保存到变量 api_port
    api_workers: int = Field(default=2, ge=1, le=32)  # 计算 Field(default=2, ge=1, le=32) 并保存到变量 api_workers
    log_level: str = "INFO"  # 计算 "INFO" 并保存到变量 log_level
    log_json: bool = True  # 计算 True 并保存到变量 log_json
    log_to_file: bool = False  # 计算 False 并保存到变量 log_to_file
    log_file_path: str = "logs"  # 计算 "logs" 并保存到变量 log_file_path
    cors_allowed_origins: str = "http://localhost:5173"  # 计算 "http://localhost:5173" 并保存到变量 cors_allowed_origins
    trusted_hosts: str = "localhost,127.0.0.1,testserver"  # 计算 "localhost,127.0.0.1,testserver" 并保存到变量 trusted_hosts

    postgres_dsn: str = (  # 调用 目标函数 构造结果并保存到 postgres_dsn
        "postgresql://postgres:postgres@localhost:5432/data_chat_agent"  # 在类 Settings 中执行声明或表达式 "postgresql://postgres:postgres@localhost:5432/data_chat_agent"，提供实例所需能力
    )  # 结束上一处多行结构，保持表达式边界清晰
    postgres_schema: str = Field(  # 调用 Field 构造结果并保存到 postgres_schema
        default="harness", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"  # 为 Field 设置关键字参数 default，传入当前行给出的值
    )  # 结束 Field 调用参数，得到完整表达式结果
    postgres_langgraph_schema: str = Field(  # 调用 Field 构造结果并保存到 postgres_langgraph_schema
        default="langgraph", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"  # 为 Field 设置关键字参数 default，传入当前行给出的值
    )  # 结束 Field 调用参数，得到完整表达式结果
    postgres_pool_max_size: int = Field(default=20, ge=1)  # 计算 Field(default=20, ge=1) 并保存到变量 postgres_pool_max_size

    redis_url: str = "redis://localhost:6379/0"  # 计算 "redis://localhost:6379/0" 并保存到变量 redis_url
    redis_pool_max_connections: int = Field(default=100, ge=1)  # 计算 Field(default=100, ge=1) 并保存到变量 redis_pool_max_connections
    redis_cache_ttl_seconds: int = Field(default=900, ge=30)  # 计算 Field(default=900, ge=30) 并保存到变量 redis_cache_ttl_seconds
    redis_event_ttl_seconds: int = Field(default=3600, ge=60)  # 计算 Field(default=3600, ge=60) 并保存到变量 redis_event_ttl_seconds

    oidc_issuer: str | None = None  # 计算 None 并保存到变量 oidc_issuer
    oidc_audience: str | None = None  # 计算 None 并保存到变量 oidc_audience
    oidc_jwks_url: str | None = None  # 计算 None 并保存到变量 oidc_jwks_url
    oidc_roles_claim: str = "roles"  # 计算 "roles" 并保存到变量 oidc_roles_claim
    oidc_tenant_claim: str = "tenant_id"  # 计算 "tenant_id" 并保存到变量 oidc_tenant_claim
    oidc_user_claim: str = "sub"  # 计算 "sub" 并保存到变量 oidc_user_claim
    dev_auth_enabled: bool = False  # 计算 False 并保存到变量 dev_auth_enabled
    dev_user_id: str = "local-user"  # 计算 "local-user" 并保存到变量 dev_user_id
    dev_tenant_id: str = "local-tenant"  # 计算 "local-tenant" 并保存到变量 dev_tenant_id
    dev_roles: str = "agent:user,agent:approver,agent:admin"  # 计算 "agent:user,agent:approver,agent:admin" 并保存到变量 dev_roles

    agent_execution_enabled: bool = True  # 计算 True 并保存到变量 agent_execution_enabled
    enabled_agent_ids: str = "analytics_sql,catalog_qa"  # 计算 "analytics_sql,catalog_qa" 并保存到变量 enabled_agent_ids
    worker_concurrency: int = Field(default=32, ge=1, le=256)  # 计算 Field(default=32, ge=1, le=256) 并保存到变量 worker_concurrency
    worker_lease_seconds: int = Field(default=60, ge=15)  # 计算 Field(default=60, ge=15) 并保存到变量 worker_lease_seconds
    worker_heartbeat_seconds: int = Field(default=20, ge=5)  # 计算 Field(default=20, ge=5) 并保存到变量 worker_heartbeat_seconds
    worker_poll_seconds: float = Field(default=0.5, gt=0)  # 计算 Field(default=0.5, gt=0) 并保存到变量 worker_poll_seconds
    job_max_attempts: int = Field(default=3, ge=1, le=10)  # 计算 Field(default=3, ge=1, le=10) 并保存到变量 job_max_attempts
    queue_max_depth: int = Field(default=1000, ge=1)  # 计算 Field(default=1000, ge=1) 并保存到变量 queue_max_depth

    run_max_wall_seconds: int = Field(default=180, ge=10)  # 计算 Field(default=180, ge=10) 并保存到变量 run_max_wall_seconds
    run_max_llm_calls: int = Field(default=10, ge=1)  # 计算 Field(default=10, ge=1) 并保存到变量 run_max_llm_calls
    run_max_tokens: int = Field(default=64_000, ge=1000)  # 计算 Field(default=64_000, ge=1000) 并保存到变量 run_max_tokens
    run_max_sql_corrections: int = Field(default=1, ge=0, le=1)  # 计算 Field(default=1, ge=0, le=1) 并保存到变量 run_max_sql_corrections
    human_wait_ttl_seconds: int = Field(default=86_400, ge=60)  # 计算 Field(default=86_400, ge=60) 并保存到变量 human_wait_ttl_seconds
    max_approval_rounds: int = Field(default=2, ge=1)  # 计算 Field(default=2, ge=1) 并保存到变量 max_approval_rounds

    per_user_active_runs: int = Field(default=5, ge=1)  # 计算 Field(default=5, ge=1) 并保存到变量 per_user_active_runs
    per_tenant_active_runs: int = Field(default=50, ge=1)  # 计算 Field(default=50, ge=1) 并保存到变量 per_tenant_active_runs
    rate_limit_runs_per_minute: int = Field(default=1200, ge=1)  # 计算 Field(default=1200, ge=1) 并保存到变量 rate_limit_runs_per_minute

    max_query_chars: int = Field(default=4000, ge=1)  # 计算 Field(default=4000, ge=1) 并保存到变量 max_query_chars
    max_request_bytes: int = Field(default=1_048_576, ge=1024)  # 计算 Field(default=1_048_576, ge=1024) 并保存到变量 max_request_bytes
    result_max_rows: int = Field(default=1000, ge=1)  # 计算 Field(default=1000, ge=1) 并保存到变量 result_max_rows
    result_max_bytes: int = Field(default=2 * 1024 * 1024, ge=1024)  # 计算 Field(default=2 * 1024 * 1024, ge=1024) 并保存到变量 result_max_bytes
    sql_timeout_ms: int = Field(default=15_000, ge=100)  # 计算 Field(default=15_000, ge=100) 并保存到变量 sql_timeout_ms
    sql_approval_scan_rows: int = Field(default=100_000, ge=1)  # 计算 Field(default=100_000, ge=1) 并保存到变量 sql_approval_scan_rows
    sql_high_risk_scan_rows: int = Field(default=1_000_000, ge=1)  # 计算 Field(default=1_000_000, ge=1) 并保存到变量 sql_high_risk_scan_rows
    sql_sensitive_columns: str = ""  # 计算 "" 并保存到变量 sql_sensitive_columns

    session_retention_days: int = Field(default=30, ge=1)  # 计算 Field(default=30, ge=1) 并保存到变量 session_retention_days
    event_retention_days: int = Field(default=7, ge=1)  # 计算 Field(default=7, ge=1) 并保存到变量 event_retention_days
    audit_retention_days: int = Field(default=180, ge=1)  # 计算 Field(default=180, ge=1) 并保存到变量 audit_retention_days
    idempotency_retention_days: int = Field(default=30, ge=1)  # 计算 Field(default=30, ge=1) 并保存到变量 idempotency_retention_days

    otel_enabled: bool = True  # 计算 True 并保存到变量 otel_enabled
    otel_exporter_endpoint: str = "http://localhost:4318"  # 计算 "http://localhost:4318" 并保存到变量 otel_exporter_endpoint
    otel_sample_ratio: float = Field(default=1.0, ge=0, le=1)  # 计算 Field(default=1.0, ge=0, le=1) 并保存到变量 otel_sample_ratio
    otel_service_name: str = "data-chat-agent"  # 计算 "data-chat-agent" 并保存到变量 otel_service_name
    langfuse_host: str | None = None  # 计算 None 并保存到变量 langfuse_host
    langfuse_public_key: SecretStr | None = None  # 计算 None 并保存到变量 langfuse_public_key
    langfuse_secret_key: SecretStr | None = None  # 计算 None 并保存到变量 langfuse_secret_key
    langfuse_capture_content: bool = False  # 计算 False 并保存到变量 langfuse_capture_content

    llm_timeout_seconds: float = Field(default=45.0, gt=0)  # 计算 Field(default=45.0, gt=0) 并保存到变量 llm_timeout_seconds
    llm_max_concurrency: int = Field(default=32, ge=1)  # 计算 Field(default=32, ge=1) 并保存到变量 llm_max_concurrency
    llm_model_name: str = "Pro/zai-org/GLM-5.1"  # 计算 "Pro/zai-org/GLM-5.1" 并保存到变量 llm_model_name
    llm_base_url: str = "https://api.siliconflow.cn/v1"  # 计算 "https://api.siliconflow.cn/v1" 并保存到变量 llm_base_url
    llm_api_key: SecretStr | None = None  # 计算 None 并保存到变量 llm_api_key
    retrieval_max_concurrency: int = Field(default=8, ge=1)  # 计算 Field(default=8, ge=1) 并保存到变量 retrieval_max_concurrency
    external_tool_max_concurrency: int = Field(default=32, ge=1)  # 计算 Field(default=32, ge=1) 并保存到变量 external_tool_max_concurrency
    tool_timeout_seconds: float = Field(default=15.0, gt=0)  # 计算 Field(default=15.0, gt=0) 并保存到变量 tool_timeout_seconds
    retrieval_max_terms: int = Field(default=20, ge=1)  # 计算 Field(default=20, ge=1) 并保存到变量 retrieval_max_terms
    max_history_turns: int = Field(default=6, ge=1)  # 计算 Field(default=6, ge=1) 并保存到变量 max_history_turns
    max_history_tokens: int = Field(default=8000, ge=100)  # 计算 Field(default=8000, ge=100) 并保存到变量 max_history_tokens
    router_min_confidence: float = Field(default=0.8, ge=0, le=1)  # 计算 Field(default=0.8, ge=0, le=1) 并保存到变量 router_min_confidence
    router_min_margin: float = Field(default=0.15, ge=0, le=1)  # 计算 Field(default=0.15, ge=0, le=1) 并保存到变量 router_min_margin

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def is_production(self) -> bool:  # 定义函数 is_production，封装该模块的一项明确职责
        return self.environment in {"staging", "production"}  # 返回 self.environment in {"staging", "production"} 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def cors_origins(self) -> list[str]:  # 定义函数 cors_origins，封装该模块的一项明确职责
        return _split_csv(self.cors_allowed_origins)  # 返回 _split_csv(self.cors_allowed_origins) 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def trusted_host_values(self) -> list[str]:  # 定义函数 trusted_host_values，封装该模块的一项明确职责
        return _split_csv(self.trusted_hosts)  # 返回 _split_csv(self.trusted_hosts) 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def dev_role_values(self) -> list[str]:  # 定义函数 dev_role_values，封装该模块的一项明确职责
        return _split_csv(self.dev_roles)  # 返回 _split_csv(self.dev_roles) 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def enabled_agents(self) -> list[str]:  # 定义函数 enabled_agents，封装该模块的一项明确职责
        return _split_csv(self.enabled_agent_ids)  # 返回 _split_csv(self.enabled_agent_ids) 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def sensitive_columns(self) -> set[str]:  # 定义函数 sensitive_columns，封装该模块的一项明确职责
        return {item.lower() for item in _split_csv(self.sql_sensitive_columns)}  # 返回 {item.lower() for item in _split_csv(self.sql_sensitive_columns)} 给调用方

    @property  # 应用装饰器 property，为紧随其后的定义附加框架行为
    def langfuse_enabled(self) -> bool:  # 定义函数 langfuse_enabled，封装该模块的一项明确职责
        return bool(  # 返回 bool( 给调用方
            self.langfuse_host  # 在函数 langfuse_enabled 中执行表达式 self.langfuse_host，推进当前业务流程
            and self.langfuse_public_key  # 在函数 langfuse_enabled 中执行表达式 and self.langfuse_public_key，推进当前业务流程
            and self.langfuse_public_key.get_secret_value()  # 调用 目标函数 执行当前步骤：and self.langfuse_public_key.get_secret_value()
            and self.langfuse_secret_key  # 在函数 langfuse_enabled 中执行表达式 and self.langfuse_secret_key，推进当前业务流程
            and self.langfuse_secret_key.get_secret_value()  # 调用 目标函数 执行当前步骤：and self.langfuse_secret_key.get_secret_value()
        )  # 结束函数 langfuse_enabled 的参数及返回类型声明并开始函数体

    @model_validator(mode="after")  # 应用装饰器 model_validator(mode="after")，为紧随其后的定义附加框架行为
    def validate_production_contracts(self) -> "Settings":  # 定义函数 validate_production_contracts，封装该模块的一项明确职责
        parsed_postgres = urlparse(self.postgres_dsn)  # 计算 urlparse(self.postgres_dsn) 并保存到变量 parsed_postgres
        if parsed_postgres.scheme not in {  # 判断分支条件：if parsed_postgres.scheme not in {
            "postgresql",  # 向多行序列加入元素 "postgresql"
            "postgres",  # 向多行序列加入元素 "postgres"
            "postgresql+psycopg",  # 向多行序列加入元素 "postgresql+psycopg"
        }:  # 在函数 validate_production_contracts 中执行表达式 }:，推进当前业务流程
            raise ValueError("POSTGRES_DSN must be a PostgreSQL DSN")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("POSTGRES_DSN must be a PostgreSQL DSN")

        parsed_redis = urlparse(self.redis_url)  # 计算 urlparse(self.redis_url) 并保存到变量 parsed_redis
        if parsed_redis.scheme not in {"redis", "rediss"}:  # 判断分支条件：if parsed_redis.scheme not in {"redis", "rediss"}:
            raise ValueError("REDIS_URL must be a Redis URL")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("REDIS_URL must be a Redis URL")

        if self.worker_heartbeat_seconds >= self.worker_lease_seconds:  # 判断分支条件：if self.worker_heartbeat_seconds >= self.worker_lease_seconds:
            raise ValueError("WORKER_HEARTBEAT_SECONDS must be below lease duration")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("WORKER_HEARTBEAT_SECONDS must be below lease duration")

        if self.sql_high_risk_scan_rows <= self.sql_approval_scan_rows:  # 判断分支条件：if self.sql_high_risk_scan_rows <= self.sql_approval_scan_rows:
            raise ValueError(  # 抛出明确异常，阻止错误状态被静默接受：ValueError(
                "SQL_HIGH_RISK_SCAN_ROWS must exceed SQL_APPROVAL_SCAN_ROWS"  # 在函数 validate_production_contracts 中执行表达式 "SQL_HIGH_RISK_SCAN_ROWS must exceed SQL_APPROVAL_SCAN_ROWS"，推进当前业务流程
            )  # 结束函数 validate_production_contracts 的参数及返回类型声明并开始函数体

        if self.is_production:  # 判断分支条件：if self.is_production:
            required = {  # 计算 { 并保存到变量 required
                "OIDC_ISSUER": self.oidc_issuer,  # 为多行字典定义键 "OIDC_ISSUER" 及其对应值
                "OIDC_AUDIENCE": self.oidc_audience,  # 为多行字典定义键 "OIDC_AUDIENCE" 及其对应值
                "OIDC_JWKS_URL": self.oidc_jwks_url,  # 为多行字典定义键 "OIDC_JWKS_URL" 及其对应值
            }  # 结束上一处多行结构，保持表达式边界清晰
            missing = [name for name, value in required.items() if not value]  # 计算 [name for name, value in required.items() if not value] 并保存到变量 missing
            if missing:  # 判断分支条件：if missing:
                raise ValueError(  # 抛出明确异常，阻止错误状态被静默接受：ValueError(
                    "production OIDC configuration is incomplete: "  # 在函数 validate_production_contracts 中执行表达式 "production OIDC configuration is incomplete: "，推进当前业务流程
                    + ", ".join(missing)  # 调用 目标函数 执行当前步骤：+ ", ".join(missing)
                )  # 结束函数 validate_production_contracts 的参数及返回类型声明并开始函数体
            if self.dev_auth_enabled:  # 判断分支条件：if self.dev_auth_enabled:
                raise ValueError("DEV_AUTH_ENABLED is forbidden in production")  # 抛出明确异常，阻止错误状态被静默接受：ValueError("DEV_AUTH_ENABLED is forbidden in production")

        return self  # 返回 self 给调用方


def _split_csv(value: str) -> list[str]:  # 定义函数 _split_csv，封装该模块的一项明确职责
    return [item.strip() for item in value.split(",") if item.strip()]  # 返回 [item.strip() for item in value.split(",") if item.strip()] 给调用方


@lru_cache(maxsize=1)  # 应用装饰器 lru_cache(maxsize=1)，为紧随其后的定义附加框架行为
def get_settings() -> Settings:  # 定义函数 get_settings，封装该模块的一项明确职责
    """Return one process-wide immutable settings instance."""

    return Settings()  # 返回 Settings() 给调用方
