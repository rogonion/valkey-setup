from pathlib import Path
from typing import Tuple, List, Optional

from valkey_setup.containers.modules.valkey_bloom import ValkeyBloomRuntime
from valkey_setup.containers.modules.valkey_json import ValkeyJsonRuntime
from valkey_setup.containers.modules.valkey_search import ValkeySearchRuntime
from valkey_setup.core import BaseBuilder, BuildSpec, prune_cache_images, BuildahContainer

MODULES = ["valkey-json", "valkey-search", "valkey-bloom"]


class RuntimeBuilder(BaseBuilder):
    def __init__(self, config: BuildSpec, cache_prefix: str = "", image_name: str = "", image_tag: str = "",
                 modules: Optional[List[Tuple[str, str]]] = None):
        super().__init__(config, cache_prefix)

        if len(image_name) > 0:
            self.image_name = image_name
        else:
            self.image_name = f"{self.config.ProjectName}-runtime"

        if len(image_tag) > 0:
            self.image_tag = image_tag
        else:
            self.image_tag = self.config.Valkey.Version

        if modules:
            for module in modules:
                if not module[0] in MODULES:
                    raise RuntimeError(f"Module '{module[0]}' not found.")

        self.modules = modules

    def _init_cache_prefix(self, cache_prefix: str):
        if len(cache_prefix) > 0:
            self.cache_prefix = cache_prefix
        else:
            self.cache_prefix = f"{self.config.ProjectName}/cache/runtime/{self.config.Valkey.Version}"

    def build(self):
        self.log(f"Starting build for Valkey {self.config.Valkey.Version} runtime", style="bold blue")

        current_step = 1

        with BuildahContainer(
                base_image=self.config.BaseImage,
                image_name=self.image_name,
                config=self.config,
                cache_prefix=self.cache_prefix
        ) as container:

            self.log(f"[bold blue]Step {current_step}[/bold blue]: Retrieving valkey binaries")

            self.image_tag = self.config.Valkey.Version
            container.copy_container_current(f"{self.config.ProjectName}-core:{self.config.Valkey.Version}",
                                             self.config.Valkey.Prefix, self.config.Valkey.Prefix)

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}[/bold blue]: Installing valkey runtime dependencies")

            container.run_cached(
                command=[
                    "sh", "-c",
                    f"""
                        zypper --non-interactive refresh &&
                        zypper --non-interactive install """ + " ".join(self.config.Valkey.Runtime.Dependencies)],
                extra_cache_keys={"step": "deps", "packages": sorted(self.config.Valkey.Runtime.Dependencies)}
            )

            if self.modules:
                self.log(
                    f"[bold blue]Step {current_step}[/bold blue]: Installing modules {self.modules}")

                for module in self.modules:
                    match (module[0]):
                        case 'valkey-json':
                            valkeyjson_build = ValkeyJsonRuntime(self.config, container, module[1])
                            valkeyjson_build.build()
                        case 'valkey-search':
                            valkeybloom_build = ValkeySearchRuntime(self.config, container, module[1])
                            valkeybloom_build.build()
                        case 'valkey-bloom':
                            valkeybloom_build = ValkeyBloomRuntime(self.config, container, module[1])
                            valkeybloom_build.build()
                        case _:
                            self.log(f'[bold red]Error[/bold red]: ')
                            raise RuntimeError(f"Module {module[0]} not found.")

            container.run(
                command=[
                    "sh", "-c",
                    f"""
                    zypper --non-interactive remove -y rsync &&
                    zypper clean --all"""]
            )

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}[/bold blue]: Setting up system user")

            base_valkey_dir = "/var/lib/valkey"

            container.run(
                command=["groupadd", "-r", "-g", str(self.config.Valkey.Runtime.Gid), "valkey"]
            )

            container.run(
                command=["useradd", "-r", "-u", str(self.config.Valkey.Runtime.Uid), "-g",
                         str(self.config.Valkey.Runtime.Gid), "-d", base_valkey_dir, "-s", "/sbin/nologin", "-c",
                         '"Valkey Server"', "valkey"]
            )

            container.configure(
                [
                    ("--label", f"io.valkey.user.uid={self.config.Valkey.Runtime.Uid}"),
                    ("--label", f"io.valkey.user.gid={self.config.Valkey.Runtime.Gid}"),
                    ("--label", f"io.valkey.user.name=valkey"),
                ]
            )

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}[/bold blue]: Setting up directories & permissions")

            data_dir = f"{base_valkey_dir}/data"
            container.run(["mkdir", "-p", data_dir])
            container.run(["chown", "-R", f"{self.config.Valkey.Runtime.Uid}:{self.config.Valkey.Runtime.Gid}", base_valkey_dir])
            container.configure([
                ("--env", f"VALKEY_DATA={data_dir}"),
                ("--volume", data_dir),
                ("--env",
                 f"PATH={self.config.Valkey.Prefix}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
            ])

            # Config storage folder
            container.run(
                command=["mkdir", "-p", "/usr/share/valkey/config"]
            )

            # Valkey config files
            config_dir = "/usr/share/valkey/config"
            container.run(["mkdir", "-p", config_dir])
            container.copy_host_container(Path(f"{self.config.Valkey.Runtime.Resources}/valkey.conf"),
                                          f"{config_dir}/valkey.conf")

            # Valkey entrypoint script
            container.copy_host_container(Path(f"{self.config.Valkey.Runtime.Resources}/entrypoint.sh"),
                                          "/usr/local/bin/entrypoint.sh")

            # Setup permissions
            container.run(
                command=[
                    "chown", "-R", f"{self.config.Valkey.Runtime.Uid}:{self.config.Valkey.Runtime.Gid}",
                    "/usr/share/valkey/config",
                    "/usr/local/bin/entrypoint.sh"
                ]
            )

            container.run(
                command=[
                    "chmod", "+x", "/usr/local/bin/entrypoint.sh"
                ]
            )
            container.configure([
                ("--entrypoint", '["/usr/local/bin/entrypoint.sh"]'),
                ("--cmd", '["valkey-server", "/usr/share/valkey/config/valkey.conf"]'),
                ("--user", str(self.config.Valkey.Runtime.Uid))
            ])

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}[/bold blue]: Tagging image and adding metadata.")

            container.configure([
                ("--label", f"org.valkey.version={self.config.Valkey.Version}"),
                ("--label", f"org.valkey.prefix={self.config.Valkey.Prefix}"),
            ])
            if self.config.Valkey.Runtime.Ports:
                for port in self.config.Valkey.Runtime.Ports:
                    container.configure([
                        ("--port", f"{port}")
                    ])
            image_name_tag = self.image_name + ":" + self.image_tag
            container.commit(image_name_tag)

            self.log(f"Image tagged as: [green]{image_name_tag}[/green]")

    def prune_cache_images(self):
        prune_cache_images(self.config.Buildah.Path, self.cache_prefix)
