from typing import List, Dict

from pydantic import BaseModel, Field


class BuildConfig(BaseModel):
    Dependencies: List[str] = Field(default_factory=list)
    Flags: List[str] = Field(default_factory=list)
    Env: List[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    Dependencies: List[str] = Field(default_factory=list)


class ValkeyJsonVersion(BaseModel):
    SourceUrl: str
    Build: BuildConfig = Field(default_factory=BuildConfig)
    Runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)


class ValkeyJsonConfig(BaseModel):
    Current: str
    Versions: Dict[str, ValkeyJsonVersion] = Field(default_factory=list)
