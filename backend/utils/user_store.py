"""Async PostgreSQL user, usage, redemption-code, and application stores."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..config import PLAN_FREE, PLAN_LIFETIME
from .db import get_pool

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_code(prefix: str = "") -> str:
    body = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))
    chunked = f"{body[:5]}-{body[5:]}"
    return f"{prefix}{chunked}" if prefix else chunked


# ════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════
async def create_user(email: str, password_hash: str, name: str = "",
                      referred_by: Optional[str] = None) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    ref_code = _gen_code()
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO users (id, email, password_hash, name, plan, referral_code, referred_by, created_at) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
        user_id, email.lower().strip(), password_hash, name.strip(),
        PLAN_FREE, ref_code, referred_by, _now(),
    )
    return await get_user_by_id(user_id)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE email = $1", email.lower().strip()
    )
    return dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return dict(row) if row else None


async def get_user_by_referral_code(code: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE referral_code = $1", code.strip()
    )
    return dict(row) if row else None


async def set_user_plan(user_id: str, plan: str, duration_days: int = 0) -> None:
    expires: Optional[str] = None
    if plan != PLAN_LIFETIME and duration_days > 0:
        expires = (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat()
    pool = await get_pool()
    await pool.execute(
        "UPDATE users SET plan = $1, plan_expires_at = $2 WHERE id = $3",
        plan, expires, user_id,
    )


def effective_plan(user: Dict[str, Any]) -> str:
    plan = user.get("plan", PLAN_FREE)
    if plan in (PLAN_FREE, PLAN_LIFETIME):
        return plan
    expires = user.get("plan_expires_at")
    if not expires:
        return plan
    try:
        exp = datetime.fromisoformat(expires)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return PLAN_FREE
    except ValueError:
        pass
    return plan


# ════════════════════════════════════════════
#  USAGE
# ════════════════════════════════════════════
async def record_usage(user_id: str, action: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO usage_events (user_id, action, created_at) VALUES ($1,$2,$3)",
        user_id, action, _now(),
    )


async def count_usage_this_month(user_id: str, action: str) -> int:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT COUNT(*) FROM usage_events "
        "WHERE user_id = $1 AND action = $2 AND created_at >= $3",
        user_id, action, month_start,
    )
    return row[0] if row else 0


async def usage_summary(user_id: str) -> Dict[str, int]:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT action, COUNT(*) FROM usage_events "
        "WHERE user_id = $1 AND created_at >= $2 GROUP BY action",
        user_id, month_start,
    )
    return {r["action"]: r["count"] for r in rows}


# ════════════════════════════════════════════
#  REDEMPTION CODES
# ════════════════════════════════════════════
async def create_codes(plan: str, duration_days: int, count: int, note: str = "") -> List[str]:
    codes: List[str] = []
    pool = await get_pool()
    for _ in range(count):
        code = _gen_code(prefix="IQ-")
        await pool.execute(
            "INSERT INTO redemption_codes (code, plan, duration_days, note, created_at) "
            "VALUES ($1,$2,$3,$4,$5)",
            code, plan, duration_days, note, _now(),
        )
        codes.append(code)
    return codes


async def redeem_code(code: str, user_id: str) -> Dict[str, Any]:
    code = code.strip().upper()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT * FROM redemption_codes WHERE code = $1", code
            )
            if row is None:
                return {"ok": False, "message": "Invalid code."}
            if row["used_by"]:
                return {"ok": False, "message": "This code has already been used."}
            await conn.execute(
                "UPDATE redemption_codes SET used_by = $1, used_at = $2 WHERE code = $3",
                user_id, _now(), code,
            )

    await set_user_plan(user_id, row["plan"], row["duration_days"])
    return {"ok": True, "plan": row["plan"], "message": f"Upgraded to {row['plan'].title()}!"}


# ════════════════════════════════════════════
#  APPLICATIONS (job tracker)
# ════════════════════════════════════════════
async def add_application(user_id: str, company: str, role: str = "",
                          status: str = "saved", notes: str = "",
                          job_id: Optional[str] = None) -> Dict[str, Any]:
    app_id = str(uuid.uuid4())
    now = _now()
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO applications "
        "(id, user_id, company, role, status, notes, job_id, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
        app_id, user_id, company.strip(), role.strip(), status, notes.strip(), job_id, now, now,
    )
    return await get_application(app_id)


async def get_application(app_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM applications WHERE id = $1", app_id)
    return dict(row) if row else None


async def list_applications(user_id: str) -> List[Dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM applications WHERE user_id = $1 ORDER BY updated_at DESC", user_id
    )
    return [dict(r) for r in rows]


async def update_application(app_id: str, user_id: str, **fields: Any) -> bool:
    allowed = {"company", "role", "status", "notes", "next_action_at"}
    cols = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not cols:
        return False
    cols["updated_at"] = _now()

    col_names = list(cols.keys())
    set_sql = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(col_names))
    vals = [cols[k] for k in col_names]
    n = len(col_names)
    vals.append(app_id)
    vals.append(user_id)

    pool = await get_pool()
    result = await pool.execute(
        f"UPDATE applications SET {set_sql} WHERE id = ${n + 1} AND user_id = ${n + 2}",
        *vals,
    )
    return int(result.split()[-1]) > 0


async def delete_application(app_id: str, user_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM applications WHERE id = $1 AND user_id = $2", app_id, user_id
    )
    return int(result.split()[-1]) > 0
