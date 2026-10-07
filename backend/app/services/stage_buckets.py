"""Stage Bucket Map (Phase 4.5): admins see how every stage label their
company uses is counted in reports, and can re-map a label for their
company. A change applies to reports at once (current stages) and to new
history rows; history already written keeps the bucket it was snapshotted
with, so past reports do not silently change."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.audit import insert_audit_log
from app.repositories.stage_buckets import (
    delete_tenant_mapping,
    find_tenant_mapping,
    list_metric_buckets,
    list_stage_buckets,
    resolve_bucket,
    stage_key,
    upsert_tenant_mapping,
)
from app.schemas.stage_buckets import (
    MetricBucketResponse,
    StageBucketMapResponse,
    StageBucketResponse,
    StageBucketUpdate,
)
from app.services import scope
from app.services.auth import AuthContext


def _normalised_key(raw: str) -> str:
    key = stage_key(raw or "")
    if not key or len(key) > 50:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Stage label must be 1 to 50 characters")
    return key


def _require_tenant(auth_context: AuthContext) -> int:
    tenant_id = scope.tenant_id_of(auth_context)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stage mappings belong to a company; sign in as a company user")
    return int(tenant_id)


def get_stage_bucket_map_service(engine: Engine, auth_context: AuthContext) -> StageBucketMapResponse:
    tenant_id = scope.tenant_id_of(auth_context)
    return StageBucketMapResponse(
        buckets=[MetricBucketResponse.model_validate(b) for b in list_metric_buckets(engine)],
        stages=[StageBucketResponse.model_validate(s) for s in list_stage_buckets(engine, tenant_id)],
    )


def set_stage_bucket_service(
    engine: Engine, raw_stage: str, payload: StageBucketUpdate, auth_context: AuthContext
) -> StageBucketResponse:
    tenant_id = _require_tenant(auth_context)
    key = _normalised_key(raw_stage)
    before = resolve_bucket(engine, tenant_id, key)
    previous_override = find_tenant_mapping(engine, tenant_id, key)
    upsert_tenant_mapping(engine, tenant_id, key, payload.metric_bucket, auth_context.user.id)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="stage_bucket_map",
        entity_id=tenant_id,
        action_type="stage_bucket.set",
        old_values={"stage_key": key, "metric_bucket": before, "company_override": previous_override},
        new_values={"stage_key": key, "metric_bucket": payload.metric_bucket},
    )
    return _one(engine, tenant_id, key)


def reset_stage_bucket_service(engine: Engine, raw_stage: str, auth_context: AuthContext) -> StageBucketResponse:
    tenant_id = _require_tenant(auth_context)
    key = _normalised_key(raw_stage)
    previous_override = find_tenant_mapping(engine, tenant_id, key)
    if previous_override is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This stage has no company mapping to reset")
    delete_tenant_mapping(engine, tenant_id, key)
    insert_audit_log(
        engine,
        actor_user_id=auth_context.user.id,
        location_id=auth_context.user.location_id,
        entity_type="stage_bucket_map",
        entity_id=tenant_id,
        action_type="stage_bucket.reset",
        old_values={"stage_key": key, "metric_bucket": previous_override},
        new_values={"stage_key": key, "metric_bucket": resolve_bucket(engine, tenant_id, key)},
    )
    return _one(engine, tenant_id, key)


def _one(engine: Engine, tenant_id: int, key: str) -> StageBucketResponse:
    for record in list_stage_buckets(engine, tenant_id):
        if record.stage_key == key:
            return StageBucketResponse.model_validate(record)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage was not found")
