from valkey_setup.core import BaseBuilder, BuildahContainer, prune_cache_images, BuildSpec, init_base_distro


class CoreBuilder(BaseBuilder):
    def __init__(self, config: BuildSpec, cache_prefix: str = ""):
        super().__init__(config, cache_prefix)
        self.image_name = f"{self.config.ProjectName}-core"
        self.image_tag = self.config.Valkey.Version

    def _init_cache_prefix(self, cache_prefix: str):
        if len(cache_prefix) > 0:
            self.cache_prefix = cache_prefix
        else:
            self.cache_prefix = f"{self.config.ProjectName}/cache/core/{self.config.Valkey.Version}"

    def build(self):
        self.log(f"Starting build for Valkey {self.config.Valkey.Version} core", style="bold blue")

        current_step = 1
        total_no_of_steps = 7

        with BuildahContainer(
                base_image=self.config.BaseImage,
                image_name=self.image_name,
                config=self.config,
                cache_prefix=self.cache_prefix
        ) as container:
            base_distro = init_base_distro(self.config.Distro, container)
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Installing build dependencies")

            base_distro.refresh_package_repository()

            base_distro.install_packages(
                packages=self.config.Valkey.Build.Dependencies,
                extra_cache_keys={"step": "deps", "packages": sorted(self.config.Valkey.Build.Dependencies)}
            )

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Downloading source from {self.config.Valkey.SourceUrl}")

            tar_path = f"/tmp/valkey-{self.config.Valkey.Version}.tar.gz"
            src_dir = f"/tmp/valkey-{self.config.Valkey.Version}"

            container.run_cached(
                command=[
                    "sh", "-c",
                    f"curl -L '{self.config.Valkey.SourceUrl}' -o {tar_path} && tar -xf {tar_path} -C /tmp"
                ],
                extra_cache_keys={"step": "source", "url": self.config.Valkey.SourceUrl, "src_dir": src_dir,
                                  "tar_path": tar_path}
            )

            current_step += 1
            self.log(f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Compiling and installing")
            make_flags = " ".join(self.config.Valkey.Build.Flags)
            container.run_cached(
                command=[
                    "sh", "-c",
                    f"""
                    cd {src_dir} && 
                    make -j$(nproc) {make_flags} &&
                    make install PREFIX={self.config.Valkey.Prefix}""",
                ],
                extra_cache_keys={"step": "compile", "version": self.config.Valkey.Version, "flags": sorted(self.config.Valkey.Build.Flags)}
            )

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Verifying installation.")

            try:
                container.run(["test", "-x", f"{self.config.Valkey.Prefix}/bin/valkey-server"])
                container.run([f"{self.config.Valkey.Prefix}/bin/valkey-server", "--version"])
                self.log("Verification successful.", style="bold green")
            except Exception:
                self.log("[bold red]Verification Failed[/bold red]: Valkey binary missing or corrupt.")
                raise

            current_step += 1
            self.log(
                f"[bold blue]Step {current_step}/{total_no_of_steps}[/bold blue]: Tagging image and adding metadata.")

            container.configure([
                ("--env",
                 f"PATH={self.config.Valkey.Prefix}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
                ("--label", f"org.valkey.version={self.config.Valkey.Version}"),
                ("--label", f"org.valkey.prefix={self.config.Valkey.Prefix}"),
            ])
            image_name_tag = self.image_name + ":" + self.image_tag
            container.commit(image_name_tag)

            self.log(f"Image tagged as: [green]{image_name_tag}[/green]")

    def prune_cache_images(self):
        prune_cache_images(self.config.Buildah.Path, self.cache_prefix)
