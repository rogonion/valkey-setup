"""In-memory fakes over the ports: no buildah, network, or filesystem."""

from pathlib import Path
from typing import Protocol


class FakeReporter:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warn(self, message: str) -> None:
        self.messages.append(message)


class FakeFetcher:
    def __init__(self, archive: Path) -> None:
        self.archive = archive
        self.fetched: list[str] = []

    def fetch(self, pin: Protocol) -> Path:
        self.fetched.append(pin.version)
        return self.archive


class FakeRegistry:
    def __init__(self, tags: set[str] | None = None) -> None:
        self.tags = set(tags or [])
        self.pruned: list[str] = []

    def image_exists(self, tag: str) -> bool:
        return tag in self.tags

    def prune_cache(self, cache_prefix: str) -> list[str]:
        removed = [t for t in self.tags if t.startswith(cache_prefix + ":")]
        self.tags -= set(removed)
        self.pruned.extend(removed)
        return removed


class FakeSandbox:
    """Records sandbox calls; scripts capture() responses."""

    def __init__(self, *, version_output: str = "v=9.0.1") -> None:
        self.calls: list[tuple] = []
        self.version_output = version_output

    def begin(self, base_image: str, cache_prefix: str) -> None:
        self.calls.append(("begin", base_image, cache_prefix))

    def run(self, command, env=None) -> None:
        self.calls.append(("run", tuple(command), env))

    def capture(self, command, env=None) -> str:
        self.calls.append(("capture", tuple(command), env))
        if "--version" in command:
            return self.version_output
        if command and command[0] == "ls":
            return " ".join(command[1:])
        return ""

    def run_cached(self, command, env=None, cache_keys=None) -> None:
        self.calls.append(("run_cached", tuple(command), env, dict(cache_keys or {})))

    def copy_in(self, source: Path, dest: str) -> None:
        self.calls.append(("copy_in", source, dest))

    def copy_from_image(self, image: str, src: str, dest: str) -> None:
        self.calls.append(("copy_from_image", image, src, dest))

    def set_labels(self, labels) -> None:
        self.calls.append(("set_labels", dict(labels)))

    def set_env(self, env) -> None:
        self.calls.append(("set_env", dict(env)))

    def set_entrypoint(self, entrypoint) -> None:
        self.calls.append(("set_entrypoint", tuple(entrypoint)))

    def set_cmd(self, cmd) -> None:
        self.calls.append(("set_cmd", tuple(cmd)))

    def set_user(self, user: str) -> None:
        self.calls.append(("set_user", user))

    def set_ports(self, ports) -> None:
        self.calls.append(("set_ports", tuple(ports)))

    def set_volumes(self, volumes) -> None:
        self.calls.append(("set_volumes", tuple(volumes)))

    def commit(self, tag: str) -> None:
        self.calls.append(("commit", tag))

    def finish(self) -> None:
        self.calls.append(("finish",))
