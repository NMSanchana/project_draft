"""The strict query-plan schema. A plan is *data*, never code: it is validated and then run by a
whitelisted pandas executor. Anything outside this schema is rejected."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Metric = Literal["revenue", "cost", "profit", "quantity", "orders", "customers", "aov", "margin_pct", "avg_price"]
GroupBy = Literal["category", "region", "product", "customer", "status", "month", "week", "day", "weekday"]
FilterColumn = Literal["category", "region", "product", "customer", "status"]
Operation = Literal["total", "group", "trend", "compare"]

METRIC_LABEL = {
    "revenue": "revenue",
    "cost": "total cost",
    "profit": "profit",
    "quantity": "units sold",
    "orders": "orders",
    "customers": "unique customers",
    "aov": "average order value",
    "margin_pct": "profit margin",
    "avg_price": "average price per unit",
}
METRIC_KIND = {
    "revenue": "money",
    "cost": "money",
    "profit": "money",
    "aov": "money",
    "avg_price": "money",
    "quantity": "count",
    "orders": "count",
    "customers": "count",
    "margin_pct": "pct",
}


class Filter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: FilterColumn
    value: str = Field(min_length=1, max_length=80)


class TimeRange(BaseModel):
    """One of: ``month`` (YYYY-MM), ``quarter`` (YYYY-Qn), ``year`` (YYYY), ``last_days`` (relative to the
    data's last date), or an explicit ``start``/``end`` (YYYY-MM-DD)."""

    model_config = ConfigDict(extra="forbid")
    month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    quarter: str | None = Field(default=None, pattern=r"^\d{4}-Q[1-4]$")
    year: int | None = Field(default=None, ge=1990, le=2100)
    last_days: int | None = Field(default=None, ge=1, le=3650)
    start: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("*", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        return None if v in ("", "null") else v

    def is_empty(self) -> bool:
        return not any(v is not None for v in self.model_dump().values())


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Operation = "total"
    metric: Metric = "revenue"
    group_by: GroupBy | None = None
    filters: list[Filter] = Field(default_factory=list, max_length=4)
    time_range: TimeRange | None = None
    compare_range: TimeRange | None = None  # only for operation == "compare"
    top_n: int = Field(default=5, ge=1, le=50)
    sort: Literal["asc", "desc"] = "desc"
