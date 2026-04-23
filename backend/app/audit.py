"""Audit log helper.

不可竄改的安全稽核紀錄。`log()` 會在當前 request 的 session 中暫存，
由 view function 的主要 commit 一起寫入；若寫入失敗也不應阻斷原請求。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import g, has_request_context, request

from .extensions import db
from .models import AuditLog

_logger = logging.getLogger(__name__)


def _safe_meta(meta: dict | None) -> str | None:
    if not meta:
        return None
    try:
        return json.dumps(meta, ensure_ascii=False, default=str)
    except Exception:
        return None


def log(
    action: str,
    *,
    actor=None,
    actor_username: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    meta: dict | None = None,
    commit: bool = True,
) -> None:
    """寫入一筆稽核紀錄。

    - actor: 通常是 current_user() 的結果
    - commit=False 時由呼叫方控制 commit（如跟業務寫入一起）
    """
    try:
        actor_id = None
        if actor is not None:
            actor_id = actor.id
            actor_username = actor_username or actor.username

        ip = None
        ua = None
        if has_request_context():
            ip = request.remote_addr
            ua = (request.headers.get("User-Agent") or "")[:255]

        entry = AuditLog(
            actor_id=actor_id,
            actor_username=actor_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            meta_json=_safe_meta(meta),
            ip=ip,
            user_agent=ua,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
    except Exception as e:  # 稽核失敗絕不阻斷主流程
        _logger.warning("audit log failed: action=%s err=%s", action, e)
        try:
            db.session.rollback()
        except Exception:
            pass
