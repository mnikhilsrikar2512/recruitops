"""Stage bucket map (Phase 4.5): which metric bucket each stage label counts in."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

MetricBucket = Literal["sourced", "screened", "submitted", "interview", "offer", "joined", "rejected", "withdrawn"]


class MetricBucketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    sort_order: int
    is_terminal: bool


class StageBucketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage_key: str
    example_label: str | None
    metric_bucket: str
    source: Literal["company", "platform", "inferred"]
    platform_bucket: str | None
    applications: int


class StageBucketMapResponse(BaseModel):
    buckets: list[MetricBucketResponse]
    stages: list[StageBucketResponse]


class StageBucketUpdate(BaseModel):
    metric_bucket: MetricBucket
