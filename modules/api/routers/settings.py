"""Server-side application settings.

Org-scoped configuration stored as a single JSONB document. This is the source
of truth for inventory field mapping and the usage-aware security rules engine,
shared by the web app and (in future) the native Swift/C# apps.

Role enforcement for writes happens upstream in the Next.js proxy layer (the
FastAPI tier has no per-user identity); the PUT here trusts the internal secret.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from dependencies import (
    cache_get, cache_set, get_db_connection, invalidate_caches, load_sql,
    logger, verify_authentication,
)

router = APIRouter(tags=["settings"])

# Current document schema version. Bump when the document shape changes in a way
# that older readers (including native apps) need to detect and migrate.
CURRENT_SCHEMA_VERSION = 1

_ORG_SCOPE = "org"
_ORG_PRINCIPAL = ""
_CACHE_NS = "settings"


# ── Validation models (permissive: unknown keys are preserved) ──────────────
# The store is JSONB and the document is meant to evolve, so we validate shape
# loosely and keep extra fields rather than rejecting forward-compatible docs.

class _Lenient(BaseModel):
    model_config = ConfigDict(extra="allow")


class InventoryField(_Lenient):
    key: str
    sourceKey: Optional[str] = None
    label: Optional[str] = None
    order: Optional[int] = None
    visible: Optional[bool] = True
    knownValues: Optional[List[str]] = None


class SecurityRule(_Lenient):
    id: str
    check: str
    state: Optional[str] = "any"          # 'enabled' | 'disabled' | 'any'
    severity: str                          # 'ok' | 'warning' | 'danger' | 'neutral'
    enabled: Optional[bool] = True
    when: Optional[Dict[str, Any]] = None


class SettingsDocument(_Lenient):
    schemaVersion: Optional[int] = CURRENT_SCHEMA_VERSION
    general: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None


_VALID_SEVERITIES = {"ok", "warning", "danger", "neutral", "unknown"}


def _validate_document(doc: Any) -> SettingsDocument:
    """Validate enough of the document to catch obvious corruption without
    rejecting forward-compatible additions."""
    if not isinstance(doc, dict):
        raise HTTPException(status_code=422, detail="Settings document must be a JSON object")
    try:
        parsed = SettingsDocument(**doc)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid settings document: {e}")

    # Spot-check the security rules' severities (the part the UI colors on).
    rules = (parsed.security or {}).get("rules") if parsed.security else None
    if isinstance(rules, list):
        for r in rules:
            sev = r.get("severity") if isinstance(r, dict) else None
            if sev is not None and sev not in _VALID_SEVERITIES:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid rule severity '{sev}'. Allowed: {sorted(_VALID_SEVERITIES)}",
                )
    return parsed


@router.get("/settings", dependencies=[Depends(verify_authentication)], tags=["settings"])
async def get_settings():
    """Return the org-scoped settings document.

    When no document exists yet, returns ``{"exists": false, "value": null}`` so
    the client can trigger first-time onboarding.
    """
    cached = cache_get(_CACHE_NS, (_ORG_SCOPE, _ORG_PRINCIPAL))
    if cached is not None:
        return cached

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            load_sql("settings/get"),
            {"scope": _ORG_SCOPE, "principal": _ORG_PRINCIPAL},
        )
        row = cursor.fetchone()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")

    if not row:
        result = {
            "exists": False,
            "value": None,
            "schemaVersion": CURRENT_SCHEMA_VERSION,
        }
    else:
        value, schema_version, updated_at, updated_by = row
        result = {
            "exists": True,
            "value": value,
            "schemaVersion": schema_version,
            "updatedAt": updated_at.isoformat() if updated_at else None,
            "updatedBy": updated_by,
        }

    cache_set(_CACHE_NS, result, (_ORG_SCOPE, _ORG_PRINCIPAL))
    return result


@router.put("/settings", dependencies=[Depends(verify_authentication)], tags=["settings"])
async def put_settings(
    request: Request,
    x_updated_by: Optional[str] = Header(None, alias="X-Updated-By"),
):
    """Replace the org-scoped settings document.

    Writes are gated by an admin role check in the Next.js proxy before reaching
    this endpoint; the API trusts the internal secret.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    parsed = _validate_document(body)
    schema_version = parsed.schemaVersion or CURRENT_SCHEMA_VERSION

    # Persist the (validated) document as-is, preserving any extra fields.
    document = parsed.model_dump(exclude_none=False)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            load_sql("settings/upsert"),
            {
                "scope": _ORG_SCOPE,
                "principal": _ORG_PRINCIPAL,
                "value": json.dumps(document),
                "schema_version": schema_version,
                "updated_by": x_updated_by,
            },
        )
        row = cursor.fetchone()
        conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

    invalidate_caches()

    value, saved_version, updated_at, updated_by = row
    logger.info(f"[SETTINGS] org settings updated by {updated_by or 'unknown'}")
    return {
        "exists": True,
        "value": value,
        "schemaVersion": saved_version,
        "updatedAt": updated_at.isoformat() if updated_at else None,
        "updatedBy": updated_by,
    }


@router.get("/settings/inventory/discover", dependencies=[Depends(verify_authentication)], tags=["settings"])
async def discover_inventory_keys(
    include_archived: bool = Query(default=False, description="Include archived devices in discovery"),
):
    """Discover the inventory keys present across the fleet, with sample values.

    Powers the onboarding wizard's field-mapping step so admins can map whatever
    keys their Inventory.yaml emits to ReportMate's canonical fields.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            load_sql("settings/inventory_discover"),
            {"include_archived": include_archived},
        )
        rows = cursor.fetchall()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inventory discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Inventory discovery failed: {str(e)}")

    keys = []
    for key, device_count, distinct_count, sample_values in rows:
        keys.append({
            "key": key,
            "deviceCount": device_count,
            "distinctCount": distinct_count,
            "sampleValues": list(sample_values) if sample_values else [],
        })

    return {
        "keys": keys,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
