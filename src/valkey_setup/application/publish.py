"""Use cases: publish and fetch the final runtime image of a profile.

Registry distribution (ADR 0019): final images are the distribution unit -
never the hash-keyed cache layers. The from-source build remains the audit
path; the registry is the accelerator.
"""

import valkey_setup.domain.ports.infra as infra_ports
from valkey_setup.domain.error import ConfigError
from valkey_setup.domain.model.build import (
    Pins,
    Profile,
    RegistryConfig,
    remote_image_tag,
    runtime_image_tag,
)


class PushImages:
    """Push a profile's final runtime image to the configured registry."""

    def __init__(
        self,
        *,
        pins: Pins,
        transport: infra_ports.ImageTransport,
        reporter: infra_ports.Reporter,
    ) -> None:
        self._pins = pins
        self._transport = transport
        self._reporter = reporter

    def run(self, profile: Profile, config: RegistryConfig | None) -> str:
        if config is None:
            raise ConfigError(
                "registry.toml is not configured; copy registry.toml.example "
                "to registry.toml and set the namespace"
            )
        tag = runtime_image_tag(self._pins, profile)
        remote = remote_image_tag(tag, config)
        self._reporter.info(f"pushing {tag} -> {remote}")
        self._transport.push(tag, remote, tls_verify=config.tls_verify)
        self._reporter.info(f"pushed: {remote}")
        return remote


class PullImages:
    """Pull a profile's final runtime image, retagged to its local name."""

    def __init__(
        self,
        *,
        pins: Pins,
        transport: infra_ports.ImageTransport,
        reporter: infra_ports.Reporter,
    ) -> None:
        self._pins = pins
        self._transport = transport
        self._reporter = reporter

    def run(self, profile: Profile, config: RegistryConfig | None) -> str:
        if config is None:
            raise ConfigError(
                "registry.toml is not configured; copy registry.toml.example "
                "to registry.toml and set the namespace"
            )
        tag = runtime_image_tag(self._pins, profile)
        remote = remote_image_tag(tag, config)
        self._reporter.info(f"pulling {remote} -> {tag}")
        self._transport.pull(remote, tag, tls_verify=config.tls_verify)
        self._reporter.info(f"pulled: {tag}")
        return tag
