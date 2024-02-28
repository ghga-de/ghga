from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Config(BaseSettings):
    vault_addr: str = Field("http://localhost:8200", description="Vault address.")
    vault_namespace: str = Field("vault", description="Vault namespace.")
    token: str = Field("dev-token", description="Vault token.")
    secret_key_name: str = Field(
        "key", description="Name of the key for stored secrets."
    )
    kube_role: Optional[str] = Field(
        default=None,
        description="Vault Kubernetes authentication role name.",
    )

    path_prefix: str = Field("", description="Path prefix for secret paths.")
    path_int_private: str = Field(
        "ghga-auth/private", description="Internal key pair private path."
    )
    path_int_public: str = Field(
        "ghga-auth/public", description="Internal key pair public path."
    )
    path_ext_public: str = Field(
        "oidc/public", description="External OIDC key public path."
    )
    path_wps_private: str = Field(
        "work-package-sign/private",
        description="Private work-package signing key path.",
    )
    path_wps_public: str = Field(
        "work-package-sign/public", description="Public work-package signing key path."
    )

    mount_point: str = Field("secret", description="Mount point for secrets engine.")

    verify_write: bool = Field(True, description="Flag to verify write.")
    show_external_keys: bool = Field(True, description="Flag to show external keys.")

    ssl_verify: bool = Field(False, description="SSL verification flag for Vault.")
    timeout: int = Field(15, description="Timeout in seconds.")

    sa_token_path: str = Field(
        "/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Kubernetes service account token path.",
    )

    oidc_authority_url: str = Field(
        "https://proxy.aai.lifescience-ri.eu/", description="OIDC authority URL."
    )
    discovery_url: str = Field(
        f"https://proxy.aai.lifescience-ri.eu/.well-known/openid-configuration",
        description="OIDC discovery URL.",
    )
    timeout: int = Field(30, description="Timeout in seconds.")

    class Config:
        env_prefix = "AUTH_KM_JOBS_"  # Prefix for environment variables
