"""PostgreSQL database initialisation via asyncpg. Call init_db() at app startup."""
import asyncpg

from ..config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_db() first.")
    return _pool


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=10)

    async with _pool.acquire() as conn:
        # ── jobs ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id       TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                progress     INTEGER NOT NULL DEFAULT 0,
                message      TEXT NOT NULL DEFAULT '',
                error        TEXT,
                report_json  TEXT,
                pdf_bytes    BYTEA,
                md_content   TEXT,
                ppt_prompt   TEXT,
                user_id      TEXT,
                share_token  TEXT,
                is_public    BOOLEAN NOT NULL DEFAULT FALSE,
                created_at   TEXT NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_share ON jobs(share_token)"
        )

        # ── users ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              TEXT PRIMARY KEY,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                name            TEXT NOT NULL DEFAULT '',
                plan            TEXT NOT NULL DEFAULT 'free',
                plan_expires_at TEXT,
                referral_code   TEXT UNIQUE,
                referred_by     TEXT,
                created_at      TEXT NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_refcode ON users(referral_code)"
        )

        # ── redemption_codes ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS redemption_codes (
                code          TEXT PRIMARY KEY,
                plan          TEXT NOT NULL,
                duration_days INTEGER NOT NULL DEFAULT 0,
                note          TEXT NOT NULL DEFAULT '',
                used_by       TEXT,
                used_at       TEXT,
                created_at    TEXT NOT NULL
            )
        """)

        # ── usage_events ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id         BIGSERIAL PRIMARY KEY,
                user_id    TEXT NOT NULL,
                action     TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_user_action "
            "ON usage_events(user_id, action, created_at)"
        )

        # ── applications (job tracker) ──
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id             TEXT PRIMARY KEY,
                user_id        TEXT NOT NULL,
                company        TEXT NOT NULL,
                role           TEXT NOT NULL DEFAULT '',
                status         TEXT NOT NULL DEFAULT 'saved',
                notes          TEXT NOT NULL DEFAULT '',
                job_id         TEXT,
                next_action_at TEXT,
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_apps_user "
            "ON applications(user_id, updated_at DESC)"
        )
