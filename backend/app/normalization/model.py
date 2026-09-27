"""Common normalized security model.

Beginner idea: "normalization" = converting different vendor syntax into ONE
common internal form. Cisco says `no service telnet`, Juniper says
`delete system services telnet`, Palo Alto deletes `deviceconfig system telnet`
— all three mean `management.telnet_enabled = False`.

The compliance engine (Phase 10) only reads THIS model, never vendor syntax.
That is why we never write `if vendor == "cisco"` inside compliance rules.
"""

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    hostname: str | None = None
    vendor: str = "unknown"


class Management(BaseModel):
    telnet_enabled: bool | None = None
    ssh_enabled: bool | None = None
    http_enabled: bool | None = None
    https_enabled: bool | None = None
    mgmt_restricted: bool | None = None
    unnecessary_services: bool | None = None


class Logging(BaseModel):
    enabled: bool | None = None
    security_logging: bool | None = None


class Authentication(BaseModel):
    strong_authentication: bool | None = None
    weak_creds_found: bool = False
    password_encryption: bool | None = None


class Snmp(BaseModel):
    enabled: bool | None = None
    insecure: bool | None = None


class Ntp(BaseModel):
    configured: bool | None = None
    servers: list[str] = Field(default_factory=list)


class NormalizedConfig(BaseModel):
    """Vendor-independent view of a device's security posture."""

    device: DeviceInfo = Field(default_factory=DeviceInfo)
    management: Management = Field(default_factory=Management)
    logging: Logging = Field(default_factory=Logging)
    authentication: Authentication = Field(default_factory=Authentication)
    snmp: Snmp = Field(default_factory=Snmp)
    ntp: Ntp = Field(default_factory=Ntp)
    # Evidence maps normalized field path -> exact config line, e.g.
    # {"management.telnet_enabled": "no service telnet"}.
    evidence: dict[str, str] = Field(default_factory=dict)
    # Lines no parser understood (future AI phase input).
    unknown_lines: list[str] = Field(default_factory=list)

    def get_field(self, dotted: str):
        """Read a value by dotted path, e.g. `management.telnet_enabled`."""
        current: object = self
        for part in dotted.split("."):
            if isinstance(current, BaseModel):
                current = getattr(current, part, None)
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
