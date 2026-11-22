# ProcureLocal Enterprise Edition (SAP / Tally Grade)

**Air-Gapped Multi-System Enterprise Procurement, Multi-Round Bidding, Sanctioning, Inward (GRN), Fixed Asset Capitalization, Statutory Forms, Vendor Compliance, and 3-Way Matching ERP Studio.**

[![Runtime](https://img.shields.io/badge/Runtime-Node.js%2022%20LTS-brightgreen.svg)](https://nodejs.org)
[![Database](https://img.shields.io/badge/Database-Embedded%20Native%20SQLite%203-blue.svg)](https://nodejs.org/api/sqlite.html)
[![Languages](https://img.shields.io/badge/Polyglot-C%23%20%7C%20Python%20%7C%20Java%20%7C%20Node.js-blueviolet.svg)](#)
[![Architecture](https://img.shields.io/badge/Architecture-Centralized%20Multi--System%20LAN-orange.svg)](#)
[![Compliance](https://img.shields.io/badge/Compliance-SOX%20%7C%20ISO%209001%20Audit%20Ready-red.svg)](#)
[![Desktop](https://img.shields.io/badge/Desktop-All--In--One%20Windows%20EXE-informational.svg)](#)

---

## 🌐 Standalone Multi-System Architecture (Central Remote Shared Database / NAS)

ProcureLocal delivers an air-gapped, zero-friction **1-Step Standalone Architecture**. Every user on any workstation runs `ProcureLocal.exe` directly in a single click—no host/client mode selection popups or manual IP handshakes required. All workstations automatically point to and synchronize with **ONE Central Remote Database & Document Vault** stored on your office Network Shared Drive or NAS:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│             🏢 CENTRAL REMOTE NETWORK SHARED DRIVE / NAS (Windows Share)         │
│             UNC Path: \\Server\SharedData\ProcureDB  (or Mapped Drive Z:\)       │
│                                                                                  │
│   • ONE Central SQLite Database: procure.db (Multi-User Concurrency Engine)      │
│   • ONE Central Document Vault: documents/ (Quotations, POs, Invoices, Formats) │
│   • ONE Central Audit Ledger: backups/ (SOX Snapshots & Cryptographic Hashes)   │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │ (Windows SMB File Share)       │ (Windows SMB File Share)       │ (Windows SMB File Share)
        ▼                                ▼                                ▼
┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ 💻 WORKSTATION 1 (COMM)  │      │ 💻 WORKSTATION 2 (STR)  │      │ 💻 WORKSTATION 3 (MGT)  │
│ Commercial / Purchasing │      │ Warehouse Store Inward  │      │ HOD / Finance Approvals │
│                         │      │                         │      │                         │
│ • ProcureLocal.exe      │      │ • ProcureLocal.exe      │      │ • ProcureLocal.exe      │
│ • 1-Click Direct Launch │      │ • 1-Click Direct Launch │      │ • 1-Click Direct Launch │
│ • Target: \\Server\...  │      │ • Target: \\Server\...  │      │ • Target: \\Server\...  │
└─────────────────────────┘      └─────────────────────────┘      └─────────────────────────┘
```

### 🔑 1-Step Standalone Simplicity:
1. **Zero Setup Prompts on Launch:**
   - Double-clicking **`ProcureLocal.exe`** starts the application immediately in 1 step! No dialogs asking to pick "Host Server" or "Client Mode".
2. **Central Remote Data Storage:**
   - Every workstation reads and writes directly to the central shared folder (`\\Server\SharedData\ProcureDB` or `Z:\ProcureDB`).
   - When Commercial enters quotes, Store Inward receives material (GRN), or Finance approves POs, all changes are saved to the single remote database in real-time.
3. **Enterprise Concurrency & Network Share Protection:**
   - ProcureLocal features native SQLite concurrency optimization with `PRAGMA busy_timeout = 15000` (15-second automatic wait for write locks) and `PRAGMA synchronous = NORMAL`. Multiple users across different office systems can read and write simultaneously without database locks or corruption.
4. **How to Point Workstations to the Remote Shared Database:**
   - **Method 1 (In-App Settings UI - Recommended):** Open `ProcureLocal` -> Click **`Settings & Audit`** -> Scroll to **`📁 Remote Shared Database (NAS / Windows Share)`** -> Enter the remote path (e.g. `\\Server\SharedData\ProcureDB`) -> Click **"🔄 Test Read/Write Access"** -> Click **"💾 Save Remote Share Path"**.
   - **Method 2 (Configuration File):** Open `config.json` in the ProcureLocal folder and set `"dataDir": "\\\\Server\\SharedData\\ProcureDB"`.
   - **Method 3 (Command-Line):** Run `ProcureLocal.exe --set-db "\\Server\SharedData\ProcureDB"`.

---

## ⚡ Polyglot Multi-Language Architecture (C#, Python, Java, Node.js)

ProcureLocal strategically unifies four enterprise languages, assigning each language to the exact domain where it excels:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PROCURELOCAL POLYGLOT ENTERPRISE SUITE                          │
├───────────────────┬───────────────────┬─────────────────────────┬──────────────────────┤
│  🖥️ C# (.NET)     │  🐍 PYTHON 3      │  ☕ JAVA (ENTERPRISE)   │  🟢 NODE.JS 22 LTS   │
├───────────────────┼───────────────────┼─────────────────────────┼──────────────────────┤
│ • Standalone All- │ • TallyPrime /    │ • SAP ECC 6.0 & S/4HANA │ • Embedded Native    │
│   In-One Launcher │   Tally ERP 9 XML │   RFC & BAPI Connector  │   SQLite Database    │
│   (ProcureLocal)  │   Voucher Bridge  │   (BAPI_PO_CREATE1)     │   (WAL Engine)       │
│ • 1-Click Launch  │ • Spend Analytics │ • SAP Material Master & │ • Central Document   │
│ • Remote NAS / DB │   & Pareto 80/20  │   Asset Master (FI-AA)  │   Vault Management   │
│ • Direct Hardware │   ABC Intelligence│ • Multi-Threaded Batch  │ • High-Concurrency   │
│   Thermal Barcode │ • Multi-Sheet     │   Integrity Processor   │   REST API Server    │
│   Printer Spooler │   Styled Excel    │ • SHA-256 Cryptographic │ • Real-Time Live     │
│   (Zebra / TSC)   │   Workbooks       │   Audit Ledger Chain    │   Sync Studio UI     │
└───────────────────┴───────────────────┴─────────────────────────┴──────────────────────┘
```

### 1. 🖥️ C# (.NET) Enterprise Desktop Launcher & Hardware Spooler
- **All-In-One Single Executable (`ProcureLocal.exe`):** Compiled with native Windows `.NET Framework` (`csc.exe`). Runs on any Windows 10/11 system without external runtimes in **1 direct step**.
- **Remote Shared DB Configurator:** Auto-mounts the central network shared folder or NAS (`\\Server\SharedData\ProcureDB`), with GUI folder browsing and read/write access testing via `--setup` or `--config-db`.
- **Direct Thermal Barcode Spooler (`RawPrinterHelper`):** Interacts directly with Windows `winspool.drv` API to dispatch raw ZPL / EPL / ESC-POS printer codes straight to factory thermal barcode sticker printers (Zebra, TSC, Citizen, TVS) without browser print dialogs.

### 2. 🐍 Python 3 Data Intelligence & Accounting Suite (`python/`)
- **TallyPrime / Tally ERP 9 XML Bridge (`tally_bridge.py`):** Automatically converts approved Purchase Orders, matched Invoices, and Vendor Masters into official Tally XML format for 1-click import into Tally.
- **Executive Spend Intelligence & Pareto ABC Analysis (`spend_analytics.py`):** Calculates statistical 80/20 ABC spend classification, departmental outlay distribution, and commercial negotiation savings metrics.
- **Automated Multi-Sheet Excel Workbooks (`excel_reports.py`):** Generates styled multi-tab Excel workbooks containing PR registers, PO registers, 3-way match summaries, and vendor directories.
- **Bulk CSV Importer (`bulk_importer.py`):** High-speed batch importer with built-in 15-digit GSTIN algorithmic checksum validation and 10-digit PAN derivation.
- **Python Programmatic SDK (`procure_sdk.py`):** REST API client library for custom ETL pipelines and Python scripts.

### 3. ☕ Java Enterprise SAP RFC & Batch Processor (`java/`)
- **SAP ERP RFC / BAPI Bridge (`ProcureSapBridge.java`):**
  - **Material Master Sync:** Reads SAP Material Master (MARA/MAKT) and syncs into ProcureLocal Item Catalog.
  - **PO Creation:** Translates ProcureLocal approved purchase orders into SAP `BAPI_PO_CREATE1` calls with G/L accounts and Cost Center allocation.
  - **Asset Master Capitalization:** Posts capitalized factory asset tags and OEM serial numbers into SAP Fixed Assets (`BAPI_FIXEDASSET_CREATE`).
- **High-Throughput Batch Processor (`ProcureBatchProcessor.java`):**
  - Multi-threaded batch validator computing SHA-256 cryptographic audit digests across all Document Vault files to verify zero tampering under SOX/ISO standards.
- **Runner Script (`tools/run-java-bridge.bat`):** 1-click script to compile and launch the Java SAP Bridge.

### 4. 🟢 Node.js 22 LTS Embedded SQLite Core Engine
- High-concurrency transaction core operating with native embedded SQLite (`node:sqlite`) in Write-Ahead-Logging (WAL) mode.
- Serves the Single-Page Application (SPA) studio to dozens of concurrent client workstations with microsecond response times.
- Zero external `npm` dependencies for complete supply-chain security and air-gapped immunity.

---

## 🚀 Key Enterprise Modules & Core Capabilities

### 1. Requisitions & Purchase Indents (PR Management)
- **Multi-Department & Cost Center Routing:** Supports Department, Plant Location, Priority (*Normal / Urgent / Critical*), Cost Centre (e.g. `PACCO100`), and GL Account codes (e.g. `4258600027`).
- **Revenue vs. Capex Classification:**
  - **Revenue Indents:** Consumables, routine maintenance, operational spares, and services subject to standard commercial bidding.
  - **Capex Indents:** Machinery, IT infrastructure, plant automation, and fixed asset procurement governed by formal corporate sanction memos and CITPC compliance.

---

### 2. Multi-Round Quotations & Mandatory Negotiation Audit Trail
- **Round 1 (Initial Vendor Quotations):** Record commercial quotations with reference numbers, quotation dates, payment terms, delivery timelines, and warranty terms. Attach both Commercial Quotation PDF and RFQ Email correspondence directly.
- **Round 2 (Final Revised Quotations & 100% Vendor Compliance Policy):**
  - **Mandatory Vendor Revision Enforcement:** Enforces that **all vendors** who submitted Round 1 initial bids must submit a Round 2 Final Revised Quote before the requisition can advance.
  - **Real-Time Compliance Alert Banner:** Prominently alerts indenter and commercial teams if any Round 1 vendor is pending final quotes.
  - **Automated Rate Pre-Filling:** Automatically pre-populates Round 1 unit rates and GST for seamless revision.
- **Quick Vendor Registration (`＋ Create New Vendor`):** Allows commercial buyers to add and register a new vendor on-the-fly directly inside the quotation entry screen without discarding draft line items.

---

### 3. Commercial Comparative Statement Matrix (CST / CS Sheet)
- **Side-by-Side Evaluation Matrix:** Complete line-by-line commercial comparison displaying Basic Unit Rates, GST %, Freight, Landed Cost per Unit, and Total Extended Landed Outlay.
- **Automated Ranking (L1 / L2 / L3):** Automatic determination of lowest landed cost bidder (L1) across all lines with percentage variance calculations for L2/L3 bidders.
- **Procurement Negotiation Savings Tracker:** Automatically calculates and displays real commercial savings: **Round 1 Initial L1 vs. Final Negotiated L1** in both Indian Rupees (₹) and percentage savings (%).
- **Executive Landscape CST Printout (`/api/procs/:id/cst/print`):** 1-click printable landscape comparative statement.

---

### 4. Corporate Sanction Logic Note & Selection Memo
- **Standard Corporate Executive Layout:** Standard A4 memo format matching corporate executive specifications (HOD sanction blocks, Background, Technical Scope, Nature of Work checklist, Budget Heads, Cash Flow, and Indenter Signatures).
- **Interactive Vendor Selection & Commercial Allocation Card:** Displays comparative table of all quoting vendors with commercial rank (L1, L2, L3), total landed cost, and quote dates.
- **Standard Statutory Selection Justifications:** L1 Lowest Bidder, Technically Superior OEM, Sole Proprietary OEM, Shortest Lead Time, Plant Standardization, Client Specified Brand.
- **Live A4 Sheet Preview & High-Fidelity PDF Print (`/api/procs/:id/logic/print`).**

---

### 5. Statutory & Enterprise Forms Center (Plant Governance)
Dedicated **"Forms & Formats"** Hub accessible directly from the main sidebar navigation:
- **Never-Empty Plant Standard Form Templates:** Access official corporate form templates anytime—even before creating an active requisition.
- **IT CITPC Note (IT Committee / Capex Sanction Memo):** Matches official corporate memo layouts (Title, Division, Indenter, Request Type, DMM Lead Time, Background, Business Need, Delivery Location Breakdown, Technical Evaluation, Capacity Augmentation checklist, CIO Approval block, and Technical Specifications Certification). Printable via `/api/forms/citpc-note/print`.
- **Project Completion & Handover Certificate:** Formal project handover memo for civil, electrical, mechanical, and IT infrastructure projects (`/api/forms/completion-cert/print`).
- **Commercial Fixed Asset (FAR) Handover Memo:** Inter-departmental capital expenditure FAR handover protocol (`/api/forms/far-handover/print`).

---

### 6. Vendor Master & Statutory Compliance Directory (India GST & MSME)
Enterprise-grade Vendor Directory with built-in statutory compliance intelligence:
- **Comprehensive Vendor Profiles:** Stores legal entity business name, contact persons, phone numbers, email addresses, street address, city, state, postal PIN code, and star performance ratings.
- **Smart GSTIN & Auto-PAN Derivation:**
  - Real-time detection of Indian State from the 2-digit GST state code (e.g. `27` -> Maharashtra, `29` -> Karnataka, `24` -> Gujarat).
  - Automatic extraction of the 10-digit PAN Card Number from characters 3–12 of the GSTIN.
  - Supports unregistered vendors and local retail contractors without throwing validation errors.
- **MSME / Udyam Enterprise Classification:** Micro, Small, Medium, and Large Enterprise designations with official Udyam Registration Number tracking.
- **Banking Coordinates & Commercial Terms:** Bank Name, Account Number, IFSC code, and standard payment terms (e.g. 30 days net, 15 days, 45 days MSME statutory, Advance).
- **Vendor Track Record:** Comprehensive order history showing all past requisitions and purchase orders awarded to each vendor.

---

### 7. Enterprise Document Vault & Universal Document Viewer
Centralized permanent repository for all procurement proofs, quotations, and commercial correspondence:
- **Universal In-App Document Viewer (`openDocViewer`):**
  - High-fidelity preview modal rendering PDFs directly using dual `<object>` and `<iframe>` technology.
  - In-app preview for scan images (PNG, JPG, WEBP, SVG) and HTML documents.
  - One-click **"Download File"**, **"Full Window"**, and **"Print Document"** options.
- **Requisition Overview Quick Documents Bar:** Every requisition's main overview page features a prominent **"📎 Attached Requisition Documents"** card showing original file names, category badges, and instant `👁️ View` and `📥 Download` buttons.
- **Modernized Requisition Document Repository Subtab (`setTab('dc')`):** Full rich table featuring file type icons, original file names, storage codes, category tags, vendor names, upload timestamp/user, and direct action buttons.
- **Direct Requisition Navigation:** One-click jump button (`🔗`) in the Document Vault opens the originating requisition immediately.

---

### 8. Official Purchase Orders & Service Contracts (PO / SO Generation)
- **GST Legal PO / SO Documents:** Generates statutory, audit-compliant Purchase Orders and Service Contracts with company billing & dispatch addresses, vendor GSTIN, HSN/SAC codes, and tax breakdowns.
- **Indian Rupee Words Conversion:** Automatically converts total net PO value to formal words.
- **SAP / ERP PO Linking:** Record and link official SAP or legacy ERP PO numbers and attach scanned copies.
- **Document Deduplication:** Prevents accidental duplicate uploads of the same PO document.

---

### 9. Goods Receipt Note (GRN / Store Inward & Quality Inspection)
- **Store Material Inward Recording:** Log material receipt dates, vendor delivery challan (DC) numbers, transporter details, vehicle numbers, and physical warehouse/bin locations.
- **3-Way Quantity Inspection:** Record **Received Qty, Accepted Qty, and Rejected Qty** with formal inspection classifications (`Accepted`, `Accepted with Deviation`, `Rejected`).
- **Store Inward Slips (`/api/grns/:id/print`):** Printable Store Inward reports.

---

### 10. Factory Fixed Asset Register & Plant Capitalization (SAP FI-AA Equivalence)
- **Zero-Duplicate Data Integrity (SAP Code & OEM Serial No):**
  - **SAP Asset Code (Asset Tag):** Uniquely identifies each physical piece of equipment in the factory. Strict database-level uniqueness prevents duplicate SAP codes.
  - **OEM Serial Number:** Strict uniqueness verification blocks duplicate serial numbers across all factory records, preventing ghost assets or double-capitalization.
- **Industrial Thermal Barcode Tag Labels (`/api/assets/:id/print`):** Formatted industrial label generator ready for thermal barcode sticker printers with Code128 barcodes.
- **Dedicated Post-PO/SO SAP Code & Serial Number Print (`/api/pos/:id/sap-serial-print` & `/api/procs/:id/sap-serial-print`):** Once a Purchase Order (PO) or Service Order (SO) is completed, generates a dedicated equipment sticker/slip that prints **ONLY** the **SAP Code** and **OEM Serial Number** with scannable Code 39 vector barcodes. Omits all prices, vendor bank details, and contract terms so physical equipment labels remain 100% clean and compliant.

---

### 11. 3-Way Matching & Invoicing Engine (SAP MIRO Equivalence)
- **Automated 3-Way Reconciliation:** Reconciles **Purchase Order vs. GRN Store Inward vs. Vendor Tax Invoice**.
- **Automated Discrepancy Detection:** Highlights reconciliation status (`MATCHED`, `QTY_MISMATCH`, `PRICE_MISMATCH`, `PENDING_GRN`).
- **Payment Release Tracker:** Record payment vouchers, bank UTR numbers, cheque references, payment release dates, and paid status.

---

### 12. Executive 360° Universal Record Search & Dashboard BI
Instant, cross-database search engine positioned directly on the Executive Dashboard:
- **Global Keyboard Shortcut (`Ctrl + K`):** Instant focus into the 360° universal search from any screen in the studio.
- **Standard Search Criteria Filters:** 1-click category filter pills for **All**, **🏷️ SAP Code**, **🔢 Serial No**, **📦 Item**, **🧾 Invoice**, **📑 PO**, and **🏢 Vendor** with clean, standardized search keywords.
- **Accurate Financial Valuation:** Real-time analytics pipeline intelligently values open requisitions using indenter estimated budget (`p.est`) when final quotes are in progress, providing accurate, non-zero total spend visibility.
- **Complete 360° Requisition Dossier Cards:** Displays all connected line items, purchase orders, GRN inspection slips, vendor invoices, payment status, and capitalized plant equipment in one unified view.

---

### 13. Strict Audit Lock & SOX / ISO 9001 Governance
- **Automated Audit Freeze (`Confirm & Complete Requisition ✔`):** Once a requisition reaches completion, it locks permanently. All direct modification buttons are disabled to prevent unauthorized alterations.
- **Role-Based Admin Unlock Workflow:** Standard users cannot modify completed requisitions. To request changes, users submit a formal **Unlock Request** stating business justification for Admin review.

---

## 🛠️ Quick Start & Multi-System Launch Guide

### 1. Launching ProcureLocal (1-Click Standalone)
1. Double-click **`ProcureLocal.exe`** on any workstation.
2. The application opens directly to the Executive Procurement Studio in 1 step (zero modal dialogs or IP prompts).
3. **Default Admin Login:**
   - **Username:** `admin`
   - **Password:** `admin123`

### 2. Pointing to Remote Shared Database (NAS / Windows Share)
To share one central database and document vault across all office PCs:
- **From Application UI:**
  1. Open `ProcureLocal` -> Click **`Settings & Audit`** in the left menu.
  2. Locate the **"📁 Remote Shared Database (NAS / Windows Share) & Standalone Deployment"** section.
  3. Enter your central Windows share path (e.g. `\\Server\SharedData\ProcureDB` or mapped drive `Z:\ProcureDB`).
  4. Click **"🔄 Test Read/Write Access"** to verify connectivity, then click **"💾 Save Remote Share Path"**.
- **From Command Line:**
  - Run: `ProcureLocal.exe --set-db "\\Server\SharedData\ProcureDB"`
  - Or run: `ProcureLocal.exe --setup` to open the Network Folder Browser GUI.
- **From config.json:**
  - Simply set `"dataDir": "\\\\Server\\SharedData\\ProcureDB"` in `config.json`.

### 3. Running Polyglot Tools
- **Python Spend Analytics:** Run `ProcureLocal.exe --python spend_analytics.py` or double-click `run-python-cli.bat`.
- **TallyPrime XML Sync:** Run `ProcureLocal.exe --python tally_bridge.py`.
- **Java SAP Bridge:** Double-click `tools/run-java-bridge.bat` or run `ProcureLocal.exe --java`.

---

## 📁 Storage & Folder Architecture

```
ProcureLocal/
├── ProcureLocal.exe                   All-In-One Desktop Executable (C# Launcher & Spooler)
├── server.js                          Core Enterprise REST Server (Node.js 22 LTS)
├── public/
│   └── index.html                     Single-Page Enterprise ERP Studio UI
├── DB/                                ONE Central Data Store
│   ├── procure.db                     Native SQLite 3 Database (WAL mode enabled)
│   ├── documents/                     Document Vault (Quotations, POs, Invoices, Formats)
│   └── backups/                       Automated snapshots & manual database exports
├── python/                            Python 3 Data Intelligence Suite
│   ├── tally_bridge.py                Tally ERP 9 / TallyPrime XML export generator
│   ├── spend_analytics.py             Pareto ABC analysis & spend intelligence
│   ├── excel_reports.py               Multi-sheet formatted Excel workbook generator
│   ├── bulk_importer.py               Bulk CSV importer for vendors & item master
│   └── procure_sdk.py                 Python programmatic REST SDK
├── java/                              Java Enterprise SAP & Batch Bridge
│   └── com/procurelocal/
│       ├── ProcureSapBridge.java      SAP RFC / BAPI_PO_CREATE1 & Asset Master Connector
│       └── ProcureBatchProcessor.java Multi-threaded batch audit & SHA-256 engine
└── tools/
    ├── ProcureLocal.cs                C# Desktop Source Code
    ├── run-java-bridge.bat            Java SAP Bridge Execution Script
    └── stop-server.bat                Graceful Process Shutdown Script
```

---

*ProcureLocal Enterprise Edition — Engineered for Manufacturing Excellence, Multi-System Plant Operations & Corporate Procurement Governance.*
