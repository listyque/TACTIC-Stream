"""Portable dashboard bricks shared by agent schemas and native server commands."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class DashboardFilter(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    column: str = Field(min_length=1, max_length=128)
    relation: Literal['=', '!=', '<', '<=', '>', '>=', 'like'] = '='
    value: str | int | float | bool | None


class DashboardPageFilter(DashboardFilter):
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    search_type: str = Field(min_length=1, max_length=256)
    enabled: bool = False


class DashboardFilterValue(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool
    value: str | int | float | bool | None


class DashboardGrouping(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    column: str = Field(min_length=1, max_length=128)
    title: str = Field(default='', max_length=256)
    period: Literal['value', 'year', 'month', 'day'] = 'value'


class DashboardAggregate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    function: Literal['count', 'sum', 'avg', 'min', 'max'] = 'count'
    column: str = Field(default='', max_length=128)


class DashboardBlock(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['row', 'column', 'text', 'markdown', 'metric', 'table', 'items', 'details', 'link', 'chart', 'summary']
    title: str = Field(default='', max_length=256)
    text: str = Field(default='', max_length=65536)
    source_key: str = Field(default='', max_length=2048)
    field: str = Field(default='', max_length=128)
    binding: Literal['auto', 'static', 'project', 'selection', 'record'] = 'auto'
    search_type: str = Field(default='', max_length=256)
    view: str = Field(default='table', pattern=r'^[A-Za-z_][\w.@-]{0,127}$')
    filters: list[DashboardFilter] = Field(default_factory=list, max_length=32)
    page_filters: dict[str, str] | None = Field(default=None, max_length=8)
    group_by: list[DashboardGrouping] = Field(default_factory=list, max_length=3)
    aggregates: list[DashboardAggregate] = Field(default_factory=list, max_length=8)
    measure: str = Field(default='', max_length=48)
    group_limit: int = Field(default=50, ge=1, le=100)
    group_order: Literal['group', 'value_asc', 'value_desc'] = 'group'
    href: str = Field(default='', max_length=2048)
    weight: int = Field(default=1, ge=1, le=12)
    width: int | None = Field(default=None, ge=40, le=2400)
    height: int | None = Field(default=None, ge=24, le=1600)
    padding: list[Annotated[int, Field(ge=0, le=256)]] = Field(default_factory=lambda: [0, 0, 0, 0], min_length=4, max_length=4)
    margin: list[Annotated[int, Field(ge=0, le=256)]] = Field(default_factory=lambda: [0, 0, 0, 0], min_length=4, max_length=4)
    gap: int = Field(default=8, ge=0, le=128)
    controls: list[Literal['search', 'searchLimit', 'shelf', 'selection', 'gear', 'insert']] | None = Field(default=None, max_length=6)
    children: list['DashboardBlock'] = Field(default_factory=list, max_length=32)


class DashboardDocument(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    title: str = Field(min_length=1, max_length=256)
    filters: list[DashboardPageFilter] = Field(default_factory=list, max_length=8)
    blocks: list[DashboardBlock] = Field(min_length=0, max_length=32)
