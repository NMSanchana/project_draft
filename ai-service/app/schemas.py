"""Pydantic models mirroring ``frontend/src/lib/analytics.ts`` (``ProcessedAnalytics`` and friends).

Field names are camelCase on purpose: they are the frontend contract and must not change.
Extra optional fields (``datasetId``, ``status``, ``quality``, ``ml``) are additive.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TrendBarItem(BaseModel):
    name: str
    heightPercent: str
    value: str
    numericValue: float
    color: str
    defaultActive: bool | None = None


class RuleInsight(BaseModel):
    id: str | int
    title: str
    desc: str
    type: Literal["growth", "alert", "opportunity", "info"]
    severity: Literal["High", "Medium", "Low", "Info"]
    recommendation: str = ""


class IngestionActivity(BaseModel):
    id: str
    task: str
    fileName: str
    date: str
    accuracy: str
    duration: str
    status: Literal["Completed", "Ready", "Processing"]
    recordsCount: int


class ProcessedAnalytics(BaseModel):
    # --- existing frontend contract (unchanged) ---
    fileName: str
    recordsCount: int
    revenue: float
    totalCost: float
    totalProfit: float
    profitMargin: float
    orders: int
    uniqueCustomers: int
    trendData: list[TrendBarItem]
    trendSummary: str
    trendBadge: str
    insights: list[RuleInsight]
    activities: list[IngestionActivity]
    # --- additive optional extras ---
    datasetId: str | None = None
    status: Literal["enriching", "ready", "failed"] | None = None
    stage: str | None = None
    quality: dict[str, Any] | None = None
    kpis: dict[str, Any] | None = None
    ml: dict[str, Any] | None = None


class DatasetSummary(BaseModel):
    datasetId: str
    fileName: str
    status: str
    rows: int
    createdAt: str


class ErrorBody(BaseModel):
    success: bool = Field(False)
    message: str
    code: str
