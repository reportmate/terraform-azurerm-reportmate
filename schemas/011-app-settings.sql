-- Migration 011: server-side application settings store
--
-- Holds org-scoped (and, in future, user-scoped) configuration as a single
-- JSONB document per (scope, principal). This is what makes inventory field
-- mapping and the usage-aware security rules engine configurable, and is the
-- contract the web app and future native Swift/C# apps all read from.
--
-- Idempotent: also created on API startup in main.py (ensure_performance_indexes)
-- so running containers self-provision without a manual migration step.

CREATE TABLE IF NOT EXISTS app_settings (
    id             BIGSERIAL PRIMARY KEY,
    scope          TEXT NOT NULL DEFAULT 'org',          -- 'org' | 'user'
    principal      TEXT NOT NULL DEFAULT '',             -- '' for org; user/tenant id for user scope
    value          JSONB NOT NULL DEFAULT '{}'::jsonb,   -- the full settings document
    schema_version INTEGER NOT NULL DEFAULT 1,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by     TEXT,                                 -- email/principal that last wrote it (audit)
    UNIQUE (scope, principal)
);

COMMENT ON TABLE app_settings IS 'Org/user scoped settings documents (JSONB). One row per (scope, principal).';
