"""Typer CLI: the primary adapter and task-runner surface."""

from typing import Annotated

import typer

from valkey_setup.adapters.cli.run import (
    run_build,
    run_clean,
    run_module,
    run_pull,
    run_push,
    run_runtime,
)
from valkey_setup.domain.error import ValkeySetupError

app = typer.Typer(
    name="valkey-setup",
    help="Build pinned Valkey from source into artifact images and a runtime image.",
    no_args_is_help=True,
)

ProfileOption = Annotated[
    str | None,
    typer.Option("--profile", "-p", help="Build profile (see profiles.toml)."),
]
JobsOption = Annotated[
    int | None,
    typer.Option(
        "--jobs", "-j",
        help="Parallel compile jobs (default: profile jobs, else half the CPUs).",
    ),
]


@app.command()
def build(
    profile: ProfileOption = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Rebuild even if the image exists.")] = False,
    jobs: JobsOption = None,
) -> None:
    """Build the core artifact image (compiled valkey, no modules)."""
    try:
        run_build(profile, force=force, jobs=jobs)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def module(
    profile: ProfileOption = None,
    names: Annotated[
        list[str] | None,
        typer.Option("--name", "-m", help="Module to build (default: all profile modules)."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Rebuild even if the image exists.")] = False,
    jobs: JobsOption = None,
) -> None:
    """Build module artifact images (compiled .so per module)."""
    try:
        run_module(profile, names, force=force, jobs=jobs)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def runtime(
    profile: ProfileOption = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Rebuild even if the image exists.")] = False,
    jobs: JobsOption = None,
    from_source: Annotated[
        str,
        typer.Option(
            "--from",
            help="How to resolve a missing runtime image: auto (pull if a "
                 "registry is configured, else build) | build | pull.",
        ),
    ] = "auto",
) -> None:
    """Assemble the runtime image (core + modules; builds them if missing)."""
    try:
        run_runtime(profile, force=force, jobs=jobs, source=from_source)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def clean(
    profile: ProfileOption = None,
    cache: Annotated[bool, typer.Option("--cache", help="Prune the profile's layer-cache images.")] = False,
) -> None:
    """Prune layer-cache images for a profile."""
    try:
        run_clean(profile, cache=cache)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def profiles() -> None:
    """List the available build profiles."""
    from valkey_setup.adapters.cli.config import find_project_root, load_profiles

    try:
        root = find_project_root()
        loaded = load_profiles(root)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    for name in loaded.names():
        marker = " (default)" if name == loaded.default else ""
        typer.echo(f"{name}{marker}")
        profile = loaded.profiles[name]
        typer.echo(f"  base image: {profile.base_image}")
        typer.echo(f"  prefix:     {profile.prefix}")
        typer.echo(f"  jobs:       {profile.jobs or 'auto (half the CPUs)'}")
        typer.echo(f"  modules:    {', '.join(profile.modules) or '(none)'}")


@app.command()
def push(profile: ProfileOption = None) -> None:
    """Push the profile's runtime image to the configured registry."""
    try:
        run_push(profile)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def pull(profile: ProfileOption = None) -> None:
    """Pull the profile's runtime image from the configured registry."""
    try:
        run_pull(profile)
    except ValkeySetupError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
