from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration settings for the auth_km_jobs service."""

    # Vault settings
    vault_addr: str = Field(
        default="http://localhost:8200", description="Vault address."
    )
    vault_namespace: str = Field(default="vault", description="Vault namespace.")
    vault_auth_mount_point: str = Field(
        default="kubernetes", description="Mount point for Kubernetes authentication."
    )
    token: str = Field(default="dev-token", description="Vault token.")
    secret_key_name: str = Field(
        default="key", description="Name of the key for stored secrets."
    )
    kube_role: str | None = Field(
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
    path_totp_key: str = Field(
        default="totp/encryption-key",
        description="TOTP token symmetric encryption key path.",
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

    # OIDC settings

    oidc_authority_url: str = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/",
        description="OIDC authority URL.",
    )
    discovery_url: str = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/.well-known/openid-configuration",
        description="OIDC discovery URL.",
    )

    # MongoDB settings
    mongo_dsn: str = Field(
        default="mongodb://localhost:27017/",
        description="Auth service MongoDB connection string.",
    )
    db_name: str = Field(
        default="auth-service",
        description="Name of the auth service database.",
    )
    user_tokens_collection: str = Field(
        default="user_tokens",
        description="Name of the collection for user tokens.",
    )

    # General settings
    timeout: int = Field(default=30, description="Timeout in seconds.")

    @field_validator("path_prefix", mode="before")
    @classmethod
    def ensure_slash_prefix(cls, v: str | None) -> str:
        """Normalize path_prefix to always end with a single slash."""
        if not v:
            return "/"
        return v.rstrip("/") + "/"

    model_config = {
        "env_prefix": "AUTH_KM_JOBS_",
    }
