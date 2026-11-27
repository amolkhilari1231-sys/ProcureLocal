#!/usr/bin/env python3
"""
ProcureLocal - Tally ERP 9 / TallyPrime XML Integration Bridge
---------------------------------------------------------------
Converts Purchase Orders, Invoices, and Vendor Masters from ProcureLocal SQLite
into official Tally XML format (Tally Import Specification compliant).

Zero external dependencies - runs on standard Python 3.
Usage:
    python tally_bridge.py --all-pos           # Export all issued POs to tally_pos.xml
    python tally_bridge.py --all-invoices      # Export all invoices to tally_invoices.xml
    python tally_bridge.py --vendors           # Export vendor ledgers to tally_ledgers.xml
    python tally_bridge.py --stdout            # Output all active POs to stdout for API streaming
"""

import sys
import os
import json
import sqlite3
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

# Setup import path for config_helper
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from config_helper import resolve_db_path
except ImportError:
    from python.config_helper import resolve_db_path

def get_db_connection(db_path=None):
    path = resolve_db_path(db_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"ProcureLocal database not found at {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def get_settings(conn):
    s = {}
    for r in conn.execute("SELECT k, v FROM settings").fetchall():
        try:
            s[r["k"]] = json.loads(r["v"])
        except Exception:
            s[r["k"]] = r["v"]
    return s

def format_tally_date(date_str):
    """Converts YYYY-MM-DD or ISO timestamp into Tally YYYYMMDD format."""
    if not date_str:
        return datetime.date.today().strftime("%Y%m%d")
    clean = str(date_str)[:10].replace("-", "")
    return clean if len(clean) == 8 else datetime.date.today().strftime("%Y%m%d")

def generate_tally_envelope():
    """Generates the root Tally XML Envelope element."""
    env = ET.Element("ENVELOPE")
    hdr = ET.SubElement(env, "HEADER")
    tally_req = ET.SubElement(hdr, "TALLYREQUEST")
    tally_req.text = "Import Data"
    
    body = ET.SubElement(env, "BODY")
    imp_data = ET.SubElement(body, "IMPORTDATA")
    req_desc = ET.SubElement(imp_data, "REQUESTDESC")
    rep_name = ET.SubElement(req_desc, "REPORTNAME")
    rep_name.text = "Vouchers"
    req_data = ET.SubElement(imp_data, "REQUESTDATA")
    return env, req_data

def export_vendors_tally_xml(conn=None):
    """Exports all registered vendors as Tally Sundry Creditor Ledgers."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    settings = get_settings(conn)
    vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()

    env, req_data = generate_tally_envelope()

    for v in vendors:
        msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(msg, "LEDGER", {"NAME": v["name"], "ACTION": "Create"})
        
        ET.SubElement(ledger, "NAME").text = v["name"]
        ET.SubElement(ledger, "PARENT").text = "Sundry Creditors"
        ET.SubElement(ledger, "ISBILLWISEON").text = "Yes"
        ET.SubElement(ledger, "AFFECTSSTOCK").text = "No"
        
        # Statutory GST & PAN Details
        if v["gst"]:
            ET.SubElement(ledger, "PARTYGSTIN").text = v["gst"]
            ET.SubElement(ledger, "GSTREGISTRATIONTYPE").text = "Regular"
        if v["pan"]:
            ET.SubElement(ledger, "PANNUMBER").text = v["pan"]
        
        # Address Details
        if v["address"]:
            addr_list = ET.SubElement(ledger, "ADDRESS.LIST", {"TYPE": "String"})
            for line in v["address"].split(","):
                ET.SubElement(addr_list, "ADDRESS").text = line.strip()
        if v["state"]:
            ET.SubElement(ledger, "STATENAME").text = v["state"]
        if v["pincode"]:
            ET.SubElement(ledger, "PINCODE").text = v["pincode"]
        if v["email"]:
            ET.SubElement(ledger, "EMAIL").text = v["email"]
        if v["phone"]:
            ET.SubElement(ledger, "LEDGERPHONE").text = v["phone"]

    if close_conn:
        conn.close()

    return prettify_xml(env)

def export_pos_tally_xml(conn=None, po_id=None):
    """
    Exports Purchase Orders as Tally 'Purchase Order' Vouchers with inventory lines,
    rates, HSN, and GST ledger breakdown.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    settings = get_settings(conn)
    company_name = settings.get("company", "Apex Enterprise Solutions India Pvt Ltd")

    if po_id:
        pos = conn.execute("SELECT * FROM pos WHERE id = ?", (po_id,)).fetchall()
    else:
        pos = conn.execute("SELECT * FROM pos ORDER BY id ASC").fetchall()

    env, req_data = generate_tally_envelope()

    for po in pos:
        v_date = format_tally_date(po["po_date"])
        po_items = conn.execute("SELECT * FROM po_items WHERE po_id = ?", (po["id"],)).fetchall()
        
        msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        vch = ET.SubElement(msg, "VOUCHER", {"VCHTYPE": "Purchase Order", "ACTION": "Create"})
        
        ET.SubElement(vch, "DATE").text = v_date
        ET.SubElement(vch, "VOUCHERTYPENAME").text = "Purchase Order"
        ET.SubElement(vch, "VOUCHERNUMBER").text = po["po_no"]
        ET.SubElement(vch, "PARTYLEDGERNAME").text = po["vendor_name"]
        ET.SubElement(vch, "BASICBUYERNAME").text = company_name
        
        narration = f"ProcureLocal PO: {po['po_no']} | Terms: {po['payment_terms'] or 'Standard'} | Delivery: {po['delivery_terms'] or 'Standard'}"
        ET.SubElement(vch, "NARRATION").text = narration

        # Inventory Items Entries
        total_taxable = 0.0
        total_gst = 0.0
        for it in po_items:
            qty = float(it["qty"] or 1)
            rate = float(it["rate"] or 0)
            gst_pct = float(it["gst"] or 18)
            amount = round(qty * rate, 2)
            gst_amount = round(amount * (gst_pct / 100), 2)
            total_taxable += amount
            total_gst += gst_amount

            inv_entry = ET.SubElement(vch, "ALLINVENTORYENTRIES.LIST")
            ET.SubElement(inv_entry, "STOCKITEMNAME").text = it["name"]
            ET.SubElement(inv_entry, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(inv_entry, "RATE").text = f"{rate:.2f}/{it['unit'] or 'NOS'}"
            ET.SubElement(inv_entry, "ACTUALQTY").text = f"{qty} {it['unit'] or 'NOS'}"
            ET.SubElement(inv_entry, "BILLEDQTY").text = f"{qty} {it['unit'] or 'NOS'}"
            ET.SubElement(inv_entry, "AMOUNT").text = f"-{amount:.2f}"
            
            # Batch & HSN Allocation
            batch_alloc = ET.SubElement(inv_entry, "BATCHALLOCATIONS.LIST")
            ET.SubElement(batch_alloc, "GODOWNNAME").text = "Main Location"
            ET.SubElement(batch_alloc, "BATCHNAME").text = "Primary Batch"
            ET.SubElement(batch_alloc, "AMOUNT").text = f"-{amount:.2f}"
            ET.SubElement(batch_alloc, "ACTUALQTY").text = f"{qty} {it['unit'] or 'NOS'}"
            ET.SubElement(batch_alloc, "BILLEDQTY").text = f"{qty} {it['unit'] or 'NOS'}"

        # Purchase Account Ledger (Debit)
        pur_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(pur_ledger, "LEDGERNAME").text = "Purchase Account"
        ET.SubElement(pur_ledger, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(pur_ledger, "AMOUNT").text = f"-{total_taxable:.2f}"

        # GST Ledger (CGST/SGST 9%+9% or IGST 18%)
        half_gst = round(total_gst / 2.0, 2)
        cgst_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(cgst_ledger, "LEDGERNAME").text = "Input CGST"
        ET.SubElement(cgst_ledger, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(cgst_ledger, "AMOUNT").text = f"-{half_gst:.2f}"

        sgst_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(sgst_ledger, "LEDGERNAME").text = "Input SGST"
        ET.SubElement(sgst_ledger, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(sgst_ledger, "AMOUNT").text = f"-{half_gst:.2f}"

        # Party Ledger (Credit total landed)
        party_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(party_ledger, "LEDGERNAME").text = po["vendor_name"]
        ET.SubElement(party_ledger, "ISDEEMEDPOSITIVE").text = "No"
        total_landed = total_taxable + total_gst
        ET.SubElement(party_ledger, "AMOUNT").text = f"{total_landed:.2f}"

    if close_conn:
        conn.close()

    return prettify_xml(env)

def export_invoices_tally_xml(conn=None):
    """
    Exports 3-Way Matched Invoices as Tally 'Purchase' Vouchers.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    invoices = conn.execute("""
        SELECT inv.*, p.vendor_name, p.po_no 
        FROM invoices inv
        LEFT JOIN pos p ON p.id = inv.po_id
        ORDER BY inv.id ASC
    """).fetchall()

    env, req_data = generate_tally_envelope()

    for inv in invoices:
        v_date = format_tally_date(inv["invoice_date"])
        msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        vch = ET.SubElement(msg, "VOUCHER", {"VCHTYPE": "Purchase", "ACTION": "Create"})
        
        ET.SubElement(vch, "DATE").text = v_date
        ET.SubElement(vch, "VOUCHERTYPENAME").text = "Purchase"
        ET.SubElement(vch, "VOUCHERNUMBER").text = inv["invoice_no"] or f"INV-{inv['id']}"
        ET.SubElement(vch, "REFERENCE").text = inv["po_no"] or ""
        ET.SubElement(vch, "PARTYLEDGERNAME").text = inv["vendor_name"] or "Sundry Creditors"
        
        narration = f"Tax Invoice No: {inv['invoice_no']} | PO Ref: {inv['po_no']} | Match Status: {inv['match_status']} | Payment: {inv['payment_status']}"
        ET.SubElement(vch, "NARRATION").text = narration

        basic = float(inv["amount"] or 0)
        gst = float(inv["gst_amount"] or 0)
        total = float(inv["total_amount"] or (basic + gst))

        # Purchase Account (Debit)
        pur_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(pur_ledger, "LEDGERNAME").text = "Purchase Account"
        ET.SubElement(pur_ledger, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(pur_ledger, "AMOUNT").text = f"-{basic:.2f}"

        # Input Tax (Debit)
        tax_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(tax_ledger, "LEDGERNAME").text = "Input GST"
        ET.SubElement(tax_ledger, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(tax_ledger, "AMOUNT").text = f"-{gst:.2f}"

        # Party Ledger (Credit)
        party_ledger = ET.SubElement(vch, "LEDGERENTRIES.LIST")
        ET.SubElement(party_ledger, "LEDGERNAME").text = inv["vendor_name"] or "Sundry Creditors"
        ET.SubElement(party_ledger, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(party_ledger, "AMOUNT").text = f"{total:.2f}"

    if close_conn:
        conn.close()

    return prettify_xml(env)

def prettify_xml(elem):
    """Returns a formatted, indented XML string with utf-8 encoding."""
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ProcureLocal to Tally XML Export Bridge")
    parser.add_argument("--all-pos", action="store_true", help="Export all Purchase Orders to Tally XML")
    parser.add_argument("--po", type=int, help="Export specific PO by ID")
    parser.add_argument("--all-invoices", action="store_true", help="Export all Invoices to Tally XML")
    parser.add_argument("--vendors", action="store_true", help="Export Vendor Master Ledgers to Tally XML")
    parser.add_argument("--stdout", action="store_true", help="Print XML to standard output (for streaming)")
    parser.add_argument("--out", type=str, help="Destination XML file path")
    parser.add_argument("--db", type=str, help="Path to custom procure.db database file")

    args = parser.parse_args()
    conn = get_db_connection(args.db) if args.db else None

    # Default action if no flag specified: export all POs
    xml_content = ""
    default_filename = "tally_export.xml"

    if args.vendors:
        xml_content = export_vendors_tally_xml(conn=conn)
        default_filename = "tally_vendor_ledgers.xml"
    elif args.all_invoices:
        xml_content = export_invoices_tally_xml(conn=conn)
        default_filename = "tally_invoices.xml"
    else:
        xml_content = export_pos_tally_xml(conn=conn, po_id=args.po)
        default_filename = "tally_purchase_orders.xml"

    if args.stdout:
        sys.stdout.write(xml_content)
    else:
        out_path = args.out or str(ROOT_DIR / default_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"✔ Successfully exported Tally XML to: {out_path}")
        print("  Import in Tally: Gateway of Tally -> Import Data -> Vouchers / Masters")

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    main()
