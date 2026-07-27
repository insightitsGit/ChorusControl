from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ChorusControl"
    product_title: str = "ChorusControl — AI Operations Platform"
    host: str = "0.0.0.0"
    port: int = 8443
    demo_mode: bool = Field(default=False, alias="CHORUSCONTROL_DEMO_MODE")

    license_key: str | None = Field(default=None, alias="CHORUSCONTROL_LICENSE_KEY")
    license_grace_days: int = Field(default=14, alias="CHORUSCONTROL_LICENSE_GRACE_DAYS")
    license_clock_skew_seconds: int = Field(
        default=86400, alias="CHORUSCONTROL_LICENSE_CLOCK_SKEW_SECONDS"
    )

    admin_token: str = Field(default="dev-admin-token", alias="CHORUSCONTROL_ADMIN_TOKEN")
    audit_private_key_pem: str | None = Field(
        default=None, alias="CHORUSCONTROL_AUDIT_PRIVATE_KEY_PEM"
    )
    audit_log_path: Path = Field(
        default=Path("choruscontrol_audit.jsonl"), alias="CHORUSCONTROL_AUDIT_LOG_PATH"
    )

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    sqlite_path: Path = Field(
        default=Path("data/choruscontrol.db"), alias="CHORUSCONTROL_SQLITE_PATH"
    )

    fabric_endpoint: str | None = Field(default=None, alias="FABRIC_ENDPOINT")
    # R01: HTTP/PrismAPI primary; fabric optional
    transport_primary: Literal["http", "fabric"] = Field(
        default="http", alias="CHORUSCONTROL_TRANSPORT_PRIMARY"
    )

    insightits_support_url: str = Field(
        default="https://www.insightits.com/support", alias="INSIGHTITS_SUPPORT_URL"
    )
    insightits_portal_url: str = Field(
        default="https://www.insightits.com", alias="INSIGHTITS_PORTAL_URL"
    )

    jobs_max_concurrent: int = Field(default=2, alias="JOBS_MAX_CONCURRENT")
    invalidation_threshold: float = Field(default=0.55, alias="INVALIDATION_THRESHOLD")

    ledger_sample_rate: float = Field(default=0.1, alias="CHORUSCONTROL_LEDGER_SAMPLE_RATE")
    ledger_retention_days: int = Field(default=14, alias="CHORUSCONTROL_LEDGER_RETENTION_DAYS")
    ledger_tenant_quota: int = Field(default=100_000, alias="CHORUSCONTROL_LEDGER_TENANT_QUOTA")
    trace_retention_days: int = Field(default=14, alias="CHORUSCONTROL_TRACE_RETENTION_DAYS")
    trace_max_rows: int = Field(default=100_000, alias="CHORUSCONTROL_TRACE_MAX_ROWS")
    allow_insecure_external: bool = Field(
        default=False, alias="CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL"
    )

    mother_url: str | None = Field(default=None, alias="CHORUSCONTROL_MOTHER_URL")
    join_token: str | None = Field(default=None, alias="CHORUSCONTROL_JOIN_TOKEN")
    node_id: str | None = Field(default=None, alias="CHORUSCONTROL_NODE_ID")
    node_role: str = Field(default="worker", alias="CHORUSCONTROL_NODE_ROLE")
    network_zone: Literal["in_vpc", "external"] = Field(
        default="in_vpc", alias="CHORUSCONTROL_NETWORK_ZONE"
    )
    tenant_id: str = Field(default="default", alias="CHORUSCONTROL_TENANT_ID")
    heartbeat_interval_seconds: float = Field(default=10.0, alias="CHORUSCONTROL_HEARTBEAT_INTERVAL")

    # OIDC / SSO (optional enterprise)
    oidc_enabled: bool = Field(default=False, alias="CHORUSCONTROL_OIDC_ENABLED")
    oidc_issuer: str | None = Field(default=None, alias="CHORUSCONTROL_OIDC_ISSUER")
    oidc_audience: str | None = Field(default=None, alias="CHORUSCONTROL_OIDC_AUDIENCE")
    oidc_jwks_url: str | None = Field(default=None, alias="CHORUSCONTROL_OIDC_JWKS_URL")
    oidc_role_claim: str = Field(default="chorus_roles", alias="CHORUSCONTROL_OIDC_ROLE_CLAIM")

    # Metrics retention for predictive / RCA
    metrics_retention_hours: int = Field(default=168, alias="CHORUSCONTROL_METRICS_RETENTION_HOURS")
    metrics_sample_interval_seconds: float = Field(
        default=60.0, alias="CHORUSCONTROL_METRICS_SAMPLE_INTERVAL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
