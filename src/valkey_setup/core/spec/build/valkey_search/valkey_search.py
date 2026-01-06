from typing import List, Dict

from pydantic import BaseModel, Field


class BuildConfig(BaseModel):
    Dependencies: List[str] = Field(default_factory=list)
    Flags: List[str] = Field(default_factory=list)
    Env: List[str] = Field(default_factory=list)
    Cpu: int = 4


class RuntimeConfig(BaseModel):
    Dependencies: List[str] = Field(default_factory=list)


class ValkeySearchVersion(BaseModel):
    SourceUrl: str
    Build: BuildConfig = Field(default_factory=BuildConfig)
    Runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)


class ValkeySearchConfig(BaseModel):
    Current: str
    Versions: Dict[str, ValkeySearchVersion] = Field(default_factory=list)
