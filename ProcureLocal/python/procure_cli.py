#!/usr/bin/env python3
"""
ProcureLocal - Executive Procurement CLI & Administrative Console
------------------------------------------------------------------
Interactive command-line control center for ProcureLocal:
- Query active requisitions, POs, GRNs, and 3-way match invoices
- Export directly to Tally ERP 9 / TallyPrime XML
- Generate executive multi-sheet Excel reports
- Run ABC Pareto spend analytics
- Import bulk vendors and items

Zero external dependencies - runs on standard Python 3.
Usage:
    python procure_cli.py               # Interactive menu
    python procure_cli.py list          # List active requisitions
    python procure_cli.py pos           # List purchase orders
    python procure_cli.py tally         # Export Tally XML
    python procure_cli.py excel         # Generate Excel report
    python procure_cli.py analytics     # Spend analytics dashboard
    python procure_cli.py audit         # Recent compliance audit log
"""

import sys
import os
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup import path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

from python.procure_sdk import ProcureSDK
from python.spend_analytics import format_inr, compute_spend_analytics, print_dashboard
from python.tally_bridge import export_pos_tally_xml, export_vendors_tally_xml
from python.excel_reports import generate_excel_xml
from python.bulk_importer import import_vendors_csv, import_items_csv, generate_sample_templates

def show_banner():
    print("""
==============================================================================
  🏭 PROCURELOCAL v3 ENTERPRISE - COMMAND-LINE SUITE (PYTHON 3)
  Zero-Cloud Local Procurement & Statutory Compliance Engine
==============================================================================""")

def cmd_list(sdk):
    procs = sdk.list_requisitions()
    print(f"\n[+] PURCHASE REQUISITIONS ({len(procs)} Total):")
    print("-" * 78)
    print(f"{'Code':<15} {'Type':<8} {'Stage':<14} {'Estimated (₹)':<16} {'Title'}")
    print("-" * 78)
    for p in procs:
        est = format_inr(p["est"])
        print(f"{p['code']:<15} {p['type'].upper():<8} {p['stage'].upper():<14} {est:<16} {p['title'][:22]}")
    print("-" * 78)

def cmd_pos(sdk):
    pos = sdk.list_pos()
    print(f"\n[+] ISSUED PURCHASE ORDERS ({len(pos)} Total):")
    print("-" * 78)
    print(f"{'PO Number':<16} {'Date':<12} {'Landed Amount':<16} {'Status':<10} {'Vendor Name'}")
    print("-" * 78)
    for po in pos:
        landed = format_inr(po["total_landed"])
        print(f"{po['po_no']:<16} {po['po_date']:<12} {landed:<16} {po['status']:<10} {po['vendor_name'][:20]}")
    print("-" * 78)

def cmd_invoices(sdk):
    invs = sdk.list_invoices()
    print(f"\n[+] 3-WAY MATCHING & INVOICES ({len(invs)} Total):")
    print("-" * 78)
    print(f"{'Invoice No':<16} {'PO Ref':<15} {'Total Amount':<15} {'Match':<12} {'Payment'}")
    print("-" * 78)
    for inv in invs:
        tot = format_inr(inv["total_amount"])
        print(f"{inv['invoice_no']:<16} {inv['po_no'] or '—':<15} {tot:<15} {inv['match_status']:<12} {inv['payment_status']}")
    print("-" * 78)

def cmd_vendors(sdk):
    vends = sdk.list_vendors()
    print(f"\n[+] VENDOR MASTER DIRECTORY ({len(vends)} Total):")
    print("-" * 78)
    print(f"{'Vendor Name':<30} {'GSTIN':<17} {'PAN':<12} {'MSME Type'}")
    print("-" * 78)
    for v in vends:
        print(f"{v['name'][:28]:<30} {v['gst'] or '—':<17} {v['pan'] or '—':<12} {v['msme_type'] or 'Non-MSME'}")
    print("-" * 78)

def cmd_audit(sdk):
    logs = sdk.get_audit_trail(limit=15)
    print(f"\n[+] RECENT COMPLIANCE AUDIT TRAIL (Last 15 Events):")
    print("-" * 78)
    print(f"{'Timestamp':<17} {'User':<12} {'Requisition':<14} {'Action'}")
    print("-" * 78)
    for l in logs:
        ts = str(l["at"])[:16].replace("T", " ")
        code = l["proc_code"] or "System"
        print(f"{ts:<17} {l['user'][:10]:<12} {code:<14} {l['act'][:32]}")
    print("-" * 78)

def cmd_tally():
    out_path = ROOT_DIR / "tally_purchase_orders.xml"
    sdk = ProcureSDK()
    sdk.export_tally_pos(str(out_path))
    print(f"\n[OK] Exported Tally XML to: {out_path}")
    print("     Import into Tally: Gateway of Tally -> Import Data -> Vouchers")

def cmd_excel():
    out_path = ROOT_DIR / "executive_procurement_report.xls"
    sdk = ProcureSDK()
    sdk.export_excel_report(str(out_path))
    print(f"\n[OK] Generated Formatted Multi-Sheet Excel Report: {out_path}")
    print("     Open directly in Microsoft Excel or Google Sheets.")

def interactive_menu(sdk):
    show_banner()
    while True:
        print("\nSelect an Operation:")
        print("  [1] List Purchase Requisitions (PR)")
        print("  [2] View Issued Purchase Orders (PO/SO)")
        print("  [3] View 3-Way Match Invoices")
        print("  [4] Vendor Master & MSME Directory")
        print("  [5] Run Executive Spend Analytics (Pareto ABC)")
        print("  [6] Export Purchase Orders to Tally XML")
        print("  [7] Generate Multi-Sheet Excel Workbook")
        print("  [8] Generate Sample Bulk Import CSV Templates")
        print("  [9] View Recent Audit Trail")
        print("  [0] Exit")
        
        try:
            choice = input("\nEnter choice [0-9]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "1":
            cmd_list(sdk)
        elif choice == "2":
            cmd_pos(sdk)
        elif choice == "3":
            cmd_invoices(sdk)
        elif choice == "4":
            cmd_vendors(sdk)
        elif choice == "5":
            print_dashboard(compute_spend_analytics())
        elif choice == "6":
            cmd_tally()
        elif choice == "7":
            cmd_excel()
        elif choice == "8":
            generate_sample_templates()
        elif choice == "9":
            cmd_audit(sdk)
        elif choice == "0" or choice.lower() == "q":
            print("Goodbye!")
            break
        else:
            print("[!] Invalid option. Please enter 0 to 9.")

def main():
    sdk = ProcureSDK()
    args = sys.argv[1:]

    if not args:
        interactive_menu(sdk)
        return

    cmd = args[0].lower()
    if cmd in ("list", "pr", "requisitions"):
        cmd_list(sdk)
    elif cmd in ("pos", "po", "orders"):
        cmd_pos(sdk)
    elif cmd in ("inv", "invoices", "3way"):
        cmd_invoices(sdk)
    elif cmd in ("vendors", "suppliers"):
        cmd_vendors(sdk)
    elif cmd in ("analytics", "spend", "pareto"):
        print_dashboard(compute_spend_analytics())
    elif cmd in ("tally", "tallyxml"):
        cmd_tally()
    elif cmd in ("excel", "report", "xls"):
        cmd_excel()
    elif cmd in ("audit", "log", "trail"):
        cmd_audit(sdk)
    elif cmd in ("templates", "samples"):
        generate_sample_templates()
    elif cmd in ("help", "--help", "-h"):
        print(__doc__)
    else:
        print(f"Unknown command: '{cmd}'. Available commands: list, pos, invoices, vendors, analytics, tally, excel, audit, templates")

if __name__ == "__main__":
    main()

