#!/usr/bin/env python3
"""
ProcureLocal - Python Developer SDK (ProcureSDK)
------------------------------------------------
A clean, pythonic SDK for integrating ProcureLocal into external ERPs,
data pipelines, ETL jobs, and automated reporting bots.

Supports both:
1. Direct SQLite mode (ultra-fast offline access to DB/procure.db)
2. HTTP REST API mode (connects over network to http://localhost:3001)

Zero external dependencies - runs on standard Python 3.
Example:
    from python.procure_sdk import ProcureSDK
    sdk = ProcureSDK()  # Direct DB mode by default
    procs = sdk.list_requisitions()
    pos = sdk.list_pos()
    print("Total Orders:", len(pos))
"""

import sys
import os
import json
import sqlite3
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# Setup import path for config_helper
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from config_helper import resolve_db_path, get_server_port
except ImportError:
    from python.config_helper import resolve_db_path, get_server_port

class ProcureSDK:
    def __init__(self, mode="db", base_url=None, db_path=None):
        """
        Initializes the SDK.
        :param mode: 'db' for direct SQLite access, 'api' for HTTP REST API.
        :param base_url: Base URL if running in 'api' mode. Defaults to port from config.json.
        :param db_path: Optional custom path to SQLite database.
        """
        self.mode = mode
        port = get_server_port()
        self.base_url = (base_url or f"http://localhost:{port}").rstrip("/")
        self.db_path = resolve_db_path(db_path)
        self.token = None

        if self.mode == "db" and not os.path.exists(self.db_path):
            raise FileNotFoundError(f"ProcureLocal SQLite DB not found at: {self.db_path}")

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _api_call(self, endpoint, method="GET", data=None):
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Cookie"] = f"sid={self.token}"

        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as res:
                content = res.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise RuntimeError(f"API Error {e.code}: {err_body}")

    def authenticate(self, username, password):
        """Authenticates with the REST API server and stores the session token."""
        if self.mode != "api":
            return True
        data = self._api_call("/api/login", method="POST", data={"username": username, "password": password})
        self.token = data.get("user", {}).get("token")
        return data

    def list_requisitions(self, stage=None):
        """Returns list of purchase requisitions, optionally filtered by stage."""
        if self.mode == "api":
            return self._api_call("/api/procs")
        
        with self._get_conn() as conn:
            if stage:
                rows = conn.execute("SELECT * FROM proc WHERE stage = ? ORDER BY id DESC", (stage,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM proc ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def get_requisition(self, proc_id):
        """Returns full details of a requisition including items, quotes, and approvals."""
        if self.mode == "api":
            return self._api_call(f"/api/procs/{proc_id}")

        with self._get_conn() as conn:
            p = conn.execute("SELECT * FROM proc WHERE id = ?", (proc_id,)).fetchone()
            if not p:
                return None
            items = conn.execute("SELECT * FROM items WHERE proc_id = ?", (proc_id,)).fetchall()
            quotes = conn.execute("SELECT * FROM quotes WHERE proc_id = ?", (proc_id,)).fetchall()
            approvals = conn.execute("SELECT * FROM approvals WHERE proc_id = ? ORDER BY seq ASC", (proc_id,)).fetchall()
            return {
                "proc": dict(p),
                "items": [dict(i) for i in items],
                "quotes": [dict(q) for q in quotes],
                "approvals": [dict(a) for a in approvals]
            }

    def list_pos(self):
        """Returns all issued Purchase Orders."""
        if self.mode == "api":
            return self._api_call("/api/pos")
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM pos ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def list_grns(self):
        """Returns all Store Inward / GRN receipts."""
        if self.mode == "api":
            return self._api_call("/api/grns")
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM grns ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def list_invoices(self):
        """Returns all vendor invoices and 3-way match statuses."""
        if self.mode == "api":
            return self._api_call("/api/invoices")
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT inv.*, p.po_no, p.vendor_name 
                FROM invoices inv
                LEFT JOIN pos p ON p.id = inv.po_id
                ORDER BY inv.id DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def list_vendors(self):
        """Returns all registered vendors with GSTIN, PAN, and MSME details."""
        if self.mode == "api":
            return self._api_call("/api/vendors")
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]

    def list_items(self):
        """Returns standard Item Master catalog items."""
        if self.mode == "api":
            return self._api_call("/api/catalog")
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM item_master ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]

    def get_settings(self):
        """Returns current system configuration and policy settings."""
        if self.mode == "api":
            return self._api_call("/api/me").get("settings", {})
        with self._get_conn() as conn:
            s = {}
            for r in conn.execute("SELECT k, v FROM settings").fetchall():
                try:
                    s[r["k"]] = json.loads(r["v"])
                except Exception:
                    s[r["k"]] = r["v"]
            return s

    def get_audit_trail(self, limit=100):
        """Returns system activity audit logs."""
        if self.mode == "api":
            return self._api_call("/api/audit")[:limit]
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT a.*, p.code as proc_code
                FROM audit a
                LEFT JOIN proc p ON p.id = a.proc_id
                ORDER BY a.id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def export_tally_pos(self, dest_path=None):
        """Generates Tally XML for all Purchase Orders."""
        from .tally_bridge import export_pos_tally_xml
        with self._get_conn() as conn:
            xml = export_pos_tally_xml(conn)
        if dest_path:
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(xml)
        return xml

    def export_excel_report(self, dest_path=None):
        """Generates multi-sheet Excel report."""
        from .excel_reports import generate_excel_xml
        with self._get_conn() as conn:
            xml = generate_excel_xml(conn)
        if dest_path:
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(xml)
        return xml

    def list_grns(self, proc_id=None):
        """Returns Goods Receipt Notes (Store Inward)."""
        if self.mode == "api":
            return self._api_call(f"/api/procs/{proc_id}/grns" if proc_id else "/api/grns")
        with self._get_conn() as conn:
            if proc_id:
                rows = conn.execute("SELECT * FROM grns WHERE proc_id=? ORDER BY id DESC", (proc_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM grns ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def list_assets(self, proc_id=None):
        """Returns Factory Fixed Assets from the Plant Asset Register."""
        if self.mode == "api":
            return self._api_call(f"/api/procs/{proc_id}/assets" if proc_id else "/api/assets")
        with self._get_conn() as conn:
            query = """
                SELECT a.*, p.code as proc_code, p.title as proc_title, p.dept, po.po_no, po.vendor_name
                FROM assets a
                LEFT JOIN proc p ON p.id = a.proc_id
                LEFT JOIN pos po ON po.id = a.po_id
            """
            if proc_id:
                query += " WHERE a.proc_id = ? ORDER BY a.id DESC"
                rows = conn.execute(query, (proc_id,)).fetchall()
            else:
                query += " ORDER BY a.id DESC"
                rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def close_requisition(self, proc_id, closed_by="System", remarks="Material received and asset capitalized."):
        """Formally closes a requisition and marks it complete."""
        if self.mode == "api":
            return self._api_call(f"/api/procs/{proc_id}/close", method="POST", data={"closed_by": closed_by, "close_remarks": remarks})
        with self._get_conn() as conn:
            now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                UPDATE proc 
                SET stage='completed', asset_status='capitalized', closed_at=?, closed_by=?, close_remarks=?, updated=?
                WHERE id=?
            """, (now_iso, closed_by, remarks, now_iso, proc_id))
            conn.commit()
            return {"ok": 1, "proc_id": proc_id, "stage": "completed"}

    def get_spend_analytics(self):
        """Computes Pareto ABC analysis, department spend, and savings metrics."""
        from .spend_analytics import compute_spend_analytics
        with self._get_conn() as conn:
            return compute_spend_analytics(conn)

