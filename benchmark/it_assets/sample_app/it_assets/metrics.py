"""Métricas de movimentação de ativos de TI (lógica do dashboard, testável isoladamente)."""

from __future__ import annotations

import sqlite3


def dashboard_metrics(con: sqlite3.Connection) -> dict:
    """Agregados úteis de movimentação, robustos a valores nulos."""
    total = con.execute("SELECT COUNT(*) AS n FROM movements").fetchone()["n"]
    by_action = {
        r["action"]: r["n"]
        for r in con.execute(
            "SELECT action, COUNT(*) AS n FROM movements GROUP BY action ORDER BY action"
        )
    }
    by_type = {
        (r["asset_type"] or "(desconhecido)"): r["n"]
        for r in con.execute(
            "SELECT asset_type, COUNT(*) AS n FROM movements GROUP BY asset_type"
        )
    }
    by_status = {
        (r["status"] or "(desconhecido)"): r["n"]
        for r in con.execute(
            "SELECT status, COUNT(*) AS n FROM movements GROUP BY status"
        )
    }
    distinct_assets = con.execute(
        "SELECT COUNT(DISTINCT asset_tag) AS n FROM movements"
    ).fetchone()["n"]
    total_value = con.execute(
        "SELECT COALESCE(SUM(value), 0) AS v FROM movements WHERE value IS NOT NULL"
    ).fetchone()["v"]
    return {
        "total_movements": total,
        "distinct_assets": distinct_assets,
        "by_action": by_action,
        "by_type": by_type,
        "by_status": by_status,
        "total_value": round(float(total_value or 0), 2),
    }


def list_assets(con: sqlite3.Connection) -> list[dict]:
    """Visão por ativo: tipo, última ação/local/status e nº de movimentações."""
    rows = con.execute(
        """
        SELECT asset_tag,
               MAX(asset_type) AS asset_type,
               COUNT(*) AS movements
        FROM movements
        GROUP BY asset_tag
        ORDER BY asset_tag
        """
    ).fetchall()
    out = []
    for r in rows:
        last = con.execute(
            """SELECT action, to_location, status FROM movements
               WHERE asset_tag = ? ORDER BY date DESC, id DESC LIMIT 1""",
            (r["asset_tag"],),
        ).fetchone()
        out.append(
            {
                "asset_tag": r["asset_tag"],
                "asset_type": r["asset_type"],
                "movements": r["movements"],
                "last_action": last["action"] if last else None,
                "location": last["to_location"] if last else None,
                "status": last["status"] if last else None,
            }
        )
    return out
