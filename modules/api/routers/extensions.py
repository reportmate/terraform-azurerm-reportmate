"""
Extension ingress & read API.

Extensions are the server-joined / add-on counterpart to the client-collected
core *modules* (inventory, system, hardware, …). They attach named JSONB data to
a device by serial from an external source (e.g. an Intune/Graph poller, a
security-vendor risk feed) — there is no device-local footprint a client could
collect. Data lives in the generic ``extension_data`` table, keyed by
(device_id, extension_name); no per-extension DDL.

Naming boundary: core device telemetry stays "modules" (dedicated tables,
device.modules). This router is *extensions only* and rejects any name that
collides with a core module — core data is ingested via /events, not here.

Auth: ``verify_authentication`` — the same data-plane gate as device ingestion
(fleet passphrase / internal secret / managed identity), not the control-plane
settings write.
"""
import json
import re
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from dependencies import verify_authentication, get_db_connection, VALID_MODULE_NAMES

logger = logging.getLogger(__name__)
router = APIRouter()

# Lowercase slug: letters/digits, then up to 63 of [a-z0-9_-]. Matches client ids.
_EXTENSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _validate_name(name: str) -> str:
    name = (name or "").strip().lower()
    if not _EXTENSION_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid extension name")
    if name in VALID_MODULE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"'{name}' is a core module — ingest core data via /events, not as an extension",
        )
    return name


def _parse_payload(body):
    """Accept {data, collectedAt, source} or a bare object as the payload."""
    if isinstance(body, dict) and "data" in body:
        return body.get("data"), body.get("collectedAt") or body.get("collected_at"), body.get("source")
    return body, None, None


def _upsert(cursor, serial: str, name: str, data, collected_at, source):
    now = datetime.now(timezone.utc)
    collected_at = collected_at or now.isoformat()
    cursor.execute(
        """
        INSERT INTO extension_data
            (device_id, extension_name, data, source, collected_at, created_at, updated_at)
        VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s)
        ON CONFLICT (device_id, extension_name) DO UPDATE
            SET data = EXCLUDED.data,
                source = EXCLUDED.source,
                collected_at = EXCLUDED.collected_at,
                updated_at = EXCLUDED.updated_at
        """,
        (serial, name, json.dumps(data), source, collected_at, now, now),
    )


# ─────────────────────────── per-device ───────────────────────────
@router.post("/device/{serial_number}/extension/{extension_name}",
             dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def upsert_device_extension(serial_number: str, extension_name: str, request: Request):
    """Attach one extension's data to a device.

    Body: ``{"data": {...}, "collectedAt": "<iso8601>", "source": "<id>"}``
    (a bare object is also accepted as the payload).
    """
    name = _validate_name(extension_name)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")
    data, collected_at, source = _parse_payload(body)
    if data is None:
        raise HTTPException(status_code=400, detail="Missing extension data")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM devices WHERE id = %s", (serial_number,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Device {serial_number} not found")
        _upsert(cursor, serial_number, name, data, collected_at, source)
        conn.commit()
        return {"success": True, "device": serial_number, "extension": name}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upsert extension {name} for {serial_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store extension data")
    finally:
        conn.close()


@router.get("/device/{serial_number}/extension/{extension_name}",
            dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def get_device_extension(serial_number: str, extension_name: str):
    """Read one extension's data for a device."""
    name = _validate_name(extension_name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data, source, collected_at, updated_at FROM extension_data "
            "WHERE device_id = %s AND extension_name = %s",
            (serial_number, name),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Extension data not found for device")
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return {"device": serial_number, "extension": name, "data": data,
                "source": row[1], "collectedAt": row[2], "updatedAt": row[3]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read extension {name} for {serial_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read extension data")
    finally:
        conn.close()


@router.delete("/device/{serial_number}/extension/{extension_name}",
               dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def delete_device_extension(serial_number: str, extension_name: str):
    """Remove one extension's data from a device (e.g. it fell out of scope)."""
    name = _validate_name(extension_name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM extension_data WHERE device_id = %s AND extension_name = %s",
            (serial_number, name),
        )
        deleted = cursor.rowcount
        conn.commit()
        return {"success": True, "device": serial_number, "extension": name, "deleted": deleted}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete extension {name} for {serial_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete extension data")
    finally:
        conn.close()


# ─────────────────────────── fleet / bulk ───────────────────────────
@router.post("/extension/{extension_name}/bulk",
             dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def bulk_upsert_extension(extension_name: str, request: Request):
    """Upsert an extension across many devices in one call — what a fleet poller
    (e.g. the Intune audit) uses after computing the whole fleet in one pass.

    Body: ``{"source": "<id>", "collectedAt": "<iso8601>",
             "devices": [{"serial": "ABC", "data": {...}}, ...]}``
    Returns counts and the serials that don't exist (skipped, not an error).
    """
    name = _validate_name(extension_name)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")
    if not isinstance(body, dict) or not isinstance(body.get("devices"), list):
        raise HTTPException(status_code=400, detail="Body must be {source?, collectedAt?, devices: [...]}")
    source = body.get("source")
    collected_at = body.get("collectedAt") or body.get("collected_at")
    entries = body["devices"]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM devices")
        known = {r[0] for r in cursor.fetchall()}
        written, unknown, bad = 0, [], 0
        for e in entries:
            serial = (e or {}).get("serial")
            data = (e or {}).get("data")
            if not serial or data is None:
                bad += 1
                continue
            if serial not in known:
                unknown.append(serial)
                continue
            _upsert(cursor, serial, name,
                    data, e.get("collectedAt") or collected_at, e.get("source") or source)
            written += 1
        conn.commit()
        return {"success": True, "extension": name, "written": written,
                "unknownSerials": unknown, "skippedBad": bad}
    except Exception as e:
        conn.rollback()
        logger.error(f"Bulk upsert failed for extension {name}: {e}")
        raise HTTPException(status_code=500, detail="Bulk upsert failed")
    finally:
        conn.close()


@router.get("/extension/{extension_name}",
            dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def get_extension_fleet(extension_name: str,
                              limit: int = Query(500, ge=1, le=5000),
                              offset: int = Query(0, ge=0)):
    """All devices' data for an extension — the source for fleet reports."""
    name = _validate_name(extension_name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM extension_data WHERE extension_name = %s", (name,))
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT device_id, data, source, collected_at, updated_at FROM extension_data "
            "WHERE extension_name = %s ORDER BY device_id LIMIT %s OFFSET %s",
            (name, limit, offset),
        )
        items = [{
            "device": r[0],
            "data": json.loads(r[1]) if isinstance(r[1], str) else r[1],
            "source": r[2], "collectedAt": r[3], "updatedAt": r[4],
        } for r in cursor.fetchall()]
        return {"extension": name, "total": total, "limit": limit, "offset": offset, "devices": items}
    except Exception as e:
        logger.error(f"Failed to read fleet for extension {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read extension fleet data")
    finally:
        conn.close()


@router.delete("/extension/{extension_name}",
               dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def purge_extension(extension_name: str):
    """Decommission an extension — remove all of its data fleet-wide."""
    name = _validate_name(extension_name)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM extension_data WHERE extension_name = %s", (name,))
        deleted = cursor.rowcount
        conn.commit()
        return {"success": True, "extension": name, "deleted": deleted}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to purge extension {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to purge extension")
    finally:
        conn.close()


# ─────────────────────────── registry ───────────────────────────
@router.get("/extensions", dependencies=[Depends(verify_authentication)], tags=["extensions"])
async def list_extensions():
    """List extensions present in storage: name, device count, last update, sources."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT extension_name,
                   COUNT(DISTINCT device_id),
                   MAX(collected_at),
                   ARRAY_AGG(DISTINCT source)
            FROM extension_data
            GROUP BY extension_name
            ORDER BY extension_name
            """
        )
        return {"extensions": [{
            "name": r[0],
            "deviceCount": r[1],
            "lastCollectedAt": r[2],
            "sources": [s for s in (r[3] or []) if s],
        } for r in cursor.fetchall()]}
    except Exception as e:
        logger.error(f"Failed to list extensions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list extensions")
    finally:
        conn.close()
