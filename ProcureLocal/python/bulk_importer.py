#!/usr/bin/env python3
"""
ProcureLocal - CSV Bulk Importer for Vendors & Item Master
----------------------------------------------------------
Imports bulk CSV data into ProcureLocal SQLite database:
1. Vendor Master with GSTIN validation and automatic PAN extraction
2. Item Master & Materials Catalog with HSN/SAC codes

Zero external dependencies - runs on standard Python 3.
Usage:
    python bulk_importer.py --generate-templates        # Creates sample CSV files
    python bulk_importer.py --vendors vendors.csv       # Bulk import vendors
    python bulk_importer.py --items items.csv           # Bulk import catalog items
"""

import sys
import os
import csv
import re
import sqlite3
import datetime
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

def validate_gstin(gst):
    """Validates 15-character Indian GSTIN and extracts 10-character PAN."""
    if not gst:
        return True, ""
    g = str(gst).strip().upper()
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if re.match(pattern, g):
        pan = g[2:12]
        return True, pan
    return False, ""

def import_vendors_csv(csv_path, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Vendor CSV file not found: {csv_path}")

    inserted = 0
    updated = 0
    skipped = 0

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or row.get("vendor_name") or "").strip()
            if not name:
                skipped += 1
                continue

            gst = (row.get("gst") or row.get("gstin") or "").strip().upper()
            pan = (row.get("pan") or "").strip().upper()

            if gst and not pan:
                is_valid, extracted_pan = validate_gstin(gst)
                if is_valid:
                    pan = extracted_pan

            address = (row.get("address") or "").strip()
            city = (row.get("city") or "").strip()
            state = (row.get("state") or "").strip()
            pincode = (row.get("pincode") or "").strip()
            contact = (row.get("contact") or "").strip()
            phone = (row.get("phone") or "").strip()
            email = (row.get("email") or "").strip()
            msme_type = (row.get("msme_type") or "Non-MSME").strip()
            msme_no = (row.get("msme_no") or "").strip()
            bank_name = (row.get("bank_name") or "").strip()
            bank_ac = (row.get("bank_ac") or "").strip()
            ifsc = (row.get("ifsc") or "").strip().upper()
            payment_terms = (row.get("payment_terms") or "30 days from GRN").strip()

            existing = conn.execute("SELECT id FROM vendors WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE vendors 
                    SET gst = COALESCE(NULLIF(?, ''), gst),
                        pan = COALESCE(NULLIF(?, ''), pan),
                        address = COALESCE(NULLIF(?, ''), address),
                        city = COALESCE(NULLIF(?, ''), city),
                        state = COALESCE(NULLIF(?, ''), state),
                        pincode = COALESCE(NULLIF(?, ''), pincode),
                        contact = COALESCE(NULLIF(?, ''), contact),
                        phone = COALESCE(NULLIF(?, ''), phone),
                        email = COALESCE(NULLIF(?, ''), email),
                        msme_type = COALESCE(NULLIF(?, ''), msme_type),
                        msme_no = COALESCE(NULLIF(?, ''), msme_no),
                        bank_name = COALESCE(NULLIF(?, ''), bank_name),
                        bank_ac = COALESCE(NULLIF(?, ''), bank_ac),
                        ifsc = COALESCE(NULLIF(?, ''), ifsc),
                        payment_terms = COALESCE(NULLIF(?, ''), payment_terms)
                    WHERE id = ?
                """, (gst, pan, address, city, state, pincode, contact, phone, email, msme_type, msme_no, bank_name, bank_ac, ifsc, payment_terms, existing["id"]))
                updated += 1
            else:
                conn.execute("""
                    INSERT INTO vendors (name, address, gst, contact, phone, email, pan, msme_type, msme_no, bank_name, bank_ac, ifsc, payment_terms, city, state, pincode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, address, gst, contact, phone, email, pan, msme_type, msme_no, bank_name, bank_ac, ifsc, payment_terms, city, state, pincode))
                inserted += 1

    conn.commit()
    # Log audit entry
    conn.execute("INSERT INTO audit(at, user, act) VALUES(?, 'python_importer', ?)",
                 (datetime.datetime.now().isoformat(), f"Bulk imported vendors: {inserted} inserted, {updated} updated from {Path(csv_path).name}"))
    conn.commit()

    if close_conn:
        conn.close()

    print(f"[OK] Vendor Import Complete: {inserted} added, {updated} updated, {skipped} skipped.")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}

def import_items_csv(csv_path, conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Items CSV file not found: {csv_path}")

    inserted = 0
    updated = 0
    skipped = 0

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or row.get("item_name") or "").strip()
            if not name:
                skipped += 1
                continue

            code = (row.get("code") or row.get("item_code") or "").strip()
            if not code:
                # Auto-generate a clean item code
                code = "MAT-" + "".join(re.findall(r"[A-Za-z0-9]", name[:10])).upper()

            category = (row.get("category") or "General Consumables").strip()
            unit = (row.get("unit") or "NOS").strip()
            hsn = (row.get("hsn") or row.get("sac") or "").strip()
            descr = (row.get("descr") or row.get("description") or "").strip()
            try:
                rate = float(row.get("citpc_rate") or row.get("standard_rate") or row.get("rate") or 0)
            except ValueError:
                rate = 0.0

            existing = conn.execute("SELECT id FROM item_master WHERE code = ? OR name = ? COLLATE NOCASE", (code, name)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE item_master 
                    SET name = ?, category = ?, unit = ?, hsn = ?, descr = ?, citpc_rate = ?
                    WHERE id = ?
                """, (name, category, unit, hsn, descr, rate, existing["id"]))
                updated += 1
            else:
                conn.execute("""
                    INSERT INTO item_master (code, name, descr, category, unit, hsn, citpc_rate, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (code, name, descr, category, unit, hsn, rate, datetime.date.today().isoformat()))
                inserted += 1

    conn.commit()
    conn.execute("INSERT INTO audit(at, user, act) VALUES(?, 'python_importer', ?)",
                 (datetime.datetime.now().isoformat(), f"Bulk imported items: {inserted} inserted, {updated} updated from {Path(csv_path).name}"))
    conn.commit()

    if close_conn:
        conn.close()

    print(f"[OK] Item Master Import Complete: {inserted} added, {updated} updated, {skipped} skipped.")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}

def generate_sample_templates():
    """Generates ready-to-use sample CSV templates for vendors and item master."""
    v_path = ROOT_DIR / "sample_vendors.csv"
    with open(v_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "gst", "pan", "msme_type", "msme_no", "address", "city", "state", "pincode", "contact", "phone", "email", "bank_name", "bank_ac", "ifsc", "payment_terms"])
        writer.writerow(["Tata Steel Limited", "27AAACT2727Q1ZW", "AAACT2727Q", "Non-MSME", "", "Bombay House, 24 Homi Mody Street", "Mumbai", "Maharashtra", "400001", "Ajay Verma", "+91 22 6665 8282", "sales@tatasteel.com", "State Bank of India", "10293847561", "SBIN0000300", "30 days from GRN"])
        writer.writerow(["Precision Tech Machining Works", "27AAKFP4321A1Z8", "AAKFP4321A", "MSME - Small", "UDYAM-MH-01-0012345", "MIDC Bhosari, Plot 88", "Pune", "Maharashtra", "411026", "Suresh Patel", "+91 98220 12345", "precision.tech@gmail.com", "HDFC Bank", "50200019283746", "HDFC0000123", "15 days from GRN"])
    
    i_path = ROOT_DIR / "sample_item_master.csv"
    with open(i_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "name", "category", "unit", "hsn", "descr", "citpc_rate"])
        writer.writerow(["MAT-SS-BOLT-M12", "SS 316 Hex Bolt M12 x 50mm", "Fasteners & Hardware", "NOS", "73181500", "Grade 316 Stainless Steel Hexagonal head bolt with nut", "45.00"])
        writer.writerow(["MAT-BEARING-6205", "Deep Groove Ball Bearing 6205-2RS", "Mechanical Spares", "NOS", "84821010", "High speed double sealed motor ball bearing", "380.00"])
        writer.writerow(["MAT-CAT6-CABLE", "Cat6 UTP 4-Pair Network Cable 305m", "Networking & IT", "ROLL", "85444999", "D-Link / Molex 24 AWG solid bare copper Ethernet cable box", "7850.00"])

    print(f"[OK] Generated Sample CSV Templates:")
    print(f"  1. Vendor Master Template : {v_path}")
    print(f"  2. Item Master Template   : {i_path}")

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    import argparse
    parser = argparse.ArgumentParser(description="ProcureLocal CSV Bulk Importer")
    parser.add_argument("--generate-templates", action="store_true", help="Generate sample CSV templates")
    parser.add_argument("--vendors", type=str, help="Path to vendors CSV file to import")
    parser.add_argument("--items", type=str, help="Path to items CSV file to import")

    args = parser.parse_args()

    if args.generate_templates:
        generate_sample_templates()
    elif args.vendors:
        import_vendors_csv(args.vendors)
    elif args.items:
        import_items_csv(args.items)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

