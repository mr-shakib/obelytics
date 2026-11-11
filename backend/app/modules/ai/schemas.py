from typing import Literal

from pydantic import BaseModel

ProviderName = Literal["local", "hosted", "off"]


class ProviderStatus(BaseModel):
    name: Literal["local", "hosted"]
    configured: bool
    # External: data leaves your servers, so personal data is redacted first.
    external: bool
    models: dict[str, str | None]
    # Local only: whether the model server answered, and which models it has pulled.
    reachable: bool | None = None
    installed_models: list[str] | None = None


class FeatureSetting(BaseModel):
    feature: Literal["integrity", "copilot"]
    # None: the organization has not chosen, so the server default applies.
    chosen: ProviderName | None
    default: ProviderName
    effective: ProviderName


class AISettingsResponse(BaseModel):
    features: list[FeatureSetting]
    providers: list[ProviderStatus]


class AISettingsUpdate(BaseModel):
    # Send null to go back to the server default. Omitted fields are left unchanged.
    integrity_provider: ProviderName | None = None
    copilot_provider: ProviderName | None = None


class UsageRow(BaseModel):
    feature: str
    provider: str
    model: str
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    images: int
    redactions: int
    cost_usd: float
    avg_latency_ms: int


class AIUsageResponse(BaseModel):
    days: int
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    redactions: int
    cost_usd: float
    rows: list[UsageRow]
