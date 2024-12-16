from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    vault_addr: str = Field(
        default="http://localhost:8200", description="Vault address."
    )
    vault_namespace: str = Field(default="vault", description="Vault namespace.")
    vault_auth_mount_point: str = Field(default="kubernetes", description="Mount point for Kubernetes authentication.")
    token: str = Field(default="dev-token", description="Vault token.")
    secret_key_name: str = Field(
        default="key", description="Name of the key for stored secrets."
    )
    kube_role: Optional[str] = Field(
        default=None,
        description="Vault Kubernetes authentication role name.",
    )

    path_prefix: str = Field(default="", description="Path prefix for secret paths.")
    path_int_private: str = Field(
        default="ghga-auth/private", description="Internal key pair private path."
    )
    path_int_public: str = Field(
        default="ghga-auth/public", description="Internal key pair public path."
    )
    path_ext_public: str = Field(
        default="oidc/public", description="External OIDC key public path."
    )
    path_wps_private: str = Field(
        default="work-package-sign/private",
        description="Private work-package signing key path.",
    )
    path_wps_public: str = Field(
        default="work-package-sign/public",
        description="Public work-package signing key path.",
    )

    mount_point: str = Field(
        default="secret", description="Mount point for secrets engine."
    )

    verify_write: bool = Field(default=True, description="Flag to verify write.")
    show_external_keys: bool = Field(
        default=True, description="Flag to show external keys."
    )

    ssl_verify: bool = Field(
        default=False, description="SSL verification flag for Vault."
    )

    sa_token_path: str = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Kubernetes service account token path.",
    )

    oidc_authority_url: str = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/",
        description="OIDC authority URL.",
    )
    discovery_url: str = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/.well-known/openid-configuration",
        description="OIDC discovery URL.",
    )

    timeout: int = Field(default=30, description="Timeout in seconds.")

    @validator("path_prefix")
    def ensure_slash_prefix(cls, v: str) -> str:
        return v.rstrip("/") + "/"

    class Config:
        env_prefix = "AUTH_KM_JOBS_"  # Prefix for environment variables
