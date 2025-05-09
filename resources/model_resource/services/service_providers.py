from dataclasses import dataclass
from enum import Enum
from typing import Callable

from resources.model_resource.services.auth_helpers import (
    _auth_anthropic_api_key,
    _auth_google_api_key,
    _auth_helm_api_key,
    _auth_openai_api_key,
    _auth_together_api_key,
    _auth_xai_api_key,
)


class ServiceProvider(Enum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"
    TOGETHER = "together"
    XAI = "xai"
    HELM = "helm"


@dataclass(frozen=True)
class ServiceProviderConfig:
    name: str
    api_key_name: str
    auth_function: Callable


PROVIDER_CONFIG: dict[ServiceProvider, ServiceProviderConfig] = {
    ServiceProvider.ANTHROPIC: ServiceProviderConfig(
        name="anthropic",
        api_key_name="ANTHROPIC_API_KEY",
        auth_function=_auth_anthropic_api_key,
    ),
    ServiceProvider.OPENAI: ServiceProviderConfig(
        name="openai",
        api_key_name="OPENAI_API_KEY",
        auth_function=_auth_openai_api_key,
    ),
    ServiceProvider.GOOGLE: ServiceProviderConfig(
        name="google",
        api_key_name="GOOGLE_API_KEY",
        auth_function=_auth_google_api_key,
    ),
    ServiceProvider.TOGETHER: ServiceProviderConfig(
        name="together",
        api_key_name="TOGETHER_API_KEY",
        auth_function=_auth_together_api_key,
    ),
    ServiceProvider.XAI: ServiceProviderConfig(
        name="xai",
        api_key_name="XAI_API_KEY",
        auth_function=_auth_xai_api_key,
    ),
    ServiceProvider.HELM: ServiceProviderConfig(
        name="helm",
        api_key_name="HELM_API_KEY",
        auth_function=_auth_helm_api_key,
    ),
}

ALL_API_KEYS: list[str] = [config.api_key_name for config in PROVIDER_CONFIG.values()]

API_KEY_TO_AUTH: dict[str, Callable] = {
    config.api_key_name: config.auth_function for config in PROVIDER_CONFIG.values()
}
