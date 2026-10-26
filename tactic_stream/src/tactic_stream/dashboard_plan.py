"""Portable dashboard bricks shared by agent schemas and native server commands."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DashboardFilter(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    column: str = Field(min_length=1, max_length=128)
    relation: Literal['=', '!=', '<', '<=', '>', '>=', 'like'] = '='
    value: str | int | float | bool | None


class DashboardTreeNode(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    search_type: str = Field(min_length=1, max_length=256)
    title: str = Field(default='', max_length=256)
    title_field: str = Field(default='', max_length=128)
    path: str = Field(default='', max_length=256)
    filters: list[DashboardFilter] = Field(default_factory=list, max_length=32)
    branches: list['DashboardTreeNode'] = Field(default_factory=list, max_length=16)


class DashboardBlock(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['row', 'column', 'text', 'markdown', 'metric', 'table', 'tree', 'link']
    title: str = Field(default='', max_length=256)
    text: str = Field(default='', max_length=65536)
    source_key: str = Field(default='', max_length=2048)
    field: str = Field(default='', max_length=128)
    search_type: str = Field(default='', max_length=256)
    view: str = Field(default='table', pattern=r'^[A-Za-z_][\w.@-]{0,127}$')
    filters: list[DashboardFilter] = Field(default_factory=list, max_length=32)
    href: str = Field(default='', max_length=2048)
    weight: int = Field(default=1, ge=1, le=12)
    height: int | None = Field(default=None, ge=120, le=1600)
    controls: list[Literal['search', 'searchLimit', 'shelf', 'selection', 'gear', 'insert']] | None = Field(default=None, max_length=6)
    tree: DashboardTreeNode | None = None
    children: list['DashboardBlock'] = Field(default_factory=list, max_length=32)


class DashboardDocument(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    blocks: list[DashboardBlock] = Field(min_length=1, max_length=32)
