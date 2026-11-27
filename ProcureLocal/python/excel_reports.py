#!/usr/bin/env python3
"""
ProcureLocal - Enterprise Multi-Sheet Excel XML Report Generator
-----------------------------------------------------------------
Generates professional formatted Microsoft Excel workbooks (SpreadsheetML)
with multi-sheet analytics, styled headers, zebra striping, currency formats,
and audit summaries.

Zero external dependencies - runs on standard Python 3.
Usage:
    python excel_reports.py                     # Writes executive_procurement_report.xls
    python excel_reports.py --out my_report.xls
    python excel_reports.py --stdout            # Output XML to stdout for web download
"""

import sys
import os
import json
import sqlite3
import datetime
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

def xml_escape(val):
    if val is None:
        return ""
    s = str(val)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def generate_excel_xml(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    settings = get_settings(conn)
    company = settings.get("company", "Apex Enterprise Solutions India Pvt Ltd")
    today_str = datetime.date.today().strftime("%d-%b-%Y")

    # Fetch data sets
    procs = conn.execute("SELECT * FROM proc ORDER BY id DESC").fetchall()
    pos = conn.execute("SELECT * FROM pos ORDER BY id DESC").fetchall()
    vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
    invoices = conn.execute("""
        SELECT inv.*, p.po_no, p.vendor_name, pr.code as proc_code, pr.title as proc_title
        FROM invoices inv
        LEFT JOIN pos p ON p.id = inv.po_id
        LEFT JOIN proc pr ON pr.id = inv.proc_id
        ORDER BY inv.id DESC
    """).fetchall()
    assets = conn.execute("""
        SELECT a.*, pr.code as proc_code, pr.title as proc_title, pr.dept, po.po_no, po.vendor_name
        FROM assets a
        LEFT JOIN proc pr ON pr.id = a.proc_id
        LEFT JOIN pos po ON po.id = a.po_id
        ORDER BY a.id DESC
    """).fetchall()

    # XML SpreadsheetML Template
    xml_header = """<?xml version="1.0" encoding="utf-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal">
   <Alignment ss:Vertical="Center"/>
   <Borders/>
   <Font ss:FontName="Segoe UI" ss:Size="10" ss:Color="#1E293B"/>
   <Interior/>
   <NumberFormat/>
   <Protection/>
  </Style>
  <Style ss:ID="TitleStyle">
   <Font ss:FontName="Segoe UI" ss:Size="14" ss:Color="#0F172A" ss:Bold="1"/>
   <Alignment ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="SubTitleStyle">
   <Font ss:FontName="Segoe UI" ss:Size="10" ss:Color="#64748B" ss:Italic="1"/>
   <Alignment ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="HeaderStyle">
   <Font ss:FontName="Segoe UI" ss:Size="10.5" ss:Color="#FFFFFF" ss:Bold="1"/>
   <Interior ss:Color="#0F172A" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#000000"/>
   </Borders>
  </Style>
  <Style ss:ID="DataRow">
   <Font ss:FontName="Segoe UI" ss:Size="9.5" ss:Color="#1E293B"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
  </Style>
  <Style ss:ID="DataRowAlt">
   <Font ss:FontName="Segoe UI" ss:Size="9.5" ss:Color="#1E293B"/>
   <Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
  </Style>
  <Style ss:ID="CurrencyStyle" ss:Parent="DataRow">
   <NumberFormat ss:Format="#,##0.00"/>
   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="CurrencyStyleAlt" ss:Parent="DataRowAlt">
   <NumberFormat ss:Format="#,##0.00"/>
   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="CenterStyle" ss:Parent="DataRow">
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="CenterStyleAlt" ss:Parent="DataRowAlt">
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="BadgeGreen" ss:Parent="CenterStyle">
   <Font ss:FontName="Segoe UI" ss:Size="9" ss:Color="#15803D" ss:Bold="1"/>
   <Interior ss:Color="#DCFCE7" ss:Pattern="Solid"/>
  </Style>
  <Style ss:ID="BadgeBlue" ss:Parent="CenterStyle">
   <Font ss:FontName="Segoe UI" ss:Size="9" ss:Color="#1D4ED8" ss:Bold="1"/>
   <Interior ss:Color="#DBEAFE" ss:Pattern="Solid"/>
  </Style>
 </Styles>
"""

    sheets = []

    # ----------------------------------------------------
    # SHEET 1: Procurement Register
    # ----------------------------------------------------
    s1 = [' <Worksheet ss:Name="Procurement Register">']
    s1.append('  <Table ss:DefaultRowHeight="20">')
    s1.append('   <Column ss:Width="110"/>')
    s1.append('   <Column ss:Width="260"/>')
    s1.append('   <Column ss:Width="120"/>')
    s1.append('   <Column ss:Width="70"/>')
    s1.append('   <Column ss:Width="110"/>')
    s1.append('   <Column ss:Width="110"/>')
    s1.append('   <Column ss:Width="110"/>')
    s1.append('   <Column ss:Width="120"/>')
    
    # Title Row
    s1.append('   <Row ss:Height="26">')
    s1.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="TitleStyle"><Data ss:Type="String">{xml_escape(company)} - Procurement Register</Data></Cell>')
    s1.append('   </Row>')
    s1.append('   <Row ss:Height="18">')
    s1.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="SubTitleStyle"><Data ss:Type="String">Report Generated on: {today_str} | Source: ProcureLocal Enterprise Database</Data></Cell>')
    s1.append('   </Row>')
    s1.append('   <Row ss:Height="10"/>')

    # Headers
    headers1 = ["Requisition Code", "Scope / Work Description", "Department", "Type", "Estimated Budget", "Current Stage", "Target Vendor", "Created Date"]
    s1.append('   <Row ss:Height="24">')
    for h in headers1:
        s1.append(f'    <Cell ss:StyleID="HeaderStyle"><Data ss:Type="String">{h}</Data></Cell>')
    s1.append('   </Row>')

    for idx, p in enumerate(procs):
        st = "DataRowAlt" if idx % 2 else "DataRow"
        c_st = "CurrencyStyleAlt" if idx % 2 else "CurrencyStyle"
        cen_st = "CenterStyleAlt" if idx % 2 else "CenterStyle"
        est_val = float(p["est"] or 0)
        s1.append('   <Row ss:Height="21">')
        s1.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(p["code"])}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(p["title"])}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(p["dept"] or "Operations")}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(p["type"].upper())}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{est_val}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(p["stage"].upper())}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(p["citpc_vendor"] or "Competitive")}</Data></Cell>')
        s1.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(str(p["created"])[:10])}</Data></Cell>')
        s1.append('   </Row>')

    s1.append('  </Table>')
    s1.append(' </Worksheet>')
    sheets.append("\n".join(s1))

    # ----------------------------------------------------
    # SHEET 2: Purchase Orders Register
    # ----------------------------------------------------
    s2 = [' <Worksheet ss:Name="Purchase Orders">']
    s2.append('  <Table ss:DefaultRowHeight="20">')
    s2.append('   <Column ss:Width="110"/>')
    s2.append('   <Column ss:Width="95"/>')
    s2.append('   <Column ss:Width="230"/>')
    s2.append('   <Column ss:Width="110"/>')
    s2.append('   <Column ss:Width="100"/>')
    s2.append('   <Column ss:Width="115"/>')
    s2.append('   <Column ss:Width="150"/>')
    s2.append('   <Column ss:Width="90"/>')

    s2.append('   <Row ss:Height="26">')
    s2.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="TitleStyle"><Data ss:Type="String">{xml_escape(company)} - Official Purchase Orders</Data></Cell>')
    s2.append('   </Row>')
    s2.append('   <Row ss:Height="18">')
    s2.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="SubTitleStyle"><Data ss:Type="String">GSTIN &amp; Indian Statutory Compliant Purchase Order Records</Data></Cell>')
    s2.append('   </Row>')
    s2.append('   <Row ss:Height="10"/>')

    headers2 = ["PO Number", "PO Date", "Vendor / Supplier Name", "Basic Taxable", "GST Amount", "Landed Total", "Payment Terms", "Status"]
    s2.append('   <Row ss:Height="24">')
    for h in headers2:
        s2.append(f'    <Cell ss:StyleID="HeaderStyle"><Data ss:Type="String">{h}</Data></Cell>')
    s2.append('   </Row>')

    for idx, po in enumerate(pos):
        st = "DataRowAlt" if idx % 2 else "DataRow"
        c_st = "CurrencyStyleAlt" if idx % 2 else "CurrencyStyle"
        cen_st = "CenterStyleAlt" if idx % 2 else "CenterStyle"
        b_val = float(po["total_basic"] or 0)
        g_val = float(po["total_gst"] or 0)
        l_val = float(po["total_landed"] or (b_val + g_val))
        s2.append('   <Row ss:Height="21">')
        s2.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(po["po_no"])}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(po["po_date"])}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(po["vendor_name"])}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{b_val}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{g_val}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{l_val}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(po["payment_terms"] or "30 days")}</Data></Cell>')
        s2.append(f'    <Cell ss:StyleID="BadgeGreen"><Data ss:Type="String">{xml_escape(po["status"])}</Data></Cell>')
        s2.append('   </Row>')

    s2.append('  </Table>')
    s2.append(' </Worksheet>')
    sheets.append("\n".join(s2))

    # ----------------------------------------------------
    # SHEET 3: 3-Way Match & Invoicing
    # ----------------------------------------------------
    s3 = [' <Worksheet ss:Name="3-Way Match &amp; Invoices">']
    s3.append('  <Table ss:DefaultRowHeight="20">')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="210"/>')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="95"/>')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="110"/>')
    s3.append('   <Column ss:Width="130"/>')

    s3.append('   <Row ss:Height="26">')
    s3.append(f'    <Cell ss:MergeAcross="8" ss:StyleID="TitleStyle"><Data ss:Type="String">{xml_escape(company)} - 3-Way Match Verification</Data></Cell>')
    s3.append('   </Row>')
    s3.append('   <Row ss:Height="18">')
    s3.append(f'    <Cell ss:MergeAcross="8" ss:StyleID="SubTitleStyle"><Data ss:Type="String">Automated Reconciliation: Purchase Order ↔ Store GRN Inward ↔ Vendor Invoice</Data></Cell>')
    s3.append('   </Row>')
    s3.append('   <Row ss:Height="10"/>')

    headers3 = ["Requisition", "PO Number", "Vendor Name", "Invoice No", "Invoice Date", "Basic Amount", "Total Invoiced", "3-Way Status", "Payment Status"]
    s3.append('   <Row ss:Height="24">')
    for h in headers3:
        s3.append(f'    <Cell ss:StyleID="HeaderStyle"><Data ss:Type="String">{h}</Data></Cell>')
    s3.append('   </Row>')

    for idx, inv in enumerate(invoices):
        st = "DataRowAlt" if idx % 2 else "DataRow"
        c_st = "CurrencyStyleAlt" if idx % 2 else "CurrencyStyle"
        cen_st = "CenterStyleAlt" if idx % 2 else "CenterStyle"
        b_val = float(inv["amount"] or 0)
        t_val = float(inv["total_amount"] or b_val)
        m_badge = "BadgeGreen" if inv["match_status"] == "Matched" else "CenterStyle"
        s3.append('   <Row ss:Height="21">')
        s3.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(inv["proc_code"] or "—")}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(inv["po_no"] or "—")}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(inv["vendor_name"] or "—")}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(inv["invoice_no"] or "—")}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(inv["invoice_date"] or "—")}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{b_val}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{t_val}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{m_badge}"><Data ss:Type="String">{xml_escape(inv["match_status"])}</Data></Cell>')
        s3.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(inv["payment_status"])}</Data></Cell>')
        s3.append('   </Row>')

    s3.append('  </Table>')
    s3.append(' </Worksheet>')
    sheets.append("\n".join(s3))

    # ----------------------------------------------------
    # SHEET 4: Vendor Master & MSME
    # ----------------------------------------------------
    s4 = [' <Worksheet ss:Name="Vendor Directory">']
    s4.append('  <Table ss:DefaultRowHeight="20">')
    s4.append('   <Column ss:Width="230"/>')
    s4.append('   <Column ss:Width="130"/>')
    s4.append('   <Column ss:Width="95"/>')
    s4.append('   <Column ss:Width="110"/>')
    s4.append('   <Column ss:Width="110"/>')
    s4.append('   <Column ss:Width="150"/>')
    s4.append('   <Column ss:Width="110"/>')
    s4.append('   <Column ss:Width="150"/>')

    s4.append('   <Row ss:Height="26">')
    s4.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="TitleStyle"><Data ss:Type="String">{xml_escape(company)} - Vendor Master Directory</Data></Cell>')
    s4.append('   </Row>')
    s4.append('   <Row ss:Height="18">')
    s4.append(f'    <Cell ss:MergeAcross="7" ss:StyleID="SubTitleStyle"><Data ss:Type="String">Statutory MSME, GSTIN, Bank IFSC, and Contact Records</Data></Cell>')
    s4.append('   </Row>')
    s4.append('   <Row ss:Height="10"/>')

    headers4 = ["Vendor Name", "GSTIN", "PAN", "MSME Category", "City & State", "Bank Name", "IFSC Code", "Email / Phone"]
    s4.append('   <Row ss:Height="24">')
    for h in headers4:
        s4.append(f'    <Cell ss:StyleID="HeaderStyle"><Data ss:Type="String">{h}</Data></Cell>')
    s4.append('   </Row>')

    for idx, v in enumerate(vendors):
        st = "DataRowAlt" if idx % 2 else "DataRow"
        cen_st = "CenterStyleAlt" if idx % 2 else "CenterStyle"
        loc = f"{v['city'] or ''}, {v['state'] or ''}".strip(", ")
        contact = f"{v['email'] or ''} {v['phone'] or ''}".strip()
        s4.append('   <Row ss:Height="21">')
        s4.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(v["name"])}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(v["gst"] or "—")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(v["pan"] or "—")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(v["msme_type"] or "Non-MSME")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(loc or "India")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(v["bank_name"] or "—")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(v["ifsc"] or "—")}</Data></Cell>')
        s4.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(contact or "—")}</Data></Cell>')
        s4.append('   </Row>')

    s4.append('  </Table>')
    s4.append(' </Worksheet>')
    sheets.append("\n".join(s4))

    # ----------------------------------------------------
    # SHEET 5: Plant Asset Register & Capitalization
    # ----------------------------------------------------
    s5 = [' <Worksheet ss:Name="Plant Asset Register">']
    s5.append('  <Table ss:DefaultRowHeight="20">')
    s5.append('   <Column ss:Width="110"/>')
    s5.append('   <Column ss:Width="200"/>')
    s5.append('   <Column ss:Width="150"/>')
    s5.append('   <Column ss:Width="105"/>')
    s5.append('   <Column ss:Width="130"/>')
    s5.append('   <Column ss:Width="130"/>')
    s5.append('   <Column ss:Width="110"/>')
    s5.append('   <Column ss:Width="110"/>')
    s5.append('   <Column ss:Width="140"/>')

    s5.append('   <Row ss:Height="26">')
    s5.append(f'    <Cell ss:MergeAcross="8" ss:StyleID="TitleStyle"><Data ss:Type="String">{xml_escape(company)} - Plant Fixed Asset Register</Data></Cell>')
    s5.append('   </Row>')
    s5.append('   <Row ss:Height="18">')
    s5.append(f'    <Cell ss:MergeAcross="8" ss:StyleID="SubTitleStyle"><Data ss:Type="String">Factory Asset Tagging, Capitalization &amp; Put-to-Use Master Register</Data></Cell>')
    s5.append('   </Row>')
    s5.append('   <Row ss:Height="10"/>')

    headers5 = ["Asset Tag Code", "Equipment Name", "Asset Category", "Capitalization Date", "Plant Location", "Asset Custodian", "Serial Number", "Capitalized Cost", "Status"]
    s5.append('   <Row ss:Height="24">')
    for h in headers5:
        s5.append(f'    <Cell ss:StyleID="HeaderStyle"><Data ss:Type="String">{h}</Data></Cell>')
    s5.append('   </Row>')

    for idx, a in enumerate(assets):
        st = "DataRowAlt" if idx % 2 else "DataRow"
        cen_st = "CenterStyleAlt" if idx % 2 else "CenterStyle"
        c_st = "CurrencyStyleAlt" if idx % 2 else "CurrencyStyle"
        s5.append('   <Row ss:Height="21">')
        s5.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(a["asset_code"] or "—")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(a["asset_name"] or "—")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(a["category"] or "General")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(a["capitalization_date"] or "—")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(a["plant_location"] or "Factory Floor")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{st}"><Data ss:Type="String">{xml_escape(a["custodian"] or "—")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(a["serial_no"] or "—")}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{c_st}"><Data ss:Type="Number">{float(a["cost"] or 0)}</Data></Cell>')
        s5.append(f'    <Cell ss:StyleID="{cen_st}"><Data ss:Type="String">{xml_escape(a["status"] or "Capitalized")}</Data></Cell>')
        s5.append('   </Row>')

    s5.append('  </Table>')
    s5.append(' </Worksheet>')
    sheets.append("\n".join(s5))

    xml_footer = "</Workbook>"

    if close_conn:
        conn.close()

    return xml_header + "\n".join(sheets) + "\n" + xml_footer

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    import argparse
    parser = argparse.ArgumentParser(description="ProcureLocal Enterprise Multi-Sheet Excel Report Generator")
    parser.add_argument("--out", type=str, help="Destination .xls/.xml file path")
    parser.add_argument("--stdout", action="store_true", help="Print XML to standard output for streaming")
    parser.add_argument("--db", type=str, help="Path to custom procure.db database file")

    args = parser.parse_args()
    conn = get_db_connection(args.db) if args.db else None
    excel_content = generate_excel_xml(conn=conn)

    if args.stdout:
        sys.stdout.write(excel_content)
    else:
        out_path = args.out or str(ROOT_DIR / "executive_procurement_report.xls")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(excel_content)
        print(f"[OK] Successfully generated Multi-Sheet Excel report: {out_path}")
        print("  Features: Multi-sheet tabs (PR Register, POs, 3-Way Match, Vendors) with formatted styling.")

if __name__ == "__main__":
    main()

