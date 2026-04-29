-- ═══════════════════════════════════════════════════════════════
-- Forge3D – PostgreSQL Database Schema
-- Run this in your Supabase SQL editor to set up the tables.
-- ═══════════════════════════════════════════════════════════════

-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── users ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ── projects ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects (user_id);

-- ── assets ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assets (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_url   TEXT         NOT NULL,
    filename   VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_project_id ON assets (project_id);

-- ── Row Level Security (optional – recommended for Supabase) ─────
-- These policies allow full access only through your backend service key.
-- If you use the anon key in the frontend, tighten these accordingly.

ALTER TABLE users    ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets   ENABLE ROW LEVEL SECURITY;
