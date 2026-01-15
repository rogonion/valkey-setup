from pathlib import Path
from typing import Optional, List, Tuple

import typer

from .builder import RuntimeBuilder
from valkey_setup.core import BuildSpec, load_spec

app = typer.Typer(help="A valkey runtime. Optionally with modules.")


def parse_modules(value: str) -> List[Tuple[str, str]]:
    """
    Converts 'valkey-json=1.0.0,valkey-search=latest'
    into [('valkey-json', '1.0.0'), ('valkey-search', 'latest')]
    """
    if not value:
        return []

    results = []
    for item in value.split(","):
        if "=" in item:
            name, version = item.split("=", 1)
            results.append((name.strip(), version.strip()))
        else:
            # Default to 'latest' or a version specified in your YAML
            results.append((item.strip(), "latest"))
    return results


@app.command("build", help="Build a valkey runtime image with modules (optional).")
def build(
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        image_name: Optional[str] = typer.Option("valkey", "--image-name", "--n",
                                                 help="Name of new valkey runtime image."),
        image_tag: Optional[str] = typer.Option("", "--image-tag", "--t",
                                                help="Optional. Tag of new valkey runtime image"),
        modules: Optional[str] = typer.Option("", "--modules", "--m",
                                              help="Optional. Comma-separated list of modules e.g, valkey-json=1.0.0, valkey-search=latest"),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers."),
        remove_package_manager: Optional[bool] = typer.Option(True, "--remove-package-manager", "--rp",
                                                              help="Optional. Remove dependency manager at the end of image build. Slims the image and improves security."),
        squash: Optional[bool] = typer.Option(True, "--squash", "--sq",
                                              help="Optional. Merge layers into one. Important if remove_package_manager is set to True")
):
    """
    Build valkey runtime image with optional modules.

    :param squash:
    :param remove_package_manager:
    :param cache_prefix:
    :param spec_file:
    :param image_name:
    :param image_tag:
    :param modules:
    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    module_list = parse_modules(modules)

    builder = RuntimeBuilder(config, cache_prefix, image_name, image_tag, modules=module_list,
                             remove_package_manager=remove_package_manager, squash=squash)

    builder.build()


@app.command("delete-cache", help="Delete cache images used to build valkey runtime image.")
def delete_cache(
        spec_file: Optional[Path] = typer.Option("configs/build.yaml", "--spec", "--s",
                                                 help="Path to build specification file."),
        cache_prefix: Optional[str] = typer.Option("", "--cache-prefix", "--c",
                                                   help="Optional. Custom prefix for generated images acting as cache layers.")
):
    """
    Delete cache images used to build valkey binaries from source (core).

    :param spec_file: Path to build spec file.
    :param cache_prefix: Custom prefix for cache layers generated.

    :return:
    """
    config = load_spec(spec_file, BuildSpec)

    builder = RuntimeBuilder(config, cache_prefix)

    builder.prune_cache_images()
