from enum import StrEnum

from pydantic import BaseModel, Field

from .valkey import ValkeyConfig
from .valkey_bloom import ValkeyBloomConfig
from .valkey_json import ValkeyJsonConfig
from .valkey_search import ValkeySearchConfig


class BuildahConfig(BaseModel):
    Path: str = 'buildah'

class Distro(StrEnum):
    SUSE = "suse"

class BuildSpec(BaseModel):
    ProjectName: str
    BaseImage: str
    Distro: Distro
    Buildah: BuildahConfig = Field(default_factory=BuildahConfig)
    Valkey: ValkeyConfig = Field(default_factory=ValkeyConfig)
    ValkeyJson: ValkeyJsonConfig = Field(default_factory=ValkeyJsonConfig)
    ValkeySearch: ValkeySearchConfig = Field(default_factory=ValkeySearchConfig)
    ValkeyBloom: ValkeyBloomConfig = Field(default_factory=ValkeyBloomConfig)
