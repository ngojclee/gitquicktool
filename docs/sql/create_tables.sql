-- ============================================================
-- GitQuickTool — Supabase Schema
-- Run this SQL in Supabase SQL Editor to create all tables
-- ============================================================

-- ── Tokens ──────────────────────────────────────────────────
-- Stores GitHub PATs with labels for easy identification
CREATE TABLE IF NOT EXISTS "LuxeClaw_gitquicktool_tokens" (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label       TEXT NOT NULL,
    token       TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE "LuxeClaw_gitquicktool_tokens" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Full Access for Auth and Service"
    ON "LuxeClaw_gitquicktool_tokens"
    FOR ALL
    TO authenticated, service_role
    USING (true)
    WITH CHECK (true);

-- ── Items ───────────────────────────────────────────────────
-- Stores repo/release items to clone or download
CREATE TABLE IF NOT EXISTS "LuxeClaw_gitquicktool_items" (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    type            TEXT NOT NULL CHECK (type IN ('repo', 'release')),
    url             TEXT NOT NULL,
    asset_pattern   TEXT DEFAULT '',
    token_id        UUID REFERENCES "LuxeClaw_gitquicktool_tokens"(id) ON DELETE SET NULL,
    subfolder       TEXT DEFAULT '',
    enabled         BOOLEAN DEFAULT true,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE "LuxeClaw_gitquicktool_items" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Full Access for Auth and Service"
    ON "LuxeClaw_gitquicktool_items"
    FOR ALL
    TO authenticated, service_role
    USING (true)
    WITH CHECK (true);

-- ── Settings ────────────────────────────────────────────────
-- Key-value store for app settings (download_path, etc.)
CREATE TABLE IF NOT EXISTS "LuxeClaw_gitquicktool_settings" (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT UNIQUE NOT NULL,
    value       TEXT DEFAULT '',
    updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE "LuxeClaw_gitquicktool_settings" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Full Access for Auth and Service"
    ON "LuxeClaw_gitquicktool_settings"
    FOR ALL
    TO authenticated, service_role
    USING (true)
    WITH CHECK (true);

-- ── Auto-update updated_at ──────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tokens_updated
    BEFORE UPDATE ON "LuxeClaw_gitquicktool_tokens"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_items_updated
    BEFORE UPDATE ON "LuxeClaw_gitquicktool_items"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_settings_updated
    BEFORE UPDATE ON "LuxeClaw_gitquicktool_settings"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
