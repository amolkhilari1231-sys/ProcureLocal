#!/usr/bin/env python3
"""
ProcureLocal - Executive Spend Analytics & ABC Pareto Analysis Engine
---------------------------------------------------------------------
Performs advanced procurement analytics on ProcureLocal data:
1. ABC Pareto 80/20 Classification (Strategic vs Routine spend)
2. Departmental spend distribution
3. Commercial negotiation savings metrics
4. Vendor Quality & GRN acceptance scorecards

Zero external dependencies - runs on standard Python 3.
Usage:
    python spend_analytics.py               # Visual terminal dashboard report
    python spend_analytics.py --json        # Outputs analytics as JSON
"""

import sys
import os
import json
import sqlite3
from pathlib import Path

# Resolve base paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "DB" / "procure.db"

def get_db_connection(db_path=None):
    path = db_path or DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"ProcureLocal database not found at {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def format_inr(number):
    """Formats a number into Indian Rupee formatting (e.g. 12,34,567.00)."""
    n = round(float(number or 0), 2)
    s = f"{n:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        return f"₹{integer_part}.{decimal_part}"

    last_three = integer_part[-3:]
    remaining = integer_part[:-3]
    chunks = []
    while len(remaining) > 2:
        chunks.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        chunks.insert(0, remaining)
    formatted = ",".join(chunks) + "," + last_three
    return f"₹{formatted}.{decimal_part}"

def compute_spend_analytics(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    # 1. Total Spend & Order Stats
    total_pos = conn.execute("SELECT count(*) as c, sum(total_landed) as s, sum(total_basic) as b FROM pos").fetchone()
    total_spend = float(total_pos["s"] or 0)
    total_basic = float(total_pos["b"] or 0)
    po_count = int(total_pos["c"] or 0)

    # 2. Spend by Vendor & ABC Analysis
    vendor_spend = conn.execute("""
        SELECT vendor_name, count(id) as orders_count, sum(total_landed) as total_amount
        FROM pos
        GROUP BY vendor_name
        ORDER BY total_amount DESC
    """).fetchall()

    abc_results = []
    cumulative = 0.0
    for v in vendor_spend:
        amt = float(v["total_amount"] or 0)
        cumulative += amt
        pct = (amt / total_spend * 100) if total_spend > 0 else 0
        cum_pct = (cumulative / total_spend * 100) if total_spend > 0 else 0
        
        if cum_pct <= 80 or len(abc_results) == 0:
            category = "A (Strategic)"
        elif cum_pct <= 95:
            category = "B (Tactical)"
        else:
            category = "C (Tail Spend)"

        abc_results.append({
            "vendor": v["vendor_name"],
            "orders": v["orders_count"],
            "spend": amt,
            "share_pct": round(pct, 1),
            "cum_pct": round(cum_pct, 1),
            "category": category
        })

    # 3. Departmental Spend Distribution
    dept_spend = conn.execute("""
        SELECT pr.dept, count(p.id) as po_count, sum(p.total_landed) as spend
        FROM pos p
        JOIN proc pr ON pr.id = p.proc_id
        GROUP BY pr.dept
        ORDER BY spend DESC
    """).fetchall()

    # 4. Commercial Savings Analysis (Budget vs Actual Landed PO)
    savings_data = conn.execute("""
        SELECT pr.code, pr.title, pr.est as budget, p.total_landed as actual
        FROM pos p
        JOIN proc pr ON pr.id = p.proc_id
        WHERE pr.est > 0
    """).fetchall()

    total_budget = sum(float(r["budget"] or 0) for r in savings_data)
    total_actual = sum(float(r["actual"] or 0) for r in savings_data)
    total_savings = max(0, total_budget - total_actual)
    savings_pct = (total_savings / total_budget * 100) if total_budget > 0 else 0

    # 5. Store Quality & Acceptance Scorecard
    grn_stats = conn.execute("""
        SELECT 
            sum(received_qty) as total_received,
            sum(accepted_qty) as total_accepted,
            sum(rejected_qty) as total_rejected
        FROM grn_items
    """).fetchone()

    rec = float(grn_stats["total_received"] or 0)
    acc = float(grn_stats["total_accepted"] or 0)
    rej = float(grn_stats["total_rejected"] or 0)
    acceptance_rate = (acc / rec * 100) if rec > 0 else 100.0

    if close_conn:
        conn.close()

    return {
        "total_spend": total_spend,
        "total_basic": total_basic,
        "po_count": po_count,
        "total_savings": total_savings,
        "savings_pct": round(savings_pct, 1),
        "total_budget": total_budget,
        "total_actual": total_actual,
        "acceptance_rate": round(acceptance_rate, 1),
        "total_received_qty": rec,
        "total_accepted_qty": acc,
        "total_rejected_qty": rej,
        "abc_analysis": abc_results,
        "department_spend": [
            {"dept": d["dept"] or "General Operations", "orders": d["po_count"], "spend": float(d["spend"] or 0)}
            for d in dept_spend
        ]
    }

def print_dashboard(data):
    w = 78
    print("=" * w)
    print("       PROCURELOCAL ENTERPRISE PROCUREMENT & SPEND INTELLIGENCE")
    print("=" * w)
    print(f" Total PO Spend (Landed) : {format_inr(data['total_spend']):<20} | Total POs Issued : {data['po_count']}")
    print(f" Negotiation Savings     : {format_inr(data['total_savings']):<20} | Savings Rate     : {data['savings_pct']}%")
    print(f" Store Quality Score     : {data['acceptance_rate']}% Accepted{'':<11} | Total Rejected   : {data['total_rejected_qty']:.0f} units")
    print("-" * w)
    
    # ABC Analysis Table
    print("\n[+] VENDOR ABC PARETO ANALYSIS (80/20 Rule):")
    print(f"{'Vendor Name':<34} {'Category':<15} {'Orders':<8} {'Spend Amount':<16} {'Share'}")
    print("-" * w)
    for v in data["abc_analysis"]:
        sp = format_inr(v["spend"])
        print(f"{v['vendor'][:32]:<34} {v['category']:<15} {v['orders']:<8} {sp:<16} {v['share_pct']}%")
    if not data["abc_analysis"]:
        print("  (No Purchase Orders recorded yet)")

    # Department Spend Table
    print("\n[+] SPEND DISTRIBUTION BY DEPARTMENT:")
    print(f"{'Department':<34} {'PO Count':<12} {'Landed Spend':<20}")
    print("-" * w)
    for d in data["department_spend"]:
        sp = format_inr(d["spend"])
        print(f"{d['dept'][:32]:<34} {d['orders']:<12} {sp:<20}")
    if not data["department_spend"]:
        print("  (No departmental orders found)")

    print("\n" + "=" * w)
    print("  [OK] Spend Intelligence Analysis Complete.")
    print("=" * w)

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    import argparse
    parser = argparse.ArgumentParser(description="ProcureLocal Spend Analytics & Pareto Engine")
    parser.add_argument("--json", action="store_true", help="Output analytics as raw JSON")
    parser.add_argument("--export-file", type=str, help="Export JSON results to specified file")

    args = parser.parse_args()
    data = compute_spend_analytics()

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_dashboard(data)

    if args.export_file:
        with open(args.export_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Analytics summary saved to: {args.export_file}")

if __name__ == "__main__":
    main()

