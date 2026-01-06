from valkey_setup.core import BaseBuilder, BuildSpec, BuildahContainer, prune_cache_images


class ValkeySearchBuilder(BaseBuilder):
    def __init__(self, config: BuildSpec, ext_version: str = "", cache_prefix: str = ""):
        self._init_ext_version(config, ext_version)
        super().__init__(config, cache_prefix)
        self.base_image = self.config.BaseImage
        self.image_name = f"{self.config.ProjectName}-valkeysearch"
        self.image_tag = self.config.Valkey.Version + "-" + self.ext_version

    def _init_ext_version(self, config: BuildSpec, ext_version: str):
        if not len(ext_version) > 0 or ext_version == "latest":
            ext_version = config.ValkeySearch.Current

        for version, data in config.ValkeySearch.Versions.items():
            if version == ext_version:
                self.ext_version = ext_version
                self.version_config = data
                return

        raise RuntimeError(f"No config found for valkey-json extension version {ext_version}")

    def _init_cache_prefix(self, cache_prefix: str):
        if len(cache_prefix) > 0:
            self.cache_prefix = cache_prefix
        else:
            self.cache_prefix = f"{self.config.ProjectName}/cache/valkeysearch/{self.ext_version}"

    def build(self):
        self.log(f"Starting build for ValkeySearch {self.ext_version}", style="bold blue")

        current_step = 1
        total_no_of_steps = 5

        with BuildahContainer(
                base_image=self.base_image,
                image_name=self.image_name,
                config=self.config,
                cache_prefix=self.cache_prefix
        ) as container:
            if self.version_config.Build.Dependencies:
                self.log(
                    f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Installing build dependencies")

                container.run_cached(
                    command=[
                        "sh", "-c",
                        f"""
                        zypper --non-interactive refresh &&
                        zypper --non-interactive install """ + " ".join(self.version_config.Build.Dependencies)],
                    extra_cache_keys={"step": "deps", "packages": sorted(self.version_config.Build.Dependencies)}
                )
                current_step += 1

            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Cloning {self.version_config.SourceUrl} tag {self.ext_version}")
            src_dir = f"/tmp/valkeysearch-{self.ext_version}"
            container.run_cached(
                command=[
                    "git", "clone", "--depth", "1", "--branch", self.ext_version,
                    self.version_config.SourceUrl, src_dir
                ],
                extra_cache_keys={"step": "source", "url": self.version_config.SourceUrl,
                                  "version": self.ext_version, "src_dir": src_dir}
            )

            current_step += 1
            self.log(f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Compiling and installing")

            flags = " ".join(self.version_config.Build.Flags)
            env = " ".join(self.version_config.Build.Env)
            container.run_cached(
                command=[
                    "sh", "-c",
                    f"""
                    cd {src_dir} &&
                    mkdir -p build && cd build &&
                    {env} cmake .. {flags} &&
                    make -j{self.version_config.Build.Cpu}""",
                ],
                extra_cache_keys={"step": "compile", "version": self.config.Valkey.Version, "flags": flags,
                                  "env": env}
            )

            module_dir = f"{self.config.Valkey.Prefix}/modules"
            so_file_name = "valkeysearch.so"

            container.run(
                command=["mkdir", "-p", module_dir]
            )

            container.run(
                command=["sh", "-c", f"find {src_dir} -name '*.so' -exec cp {{}} {module_dir}/{so_file_name} \\;"]
            )

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Verifying installation.")

            try:
                container.run(["ls", "-la", f"{module_dir}/{so_file_name}"])
            except Exception:
                self.log(f"[bold red]Error[/bold red]: {so_file_name} not found in {module_dir}")
                raise

            current_step += 1
            image_name_tag = self.image_name + ":" + self.image_tag
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Tagging image and adding metadata.")

            container.configure([
                ("--label",
                 f'org.opencontainers.image.title="Valkey {self.config.Valkey.Version} with ValkeySearch {self.ext_version}"'),
                ("--label", f'org.valkeysearch.version={self.ext_version}'),
            ])
            container.commit(image_name_tag)

            self.log(f"Image tagged as: [green]{image_name_tag}[/green]")

    def prune_cache_images(self):
        prune_cache_images(self.config.Buildah.Path, self.cache_prefix)
