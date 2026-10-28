"""Domain error taxonomy: the single source of raised errors.

Adapters translate subprocess exit codes, missing binaries, buildah
failures, filesystem and HTTP failures into these errors at the boundary.
Raw exceptions, exit codes, and stderr never travel past the adapter that
produced them.
"""


class ValkeySetupError(Exception):
    """Base for every error raised by this package."""


class ConfigError(ValkeySetupError):
    """pins.toml or profiles.toml is missing, unreadable, or invalid."""


class FetchError(ValkeySetupError):
    """A source tarball download failed."""


class ChecksumError(ValkeySetupError):
    """A downloaded (or cached) tarball does not match its pinned sha256."""


class SandboxError(ValkeySetupError):
    """A buildah sandbox command failed or buildah is unavailable."""


class VerificationError(ValkeySetupError):
    """A built binary reports the wrong version or a module artifact is missing."""


class ImageNotFoundError(ValkeySetupError):
    """A required artifact image is not present locally."""
