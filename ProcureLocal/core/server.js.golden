// ProcureLocal v3 Enterprise Edition – Zero-dependency Enterprise Procurement Server (Node 22 LTS)
// Features: Requisitions, Comparative Statement (CST), Logic Note, PO/SO Generation, GRN/Inward, 3-Way Matching, Invoicing, Vendor Scorecard & Master Data
const http = require('http'), fs = require('fs'), path = require('path'), crypto = require('crypto');
const { DatabaseSync } = require('node:sqlite');

let cfg = { dataDir: path.join(__dirname, 'DB'), port: 3002, host: '0.0.0.0', remoteBackupDir: '' };
try { Object.assign(cfg, JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'))); } catch {}
if (process.env.DATA_DIR) cfg.dataDir = process.env.DATA_DIR;
if (process.env.REMOTE_BACKUP_DIR) cfg.remoteBackupDir = process.env.REMOTE_BACKUP_DIR;

let DD;
try {
  let targetDir = path.isAbsolute(cfg.dataDir) ? path.resolve(cfg.dataDir) : path.resolve(__dirname, cfg.dataDir);
  fs.mkdirSync(targetDir, { recursive: true });
  DD = targetDir;
} catch (e) {
  console.warn("Notice: Configured storage path could not be accessed (" + e.message + "). Defaulting to local ./DB");
  DD = path.join(__dirname, 'DB');
  fs.mkdirSync(DD, { recursive: true });
}
const DOCS = path.join(DD, 'documents');
const BAK = path.join(DD, 'backups');
const DBF = path.join(DD, 'procure.db');
[DD, DOCS, BAK].forEach(d => {
  try { fs.mkdirSync(d, { recursive: true }); } catch {}
});

let lastUiPing = Date.now();
let uiConnected = false;
const SERVER_START_TIME = Date.now();

const ROLES = {
  admin: 'Administrator (Full Access & Settings)',
  user: 'Procurement Specialist (Create & Manage Requests)',
  finance: 'Finance & Accounts (Invoices, GRN & 3-Way Matching)',
  approver: 'HOD / Approver (Approvals & Reviews)',
  viewer: 'Viewer (Read Only Access)'
};

const FLOW = {
  revenue: ['quotations', 'negotiation', 'final', 'pr', 'logic', 'hod', 'commercial', 'approvals', 'order', 'completed'],
  capex: ['quotations', 'pr', 'logic', 'hod', 'commercial', 'approvals', 'order', 'completed']
};

const DEF = {
  // 1. Company Master & Statutory Profile
  app_name: 'MIS Procurement',
  company: 'Apex Enterprise Solutions India Pvt Ltd',
  company_cin: 'U72900MH2020PTC123456',
  company_address: 'Plot No. 42, Sector 8, Industrial Corridor',
  company_city: 'Mumbai',
  company_state: 'Maharashtra',
  company_pincode: '400076',
  company_gst: '27AABCA1234F1Z9',
  company_pan: 'AABCA1234F',
  company_phone: '+91 22 6123 4567',
  company_email: 'procurement@apex-india.com',
  company_website: 'https://apex-india.com',
  company_bank_name: 'State Bank of India',
  company_bank_ac: '30495830291',
  company_bank_ifsc: 'SBIN0001234',
  company_bank_branch: 'Corporate Finance Branch, Mumbai',
  logo: '',

  // 2. Document Numbering Prefixes & Financial Year
  prefix: 'PRC',
  po_prefix: 'PO',
  so_prefix: 'SO',
  grn_prefix: 'GRN',
  asset_prefix: 'AST',
  fy_format: 'YYYY',

  // 3. Procurement Policy, Tolerances & Compliance Thresholds
  tiers: [
    { name: 'Tier 1 - Major Procurement / Open Tender', min: 100000, vendors: 3, descr: 'Minimum 3 competitive quotations mandatory for audit compliance' },
    { name: 'Tier 2 - Mid-Value Procurement / RFQ', min: 50000, vendors: 2, descr: 'Minimum 2 competitive quotations required' },
    { name: 'Tier 3 - Petty / Spot Procurement', min: 0, vendors: 1, descr: 'Single quotation acceptable for low-value purchases' }
  ],
  policy_rules: [
    { title: 'Quotation Expiry Policy', rule: 'Quotation validity period cannot exceed 90 days. Expired quotes cannot be considered for CST evaluation.' },
    { title: 'MSME Statutory Preference', rule: 'Vendors registered under MSME (Udyam) must be prioritized with mandatory 45-day payment cycle.' },
    { title: 'GST Active Status & E-Invoicing', rule: 'Active 15-digit GSTIN and HSN/SAC code mandatory for all PO items.' },
    { title: 'Single Quotation / OEM Proprietary Waiver', rule: 'Single quotation procurement requires explicit technical justification and HOD approval.' }
  ],
  quoteMaxAgeDays: 90,
  alertDays: 15,
  match_variance_pct: 0,
  match_qty_variance_pct: 0,
  enforce_msme: true,
  enforce_hsn: true,

  // 4. Workflow, Signatories & Standard Terms
  approvers: [
    { name: 'Dipankar', desig: 'Head of Department' },
    { name: 'Vipul', desig: 'General Manager - Commercial' },
    { name: 'Vamsi', desig: 'Assistant Manager - Finance' },
    { name: 'Suresh Kumar', desig: 'Director - Operations' }
  ],
  default_indenter_title: 'Signature of Indenter',
  default_hod_title: 'Head of Department',
  default_payment_terms: '30 days from receipt and technical acceptance of material (GRN)',
  default_delivery_terms: 'Door Delivery / FOR Destination Store inclusive of freight & transit insurance',
  backupHours: 12,
  backupKeep: 14,
  backupDocs: true,
  po_terms: `1. Material must be supplied strictly in accordance with approved technical specifications, make, and brand.
2. Prices are firm and inclusive of packing, forwarding, and insurance unless explicitly stated otherwise.
3. Delivery to be completed on or before the agreed delivery date indicated in this Purchase Order.
4. Goods are subject to physical verification, quantity check, and technical inspection at our receiving store.
5. Invoicing: Tax Invoice in triplicate mentioning PO Number, HSN/SAC codes, and GST breakdown is mandatory.
6. Payment Terms: Within 30 days from physical receipt, verification, and GRN inwarding at store.
7. Statutory: All taxes, GST, and e-way bill compliance as applicable under Indian GST Act.
8. Warranty: Standard manufacturer warranty of minimum 12 months from the date of commissioning or 18 months from delivery.
9. Disputes, if any, shall be subject to the exclusive jurisdiction of competent courts in Mumbai.`
};

let db;
function open() {
  db = new DatabaseSync(DBF);
  try {
    db.exec(`
      PRAGMA busy_timeout = 15000;
      PRAGMA synchronous = NORMAL;
      PRAGMA foreign_keys = ON;
    `);
  } catch {}
  db.exec(`
    create table if not exists users(id integer primary key,username text unique,name text,email text,role text,pw text,active int default 1);
    create table if not exists vendors(id integer primary key,name text,address text,gst text,contact text,phone text,email text);
    create table if not exists proc(id integer primary key,code text unique,type text,kind text,title text,dept text,location text,est real,stage text default 'quotations',business_req text,tech text,final_reason text,citpc_ref text,citpc_date text,citpc_vendor text,pr_no text,pr_date text,hod_date text,comm_date text,notes text,requester text,created text,updated text,nature_text text,nature_ticks text,cost_centre text,gl_code text,budget_available text,cash_flow text,budget_type text,io_number text,io_gl text,qual_eval text);
    create table if not exists items(id integer primary key,proc_id int,name text,descr text,model text,qty real,unit text,hsn text,citpc_rate real,last_date text,final_vendor_id int,final_rate real,final_gst real,sap_no text,sap_date text);
    create table if not exists quotes(id integer primary key,proc_id int,type text,vendor_id int,vendor text,address text,gst text,recipient text,qdate text,delivery text,doc_id int,ref text);
    create table if not exists qitems(id integer primary key,quote_id int,item_id int,rate real,gst real);
    create table if not exists comms(id integer primary key,proc_id int,at text,by text,kind text,vendor text,text text);
    create table if not exists docs(id integer primary key,proc_id int,category text,vendor text,name text,orig text,path text,at text,by text);
    create table if not exists approvals(id integer primary key,proc_id int,seq int,name text,desig text,date text,remark text,by text);
    create table if not exists audit(id integer primary key,at text,user text,proc_id int,act text);
    create table if not exists settings(k text primary key,v text);

    -- Enterprise extensions:
    create table if not exists item_master(id integer primary key,code text unique,name text,descr text,category text,unit text,hsn text,citpc_rate real,created text);
    create table if not exists pos(id integer primary key,proc_id int,po_no text unique,po_date text,vendor_id int,vendor_name text,total_basic real,total_gst real,total_landed real,payment_terms text,delivery_terms text,billing_address text,delivery_address text,status text default 'Issued',terms_text text,created_by text,created_at text);
    create table if not exists po_items(id integer primary key,po_id int,item_id int,name text,descr text,qty real,unit text,rate real,gst real,hsn text,total real);
    create table if not exists grns(id integer primary key,proc_id int,po_id int,grn_no text unique,grn_date text,challan_no text,challan_date text,vehicle_no text,received_by text,remarks text,created_at text);
    create table if not exists grn_items(id integer primary key,grn_id int,item_id int,po_item_id int,received_qty real,accepted_qty real,rejected_qty real,rejection_reason text);
    create table if not exists invoices(id integer primary key,proc_id int,po_id int,invoice_no text,invoice_date text,amount real,gst_amount real,total_amount real,match_status text,payment_status text default 'Unpaid',payment_date text,utr_no text,doc_id int,remarks text,created_at text);
    create table if not exists assets(id integer primary key,proc_id int,po_id int,item_id int,asset_code text unique,asset_name text,category text,capitalization_date text,commissioning_date text,put_to_use_date text,plant_location text,custodian text,serial_no text,cost real,warranty_expiry text,status text default 'Capitalized & In-Service',remarks text,created_at text);
    create table if not exists unlock_requests(id integer primary key,proc_id int,req_code text,requested_by text,requested_at text,reason text,status text default 'pending',reviewed_by text,reviewed_at text,review_remarks text);
  `);

  // Non-destructive schema column enhancements
  const alterations = [
    ['proc', 'nature_text'], ['proc', 'nature_ticks'], ['proc', 'cost_centre'], ['proc', 'gl_code'],
    ['proc', 'budget_available'], ['proc', 'cash_flow'], ['proc', 'budget_type'], ['proc', 'io_number'],
    ['proc', 'io_gl'], ['proc', 'qual_eval'], ['proc', 'priority'], ['proc', 'po_no'], ['proc', 'po_date'],
    ['proc', 'grn_status'], ['proc', 'invoice_status'], ['proc', 'payment_terms'], ['proc', 'delivery_terms'],
    ['proc', 'asset_status'], ['proc', 'asset_code'], ['proc', 'capitalization_date'],
    ['proc', 'commissioning_date'], ['proc', 'received_date'], ['proc', 'plant_location'],
    ['proc', 'custodian'], ['proc', 'closed_at'], ['proc', 'closed_by'], ['proc', 'close_remarks'],
    ['proc', 'is_locked'], ['proc', 'unlock_status'], ['proc', 'unlock_reason'],
    ['proc', 'unlock_requested_by'], ['proc', 'unlock_requested_at'],
    ['proc', 'unlock_approved_by'], ['proc', 'unlock_approved_at'],
    ['proc', 'awarded_vendor_id'], ['proc', 'awarded_vendor_name'], ['proc', 'selection_basis'], ['proc', 'completion_cert'], ['proc', 'citpc_note'],
    ['quotes', 'ref'], ['quotes', 'delivery_days'], ['quotes', 'payment_terms'], ['quotes', 'warranty'], ['quotes', 'freight'], ['quotes', 'mail_doc_id'],
    ['vendors', 'pan'], ['vendors', 'msme_type'], ['vendors', 'msme_no'], ['vendors', 'bank_name'],
    ['vendors', 'bank_ac'], ['vendors', 'ifsc'], ['vendors', 'payment_terms'], ['vendors', 'rating'],
    ['vendors', 'city'], ['vendors', 'state'], ['vendors', 'pincode'],
    ['items', 'received_qty'], ['items', 'accepted_qty'], ['items', 'asset_code'], ['items', 'capitalization_date'],
    ['grns', 'inspected_by'], ['grns', 'inspection_status'], ['grns', 'store_location'],
    ['pos', 'doc_id'], ['pos', 'is_uploaded'], ['pos', 'remarks']
  ];
  for (const [t, c] of alterations) {
    try { db.exec(`alter table ${t} add column ${c} text`); } catch {}
  }

  for (const [k, v] of Object.entries(DEF)) {
    db.prepare('insert or ignore into settings values(?,?)').run(k, JSON.stringify(v));
  }
  if (!db.prepare('select 1 from users').get()) {
    db.prepare('insert into users(username,name,email,role,pw) values(?,?,?,?,?)')
      .run('admin', 'System Administrator', 'admin@apex-india.com', 'admin', hash('admin123'));
  }

  // Automatic cleanup of historical duplicate docs (keeps the latest document record per proc_id, category, and orig)
  try {
    const dupDocs = db.prepare(`
      select id, proc_id, category, orig, path from docs
      where id not in (
        select max(id) from docs group by proc_id, category, lower(orig)
      ) and orig is not null and trim(orig) != ''
    `).all();
    for (const d of dupDocs) {
      const isLinkedPo = db.prepare('select 1 from pos where doc_id = ?').get(d.id);
      if (!isLinkedPo) {
        try {
          const fp = path.join(DD, d.path);
          if (fs.existsSync(fp)) fs.unlinkSync(fp);
        } catch {}
        db.prepare('delete from docs where id = ?').run(d.id);
      }
    }
  } catch {}
}
open();

// ---- crypto & auth ----
function hash(p) {
  const s = crypto.randomBytes(12).toString('hex');
  return s + ':' + crypto.scryptSync(p, s, 32).toString('hex');
}
function chk(p, h) {
  const [s, x] = h.split(':');
  return crypto.timingSafeEqual(crypto.scryptSync(p, s, 32), Buffer.from(x, 'hex'));
}
const S = () => {
  const o = { ...DEF };
  for (const r of db.prepare('select * from settings').all()) {
    try { o[r.k] = JSON.parse(r.v); } catch { o[r.k] = r.v; }
  }
  return o;
};
const now = () => new Date().toISOString();
const today = () => now().slice(0, 10);
const slug = s => String(s || 'NA').replace(/[^\w-]+/g, '_').slice(0, 40).replace(/^[._\-]+|[._\-]+$/g, '') || 'NA';
const normParam = x => {
  if (x === undefined || x === null) return null;
  if (typeof x === 'boolean') return x ? 1 : 0;
  if (typeof x === 'number') return Number.isNaN(x) ? null : x;
  if (x instanceof Date) return x.toISOString();
  return x;
};
const one = (q, ...a) => db.prepare(q).get(...a.map(normParam));
const all = (q, ...a) => db.prepare(q).all(...a.map(normParam));
const run = (q, ...a) => db.prepare(q).run(...a.map(normParam));
const audit = (u, pid, act) => run('insert into audit(at,user,proc_id,act) values(?,?,?,?)', now(), u ? u.username : 'system', pid || null, act);
const E = (m, c = 400) => Object.assign(new Error(m), { code: c });

// ---- Strict Security Authorization for Permanent Record Deletion (SOX / ISO Compliance) ----
function verifySecurityDelete(u, j, adm, entityName) {
  if (!adm) {
    throw E(`Security Authorization Failed: Only System Administrators can permanently delete ${entityName}.`, 403);
  }
  const confirm = String(j?.confirm || '').trim().toUpperCase();
  if (confirm !== 'DELETE') {
    throw E('Security Verification Failed: You must type "DELETE" to authorize permanent deletion.', 400);
  }
  const password = String(j?.password || '').trim();
  if (!password) {
    throw E('Security Verification Failed: Administrator password is required to authorize permanent deletion.', 403);
  }
  const uRec = one('select pw from users where id=?', u.id);
  if (!uRec || !chk(password, uRec.pw)) {
    throw E('Security Verification Failed: Incorrect Administrator password. Deletion unauthorized.', 403);
  }
}

const need = (p, s) => {
  if (p.type === 'capex') return 1;
  const tiers = Array.isArray(s.tiers) ? [...s.tiers].sort((a, b) => (b.min || 0) - (a.min || 0)) : [];
  for (const t of tiers) {
    if (p.est >= (t.min || 0)) return t.vendors || 1;
  }
  return 1;
};

// ---- Tamper-Proof Audit Lock & Permission Workflow Helpers ----
function isProcLocked(p) {
  if (!p) return false;
  return Boolean((p.stage === 'completed' || Number(p.is_locked) === 1) && p.unlock_status !== 'unlocked');
}

function checkProcNotLocked(p, u) {
  if (u === true) return; // internal system bypass only
  if (isProcLocked(p)) {
    throw E('This requisition is completed & locked for SOX/ISO audit compliance. Direct modifications are restricted. An Administrator must unlock it with a recorded reason before any edits.', 403);
  }
}

// ---- Robust Unique Sequence Generators (Collision Proof) ----
function getNextProcCode(prefix = 'PRC', fyFormat = 'YYYY') {
  const curYear = new Date().getFullYear();
  const yrStr = fyFormat === 'YYYY-YY' ? `${curYear}-${String(curYear + 1).slice(2)}` : String(curYear);
  const rows = all('select code from proc');
  let maxNum = 0;
  for (const r of rows) {
    if (!r.code) continue;
    const parts = r.code.split('-');
    if (parts.length >= 2) {
      const num = parseInt(parts[1], 10);
      if (!isNaN(num) && num > maxNum) maxNum = num;
    }
  }
  let nextSeq = Math.max(maxNum + 1, (one('select max(id) m from proc').m || 0) + 1);
  let candidate = `${prefix}-${String(nextSeq).padStart(4, '0')}-${yrStr}`;
  while (one('select 1 from proc where code = ?', candidate)) {
    nextSeq++;
    candidate = `${prefix}-${String(nextSeq).padStart(4, '0')}-${yrStr}`;
  }
  return candidate;
}

function getNextPoNo(poPrefix = 'PO') {
  const curYear = new Date().getFullYear();
  const rows = all('select po_no from pos');
  let maxNum = 0;
  for (const r of rows) {
    if (!r.po_no) continue;
    const parts = r.po_no.split('-');
    const num = parseInt(parts[parts.length - 1], 10);
    if (!isNaN(num) && num > maxNum) maxNum = num;
  }
  let nextSeq = Math.max(maxNum + 1, (one('select max(id) m from pos').m || 0) + 1);
  let candidate = `${poPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  while (one('select 1 from pos where po_no = ?', candidate)) {
    nextSeq++;
    candidate = `${poPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  }
  return candidate;
}

function getNextGrnNo(grnPrefix = 'GRN') {
  const curYear = new Date().getFullYear();
  const rows = all('select grn_no from grns');
  let maxNum = 0;
  for (const r of rows) {
    if (!r.grn_no) continue;
    const parts = r.grn_no.split('-');
    const num = parseInt(parts[parts.length - 1], 10);
    if (!isNaN(num) && num > maxNum) maxNum = num;
  }
  let nextSeq = Math.max(maxNum + 1, (one('select max(id) m from grns').m || 0) + 1);
  let candidate = `${grnPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  while (one('select 1 from grns where grn_no = ?', candidate)) {
    nextSeq++;
    candidate = `${grnPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  }
  return candidate;
}

function getNextAssetCode(assetPrefix = 'AST') {
  const curYear = new Date().getFullYear();
  const rows = all('select asset_code from assets');
  let maxNum = 0;
  for (const r of rows) {
    if (!r.asset_code) continue;
    const parts = r.asset_code.split('-');
    const num = parseInt(parts[parts.length - 1], 10);
    if (!isNaN(num) && num > maxNum) maxNum = num;
  }
  let nextSeq = Math.max(maxNum + 1, (one('select max(id) m from assets').m || 0) + 1);
  let candidate = `${assetPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  while (one('select 1 from assets where asset_code = ?', candidate)) {
    nextSeq++;
    candidate = `${assetPrefix}-${curYear}-${String(nextSeq).padStart(4, '0')}`;
  }
  return candidate;
}

// ---- Asset Uniqueness Validation (Prevents duplicate SAP Code & OEM Serial Numbers) ----
function validateAssetUniqueness(assetCode, serialNo, excludeAssetId = null) {
  // 1. Validate SAP Code (asset_code)
  if (assetCode) {
    const codeClean = String(assetCode).trim();
    if (codeClean) {
      const existingCode = excludeAssetId
        ? one('select id, asset_code, asset_name from assets where lower(asset_code) = lower(?) and id != ?', codeClean, excludeAssetId)
        : one('select id, asset_code, asset_name from assets where lower(asset_code) = lower(?)', codeClean);
      if (existingCode) {
        throw E(`Duplicate SAP Code: "${codeClean}" is already registered for asset "${existingCode.asset_name}" (ID: ${existingCode.id}). SAP Code must be unique across all plant records.`, 400);
      }
    }
  }

  // 2. Validate OEM Serial Number (serial_no)
  if (serialNo) {
    const snClean = String(serialNo).trim();
    const isGeneric = ['na', 'n/a', 'none', '—', '-', 'null', ''].includes(snClean.toLowerCase());
    if (snClean && !isGeneric) {
      const existingSn = excludeAssetId
        ? one('select id, asset_code, asset_name, serial_no from assets where lower(trim(serial_no)) = lower(?) and id != ?', snClean, excludeAssetId)
        : one('select id, asset_code, asset_name, serial_no from assets where lower(trim(serial_no)) = lower(?)', snClean);
      if (existingSn) {
        throw E(`Duplicate Serial Number: "${snClean}" is already registered for asset "${existingSn.asset_name}" (SAP Code: ${existingSn.asset_code}). Each equipment unit must have a unique OEM Serial Number.`, 400);
      }
    }
  }
}

// ---- number to words & currency format ----
function numToWordsINR(n) {
  n = Math.round(Number(n) || 0);
  if (n === 0) return 'Zero Rupees Only';
  const single = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
  function convert3(num) {
    let str = '';
    if (num >= 100) { str += single[Math.floor(num / 100)] + ' Hundred '; num %= 100; }
    if (num >= 20) { str += tens[Math.floor(num / 10)] + (num % 10 ? ' ' + single[num % 10] : ''); }
    else if (num > 0) { str += single[num]; }
    return str.trim();
  }
  let crore = Math.floor(n / 10000000); n %= 10000000;
  let lakh = Math.floor(n / 100000); n %= 100000;
  let thousand = Math.floor(n / 1000); n %= 1000;
  let rem = n;
  let res = '';
  if (crore) res += convert3(crore) + ' Crore ';
  if (lakh) res += convert3(lakh) + ' Lakh ';
  if (thousand) res += convert3(thousand) + ' Thousand ';
  if (rem) res += convert3(rem);
  return 'Indian Rupees ' + res.trim() + ' Only';
}

const money = n => '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const esc = t => String(t ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const nl = t => esc(t).replace(/\n/g, '<br>');
const gt = (r, g) => (Number(r) || 0) * (1 + (Number(g) || 0) / 100);
const dmy = d => {
  const x = String(d || '').slice(0, 10).split('-');
  return x.length === 3 ? `${x[2]}.${x[1]}.${x[0]}` : (d || '');
};

// ---- quotation validation ----
function checks(q, p, s, qi, items) {
  const l = x => String(x || '').trim().toLowerCase();
  const age = (Date.now() - new Date(q.qdate)) / 864e5;
  const rated = qi.filter(x => x.rate > 0);
  const cap = p.type === 'capex'
    ? rated.filter(x => {
        const it = items.find(i => i.id === x.item_id);
        return it && it.citpc_rate > 0 && x.rate > it.citpc_rate * 1.005;
      })
    : [];

  const c = [
    ['Addressed to ' + s.company, l(q.recipient) === l(s.company)],
    ['Vendor name & address', !!q.vendor && l(q.address).length > 4],
    ['GST number format (15 digits)', /^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(String(q.gst || '').toUpperCase())],
    ['Quotation date valid (not future, max ' + s.quoteMaxAgeDays + ' days old)', !!q.qdate && age >= -1 && age <= s.quoteMaxAgeDays],
    ['Delivery location matches', l(q.delivery) === l(p.location)],
    ['At least one item rated', rated.length > 0],
    ['Rates and GST % valid', rated.every(x => x.rate > 0 && x.gst >= 0 && x.gst <= 40)]
  ];
  if (p.type === 'capex') {
    c.push(['Rate within CITPC benchmark' + (cap.length ? ' (' + cap.length + ' item(s) higher)' : ''), cap.length === 0]);
  }
  return c;
}

function loadQuotes(p, s, items) {
  return all('select * from quotes where proc_id=? order by id', p.id).map(q => {
    const qi = all('select * from qitems where quote_id=?', q.id);
    const ch = checks(q, p, s, qi, items);
    const qDoc = q.doc_id ? one('select name, orig from docs where id=?', q.doc_id) : null;
    const mDoc = q.mail_doc_id ? one('select name, orig from docs where id=?', q.mail_doc_id) : null;
    return {
      ...q,
      doc_name: qDoc?.orig || qDoc?.name || '',
      mail_doc_name: mDoc?.orig || mDoc?.name || '',
      qitems: qi,
      checks: ch,
      valid: ch.every(c => c[1])
    };
  });
}
const validOf = (qs, type) => qs.filter(q => q.type === type && q.valid);
const vendorsOf = l => new Set(l.map(q => q.vendor_id || q.vendor.toLowerCase())).size;
const covered = (l, items) => items.filter(i => !l.some(q => q.qitems.some(x => x.item_id === i.id && x.rate > 0)));

function pendingWith(p) {
  const a = one('select name from approvals where proc_id=? and date is null order by seq', p.id);
  return {
    quotations: 'You – quotations',
    negotiation: 'You – negotiation',
    final: 'You – final quotation',
    pr: 'You – create PR in SAP',
    logic: 'You – logic note',
    hod: 'HOD sign',
    commercial: 'You – submit to commercial',
    approvals: a ? a.name : '—',
    order: 'SAP PO/SO number',
    completed: null
  }[p.stage];
}

// ---- files management ----
function saveDoc(p, category, vendor, orig, buf, u) {
  const ext = path.extname(orig) || '';
  const dir = path.join(DOCS, p.code, category);
  fs.mkdirSync(dir, { recursive: true });

  // If saving an official Logic Note, Completion Certificate, or CITPC Note, remove previous draft versions for this PR so Document Vault stays clean
  if (category === 'LogicNote' || category === 'CompletionCert' || category === 'CITPCNote') {
    const existingOldDocs = all("select * from docs where proc_id=? and category=?", p.id, category);
    for (const oldDoc of existingOldDocs) {
      try {
        const oldFp = path.join(DD, oldDoc.path);
        if (fs.existsSync(oldFp)) fs.unlinkSync(oldFp);
      } catch {}
    }
    run("delete from docs where proc_id=? and category=?", p.id, category);
  }

  // Clean up any unlinked / abandoned PurchaseOrder draft uploads for this PR so Document Vault has no duplicates
  if (category === 'PurchaseOrder') {
    const unlinkedOldDocs = all("select * from docs where proc_id=? and category='PurchaseOrder' and id not in (select cast(doc_id as integer) from pos where proc_id=? and doc_id is not null)", p.id, p.id);
    for (const oldDoc of unlinkedOldDocs) {
      try {
        const oldFp = path.join(DD, oldDoc.path);
        if (fs.existsSync(oldFp)) fs.unlinkSync(oldFp);
      } catch {}
      run("delete from docs where id=?", oldDoc.id);
    }
  }

  // Deduplication: If a document with the same original filename already exists for this PR and category,
  // update/replace the file rather than creating duplicate _1, _2, _3 entries
  const existingSameDoc = one("select * from docs where proc_id=? and category=? and lower(orig) = lower(?)", p.id, category, orig);
  if (existingSameDoc) {
    try {
      const targetFp = path.join(DD, existingSameDoc.path);
      fs.mkdirSync(path.dirname(targetFp), { recursive: true });
      fs.writeFileSync(targetFp, buf);
      if (vendor) {
        const vd = path.join(DOCS, '_Vendors', slug(vendor), p.code);
        fs.mkdirSync(vd, { recursive: true });
        fs.copyFileSync(targetFp, path.join(vd, existingSameDoc.name));
      }
      run("update docs set vendor=?, at=?, by=? where id=?", vendor || '', now(), u ? u.username : 'system', existingSameDoc.id);
      audit(u, p.id, `Document refreshed/replaced: ${category}/${existingSameDoc.name}`);
      return Number(existingSameDoc.id);
    } catch {}
  }

  const n = all('select 1 from docs where proc_id=? and category=?', p.id, category).length + 1;
  const name = category === 'LogicNote'
    ? `${p.code}_LogicNote${ext}`
    : (category === 'CompletionCert'
        ? `${p.code}_Completion_Certificate${ext}`
        : (category === 'CITPCNote'
            ? `${p.code}_CITPC_Note${ext}`
            : `${p.code}_${category}_${slug(vendor)}_${today()}_${n}${ext}`));
  const fp = path.join(dir, name);
  fs.writeFileSync(fp, buf);
  if (vendor) {
    const vd = path.join(DOCS, '_Vendors', slug(vendor), p.code);
    fs.mkdirSync(vd, { recursive: true });
    fs.copyFileSync(fp, path.join(vd, name));
  }
  const r = run('insert into docs(proc_id,category,vendor,name,orig,path,at,by) values(?,?,?,?,?,?,?,?)',
    p.id, category, vendor || '', name, orig, path.relative(DD, fp), now(), u ? u.username : 'system');
  audit(u, p.id, `Document stored: ${category}/${name}`);
  return Number(r.lastInsertRowid);
}

// ---- Comparative Statement (CST) Data Calculation ----
function buildCstData(p, s, items, qs) {
  const qtype = p.type === 'capex' ? 'initial' : 'final';
  const initialQuotes = validOf(qs, 'initial');
  const compareQuotes = validOf(qs, qtype);

  // Vendor summary matrix
  const vendorSummaries = compareQuotes.map(q => {
    let basicTotal = 0;
    let gstTotal = 0;
    let landedTotal = 0;
    let itemsCovered = 0;

    const itemRates = items.map(item => {
      const qItem = q.qitems.find(qi => qi.item_id === item.id && qi.rate > 0);
      if (qItem) {
        const itemBasic = qItem.rate * item.qty;
        const itemGst = itemBasic * (qItem.gst / 100);
        const itemLanded = itemBasic + itemGst;
        basicTotal += itemBasic;
        gstTotal += itemGst;
        landedTotal += itemLanded;
        itemsCovered++;
        return {
          item_id: item.id,
          rate: qItem.rate,
          gst: qItem.gst,
          basic: itemBasic,
          landed: itemLanded,
          unit_landed: gt(qItem.rate, qItem.gst)
        };
      }
      return { item_id: item.id, rate: null, gst: null, basic: 0, landed: 0, unit_landed: 0 };
    });

    return {
      quote_id: q.id,
      vendor_id: q.vendor_id,
      vendor: q.vendor,
      ref: q.ref,
      qdate: q.qdate,
      delivery_days: q.delivery_days || 'Immediate',
      payment_terms: q.payment_terms || '30 days',
      basicTotal,
      gstTotal,
      landedTotal,
      itemsCovered,
      isFullQuote: itemsCovered === items.length,
      itemRates
    };
  });

  // Rank vendors with full quotes
  const fullQuotes = vendorSummaries.filter(v => v.isFullQuote).sort((a, b) => a.landedTotal - b.landedTotal);
  vendorSummaries.forEach(v => {
    if (v.isFullQuote) {
      const rankIdx = fullQuotes.findIndex(fq => fq.quote_id === v.quote_id);
      v.rank = 'L' + (rankIdx + 1);
      v.varianceVsL1 = rankIdx > 0 && fullQuotes[0].landedTotal > 0
        ? (((v.landedTotal - fullQuotes[0].landedTotal) / fullQuotes[0].landedTotal) * 100).toFixed(1) + '%'
        : '0%';
    } else {
      v.rank = `Partial (${v.itemsCovered}/${items.length})`;
      v.varianceVsL1 = '—';
    }
  });

  // Item-wise L1 calculation
  const itemWiseL1 = items.map(item => {
    let lowest = null;
    compareQuotes.forEach(q => {
      const qi = q.qitems.find(x => x.item_id === item.id && x.rate > 0);
      if (qi) {
        const unitLanded = gt(qi.rate, qi.gst);
        if (!lowest || unitLanded < lowest.unitLanded) {
          lowest = {
            vendor: q.vendor,
            vendor_id: q.vendor_id,
            rate: qi.rate,
            gst: qi.gst,
            unitLanded,
            totalLanded: unitLanded * item.qty
          };
        }
      }
    });
    return { item, lowest };
  });

  // Negotiation savings (Round 1 Initial Quote vs Round 2 Final Quote)
  let initialTotalL1 = 0;
  let finalTotalL1 = 0;
  if (p.type === 'revenue' && initialQuotes.length && compareQuotes.length) {
    const initFull = initialQuotes.map(q => {
      let t = 0;
      for (const qi of q.qitems) {
        const it = items.find(i => i.id === qi.item_id);
        if (it && qi.rate > 0) t += gt(qi.rate, qi.gst) * it.qty;
      }
      return t;
    }).sort((a, b) => a - b);
    initialTotalL1 = initFull[0] || 0;
    finalTotalL1 = fullQuotes[0]?.landedTotal || 0;
  }
  const savingsINR = Math.max(0, initialTotalL1 - finalTotalL1);
  const savingsPct = initialTotalL1 > 0 ? ((savingsINR / initialTotalL1) * 100).toFixed(1) : 0;

  return {
    proc: p,
    items,
    vendors: vendorSummaries,
    itemWiseL1,
    savings: { initialTotalL1, finalTotalL1, savingsINR, savingsPct }
  };
}

// ---- CST Printable HTML Report ----
function cstHtml(p, s, items, qs, u) {
  const cst = buildCstData(p, s, items, qs);
  return `<!doctype html><html><head><meta charset="utf-8"><title>Comparative Statement – ${p.code}</title>
  <style>
    @page { size: landscape; margin: 10mm; }
    body { font: 11px 'Segoe UI', Arial, sans-serif; color: #1e293b; margin: 0; background: #fff; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 12px; }
    .title { font-size: 18px; font-weight: bold; color: #0f172a; text-transform: uppercase; }
    .meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: #f8fafc; border: 1px solid #cbd5e1; padding: 8px; border-radius: 4px; margin-bottom: 12px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 14px; font-size: 11px; }
    th, td { border: 1px solid #94a3b8; padding: 6px 8px; text-align: left; }
    th { background: #0f172a; color: #fff; font-weight: 600; text-transform: uppercase; font-size: 10px; }
    .num { text-align: right; }
    .center { text-align: center; }
    .l1 { background: #dcfce7; font-weight: bold; color: #166534; }
    .l2 { background: #fef9c3; color: #854d0e; }
    .l3 { background: #fee2e2; color: #991b1b; }
    .tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px; }
    .tag-l1 { background: #15803d; color: #fff; }
    .tag-l2 { background: #ca8a04; color: #fff; }
    .savings-box { background: #eff6ff; border: 1px solid #3b82f6; border-radius: 6px; padding: 10px; margin-bottom: 14px; display: flex; justify-content: space-between; }
    .signatures { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 40px; page-break-inside: avoid; }
    .sig-box { border-top: 1px solid #0f172a; padding-top: 6px; text-align: center; font-weight: 600; }
  </style></head><body>
  <div class="header">
    <div>
      <div style="font-size: 13px; font-weight: 600; color: #64748b;">${esc(s.company)}</div>
      <div class="title">Commercial Comparative Statement (CST)</div>
    </div>
    <div style="text-align: right;">
      <b>Ref: ${p.code}</b><br>
      <span>Date: ${dmy(today())}</span>
    </div>
  </div>

  <div class="meta-grid">
    <div><b>Requisition Title:</b><br>${esc(p.title)}</div>
    <div><b>Department:</b><br>${esc(p.dept)}</div>
    <div><b>Delivery Location:</b><br>${esc(p.location)}</div>
    <div><b>Estimated Value:</b><br>${money(p.est)}</div>
  </div>

  ${cst.savings.savingsINR > 0 ? `
  <div class="savings-box">
    <div><b>Negotiation Savings Achieved:</b> Round 1 L1 (${money(cst.savings.initialTotalL1)}) vs Final Negotiated L1 (${money(cst.savings.finalTotalL1)})</div>
    <div><b style="color:#15803d; font-size: 14px;">Total Savings: ${money(cst.savings.savingsINR)} (${cst.savings.savingsPct}%)</b></div>
  </div>` : ''}

  <table>
    <thead>
      <tr>
        <th rowspan="2" class="center" style="width:30px">#</th>
        <th rowspan="2">Item Description &amp; Specs</th>
        <th rowspan="2" class="center">Qty</th>
        ${cst.vendors.map(v => `<th colspan="3" class="center" style="border-bottom: 1px solid #64748b">${esc(v.vendor)}<br><small>${v.rank} · Ref: ${esc(v.ref || 'NA')}</small></th>`).join('')}
      </tr>
      <tr>
        ${cst.vendors.map(() => `<th class="num">Basic</th><th class="center">GST%</th><th class="num">Landed</th>`).join('')}
      </tr>
    </thead>
    <tbody>
      ${items.map((item, idx) => `
        <tr>
          <td class="center">${idx + 1}</td>
          <td><b>${esc(item.name)}</b><br><small style="color:#64748b">${esc(item.descr || '')} | ${esc(item.model || '')} | HSN: ${esc(item.hsn || '')}</small></td>
          <td class="center">${item.qty} ${esc(item.unit)}</td>
          ${cst.vendors.map(v => {
            const r = v.itemRates.find(ir => ir.item_id === item.id);
            const isItemL1 = cst.itemWiseL1[idx]?.lowest?.vendor_id === v.vendor_id;
            return r && r.rate > 0 ? `
              <td class="num ${isItemL1 ? 'l1' : ''}">${money(r.rate)}</td>
              <td class="center ${isItemL1 ? 'l1' : ''}">${r.gst}%</td>
              <td class="num ${isItemL1 ? 'l1' : ''}"><b>${money(r.landed)}</b></td>`
              : `<td colspan="3" class="center" style="color:#94a3b8">Not Quoted</td>`;
          }).join('')}
        </tr>`).join('')}
      <tr style="background:#f1f5f9; font-weight:bold;">
        <td colspan="3" style="text-align:right;">Total Basic:</td>
        ${cst.vendors.map(v => `<td colspan="3" class="num">${money(v.basicTotal)}</td>`).join('')}
      </tr>
      <tr style="background:#f1f5f9; font-weight:bold;">
        <td colspan="3" style="text-align:right;">Total GST:</td>
        ${cst.vendors.map(v => `<td colspan="3" class="num">${money(v.gstTotal)}</td>`).join('')}
      </tr>
      <tr style="background:#e2e8f0; font-weight:bold; font-size: 12px;">
        <td colspan="3" style="text-align:right;">Grand Landed Cost:</td>
        ${cst.vendors.map(v => `
          <td colspan="3" class="num ${v.rank === 'L1' ? 'l1' : ''}">
            <b>${money(v.landedTotal)}</b><br>
            <span class="tag ${v.rank === 'L1' ? 'tag-l1' : 'tag-l2'}">${v.rank}</span>
            ${v.varianceVsL1 !== '0%' ? `<small style="font-weight:normal; margin-left:4px">+${v.varianceVsL1}</small>` : ''}
          </td>`).join('')}
      </tr>
      <tr>
        <td colspan="3" style="text-align:right; font-weight:600;">Payment &amp; Delivery:</td>
        ${cst.vendors.map(v => `<td colspan="3" style="font-size:10px;">Del: ${esc(v.delivery_days)}<br>Pay: ${esc(v.payment_terms)}</td>`).join('')}
      </tr>
    </tbody>
  </table>

  <div class="signatures">
    <div class="sig-box">Prepared By (Indenter)<br><small>${esc(u ? u.name : 'Procurement Officer')}</small></div>
    <div class="sig-box">Commercial Executive<br><small>Verified</small></div>
    <div class="sig-box">Head of Department (HOD)<br><small>Approved</small></div>
    <div class="sig-box">Finance &amp; Accounts<br><small>Budget Sanctioned</small></div>
  </div>
  </body></html>`;
}

// ---- Professional Purchase Order (PO / SO) Printable Layout ----
function poHtml(po, proc, vendor, poItems, settings) {
  const isSO = proc.kind === 'so';
  const orderTitle = isSO ? 'SERVICE ORDER' : 'PURCHASE ORDER';
  const numWords = numToWordsINR(po.total_landed);

  const coGst = String(settings.company_gst || '').trim();
  const vGst = String(vendor.gst || '').trim();
  const coStateCode = coGst.slice(0, 2);
  const vStateCode = vGst.slice(0, 2);
  const isInterState = Boolean(coStateCode && vStateCode && coStateCode !== vStateCode);

  return `<!doctype html><html><head><meta charset="utf-8"><title>${orderTitle} – ${po.po_no}</title>
  <style>
    @page { size: A4; margin: 10mm 12mm; }
    @media print {
      body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      .no-print { display: none !important; }
    }
    body { font: 12px 'Segoe UI', Arial, sans-serif; color: #0f172a; margin: 0; background: #fff; }
    .no-print { position: sticky; top: 0; z-index: 1000; background: #0f172a; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.25); margin-bottom: 14px; border-radius: 6px; }
    .po-box { border: 2px solid #0f172a; padding: 0; }
    .header { padding: 14px 18px; border-bottom: 2px solid #0f172a; display: flex; justify-content: space-between; align-items: center; }
    .company-title { font-size: 20px; font-weight: 800; color: #0f172a; text-transform: uppercase; }
    .company-sub { font-size: 11px; color: #475569; margin-top: 3px; line-height: 1.4; }
    .po-title-strip { background: #0f172a; color: #fff; text-align: center; font-size: 15px; font-weight: 700; letter-spacing: 2px; padding: 6px; }
    .info-table { width: 100%; border-collapse: collapse; }
    .info-table td { border-bottom: 1px solid #0f172a; border-right: 1px solid #0f172a; padding: 8px 12px; vertical-align: top; width: 50%; }
    .info-table td:last-child { border-right: 0; }
    .label { font-size: 10px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 3px; }
    table.items { width: 100%; border-collapse: collapse; }
    table.items th, table.items td { border-bottom: 1px solid #0f172a; border-right: 1px solid #0f172a; padding: 6px 8px; font-size: 11px; }
    table.items th { background: #f8fafc; font-weight: 700; text-align: left; }
    table.items td:last-child, table.items th:last-child { border-right: 0; }
    .num { text-align: right; }
    .center { text-align: center; }
    .words-box { padding: 10px 12px; border-bottom: 1px solid #0f172a; background: #f8fafc; font-size: 12px; }
    .terms-box { padding: 12px; border-bottom: 1px solid #0f172a; font-size: 10px; line-height: 1.5; color: #334155; }
    .sig-row { display: flex; justify-content: space-between; padding: 30px 20px 15px; }
    .sig { text-align: center; font-weight: 600; width: 220px; border-top: 1px solid #0f172a; padding-top: 4px; }
  </style></head><body>
  <div class="no-print">
    <div style="font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 10px;">
      <span>📑 ${orderTitle} — ${esc(po.po_no)}</span>
      <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">(${esc(vendor.name)})</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span style="font-size: 11px; color: #cbd5e1;">Tip: Select "Save as PDF" to download</span>
      <button onclick="window.print()" style="background: #2563eb; color: #fff; border: 0; padding: 7px 18px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
        🖨️ Print / Save as PDF
      </button>
      <button onclick="window.close()" style="background: rgba(255,255,255,0.15); color: #fff; border: 0; padding: 7px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">
        ✕ Close
      </button>
    </div>
  </div>
  <div class="po-box">
    <div class="header">
      <div>
        <div class="company-title">${esc(settings.company)}</div>
        <div class="company-sub">
          ${esc(settings.company_address)}, ${esc(settings.company_city)} - ${esc(settings.company_pincode)} (${esc(settings.company_state)})<br>
          GSTIN: <b>${esc(settings.company_gst)}</b> | PAN: <b>${esc(settings.company_pan)}</b><br>
          Email: ${esc(settings.company_email)} | Tel: ${esc(settings.company_phone)}
        </div>
      </div>
      <div>
        ${settings.logo ? `<img src="${settings.logo}" style="max-height:65px;">` : `<div style="font-size:24px; font-weight:900; color:#2563eb;">${isSO ? 'SO' : 'PO'}</div>`}
      </div>
    </div>

    <div class="po-title-strip">${orderTitle}</div>

    <table class="info-table">
      <tr>
        <td>
          <div class="label">Vendor / Supplier Details:</div>
          <b style="font-size: 13px;">${esc(vendor.name)}</b><br>
          ${nl(vendor.address)}<br>
          <b>GSTIN:</b> ${esc(vendor.gst)} | <b>PAN:</b> ${esc(vendor.pan || '—')}<br>
          <b>Contact Person:</b> ${esc(vendor.contact || '—')} | <b>Tel:</b> ${esc(vendor.phone || '—')}<br>
          <b>Email:</b> ${esc(vendor.email || '—')}
        </td>
        <td>
          <table style="width:100%; border-collapse:collapse; font-size: 11px;">
            <tr><td style="border:0; padding:2px 0;"><b>${orderTitle} No:</b></td><td style="border:0; padding:2px 0; text-align:right;"><b>${esc(po.po_no)}</b></td></tr>
            <tr><td style="border:0; padding:2px 0;"><b>Date:</b></td><td style="border:0; padding:2px 0; text-align:right;">${dmy(po.po_date)}</td></tr>
            <tr><td style="border:0; padding:2px 0;"><b>Requisition / PR Ref:</b></td><td style="border:0; padding:2px 0; text-align:right;">${esc(proc.code)}${proc.pr_no ? ' / SAP ' + esc(proc.pr_no) : ''}</td></tr>
            <tr><td style="border:0; padding:2px 0;"><b>Payment Terms:</b></td><td style="border:0; padding:2px 0; text-align:right;">${esc(po.payment_terms || '30 days')}</td></tr>
            <tr><td style="border:0; padding:2px 0;"><b>Delivery Due Date:</b></td><td style="border:0; padding:2px 0; text-align:right;">${esc(po.delivery_terms || 'Immediate')}</td></tr>
            <tr><td style="border:0; padding:2px 0;"><b>Delivery Location:</b></td><td style="border:0; padding:2px 0; text-align:right;">${esc(proc.location)}</td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td>
          <div class="label">Billing Address:</div>
          <b>${esc(settings.company)}</b><br>
          ${esc(settings.company_address)}, ${esc(settings.company_city)} - ${esc(settings.company_pincode)}<br>
          GSTIN: ${esc(settings.company_gst)}
        </td>
        <td>
          <div class="label">Shipping / Delivery Address:</div>
          <b>${esc(settings.company)}</b><br>
          Delivery Store: ${esc(proc.location)}<br>
          Department: ${esc(proc.dept)}
        </td>
      </tr>
    </table>

    <table class="items">
      <thead>
        <tr>
          <th class="center" style="width:30px">#</th>
          <th>Item Name &amp; Description</th>
          <th class="center">HSN/SAC</th>
          <th class="center">Qty</th>
          <th class="num">Unit Rate (₹)</th>
          <th class="num">Basic Total (₹)</th>
          <th class="center">GST %</th>
          <th class="num">Tax (₹)</th>
          <th class="num">Total Amount (₹)</th>
        </tr>
      </thead>
      <tbody>
        ${poItems.map((item, idx) => {
          const itemBasic = item.rate * item.qty;
          const itemTax = itemBasic * (item.gst / 100);
          const itemLanded = itemBasic + itemTax;
          return `
            <tr>
              <td class="center">${idx + 1}</td>
              <td><b>${esc(item.name)}</b>${item.descr ? `<br><small style="color:#64748b">${esc(item.descr)}</small>` : ''}${item.model ? `<br><small>Make/Model: ${esc(item.model)}</small>` : ''}</td>
              <td class="center">${esc(item.hsn || '—')}</td>
              <td class="center">${item.qty} ${esc(item.unit)}</td>
              <td class="num">${money(item.rate)}</td>
              <td class="num">${money(itemBasic)}</td>
              <td class="center">${item.gst}%</td>
              <td class="num">${money(itemTax)}</td>
              <td class="num"><b>${money(itemLanded)}</b></td>
            </tr>`;
        }).join('')}
        <tr style="background:#f8fafc; font-weight:bold;">
          <td colspan="5" style="text-align:right;">Subtotal (Basic):</td>
          <td class="num">${money(po.total_basic)}</td>
          <td></td>
          <td class="num">${money(po.total_gst)}</td>
          <td class="num"><b>${money(po.total_landed)}</b></td>
        </tr>
        <tr style="background:#f1f5f9; font-size:11px;">
          <td colspan="5" style="text-align:right; color:#475569; font-weight:600;">
            GST Tax Breakdown (${isInterState ? 'Inter-State Supply · IGST' : 'Intra-State Supply · CGST + SGST'}):
          </td>
          <td colspan="4" style="text-align:right; font-family:monospace; font-size:11px;">
            ${isInterState 
              ? `<b>IGST:</b> ₹${money(po.total_gst)}` 
              : `<b>CGST:</b> ₹${money(po.total_gst / 2)} &nbsp;|&nbsp; <b>SGST:</b> ₹${money(po.total_gst / 2)}`
            }
          </td>
        </tr>
      </tbody>
    </table>

    <div class="words-box">
      <b>Amount in Words:</b> ${numWords}
    </div>

    <div class="terms-box">
      <b style="text-transform:uppercase; font-size:11px;">Terms &amp; Conditions:</b>
      <div style="margin-top:4px;">${nl(po.terms_text || settings.po_terms)}</div>
    </div>

    <div class="sig-row">
      <div class="sig">Prepared &amp; Verified By<br><small>${esc(po.created_by || 'Procurement Executive')}</small></div>
      <div class="sig">Authorized Signatory<br><small>For ${esc(settings.company)}</small></div>
    </div>
  </div>
  </body></html>`;
}

// ---- Goods Receipt Note (GRN) Printable Layout ----
function grnHtml(grn, po, proc, grnItems, settings) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>GRN – ${grn.grn_no}</title>
  <style>
    @page { size: A4; margin: 10mm 12mm; }
    @media print {
      body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      .no-print { display: none !important; }
    }
    body { font: 12px 'Segoe UI', Arial, sans-serif; color: #0f172a; margin: 0; background: #fff; }
    .no-print { position: sticky; top: 0; z-index: 1000; background: #0f172a; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.25); margin-bottom: 14px; border-radius: 6px; }
    .box { border: 2px solid #0f172a; }
    .header { padding: 14px 18px; border-bottom: 2px solid #0f172a; display: flex; justify-content: space-between; align-items: center; }
    .title { font-size: 18px; font-weight: bold; text-transform: uppercase; color: #0f172a; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 12px; background: #f8fafc; border-bottom: 1px solid #0f172a; font-size: 11px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #0f172a; border-right: 1px solid #0f172a; padding: 7px 8px; font-size: 11px; }
    th { background: #0f172a; color: #fff; text-align: left; font-size: 10px; text-transform: uppercase; }
    td:last-child, th:last-child { border-right: 0; }
    .center { text-align: center; }
    .num { text-align: right; }
    .sig-row { display: flex; justify-content: space-between; padding: 36px 20px 20px; }
    .sig { text-align: center; font-weight: 600; width: 200px; border-top: 1px solid #0f172a; padding-top: 4px; }
  </style></head><body>
  <div class="no-print">
    <div style="font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 10px;">
      <span>📦 Goods Receipt Note (GRN) — ${esc(grn.grn_no)}</span>
      <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">(${esc(po ? po.vendor_name : 'Store Inward')})</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span style="font-size: 11px; color: #cbd5e1;">Tip: Select "Save as PDF" to download</span>
      <button onclick="window.print()" style="background: #2563eb; color: #fff; border: 0; padding: 7px 18px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
        🖨️ Print / Save as PDF
      </button>
      <button onclick="window.close()" style="background: rgba(255,255,255,0.15); color: #fff; border: 0; padding: 7px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">
        ✕ Close
      </button>
    </div>
  </div>
  <div class="box">
    <div class="header">
      <div>
        <div style="font-size:12px; font-weight:600; color:#64748b;">${esc(settings.company)}</div>
        <div class="title">Goods Receipt Note (GRN) / Store Inward</div>
      </div>
      <div style="text-align:right;">
        <b>GRN No: ${esc(grn.grn_no)}</b><br>
        <span>Date: ${dmy(grn.grn_date)}</span>
      </div>
    </div>

    <div class="grid">
      <div><b>Supplier Name:</b><br>${esc(po ? po.vendor_name : '—')}</div>
      <div><b>Purchase Order No:</b><br>${esc(po ? po.po_no : '—')} (${dmy(po ? po.po_date : '')})</div>
      <div><b>Requisition Ref:</b><br>${esc(proc.code)}</div>
      <div><b>Vendor Challan / DC No:</b><br>${esc(grn.challan_no || 'NA')}</div>
      <div><b>Challan Date:</b><br>${dmy(grn.challan_date)}</div>
      <div><b>Vehicle Number:</b><br>${esc(grn.vehicle_no || 'NA')}</div>
      <div><b>Delivery Location:</b><br>${esc(proc.location)}</div>
      <div><b>Received By Storekeeper:</b><br>${esc(grn.received_by || 'Store Department')}</div>
      <div><b>Inspection Remarks:</b><br>${esc(grn.remarks || 'Goods verified and accepted.')}</div>
    </div>

    <table>
      <thead>
        <tr>
          <th class="center" style="width:30px">#</th>
          <th>Item Description</th>
          <th class="center">Ordered Qty</th>
          <th class="center">Received Qty</th>
          <th class="center" style="background:#166534">Accepted Qty</th>
          <th class="center" style="background:#991b1b">Rejected Qty</th>
          <th>Rejection Reason / Remarks</th>
        </tr>
      </thead>
      <tbody>
        ${grnItems.map((item, idx) => `
          <tr>
            <td class="center">${idx + 1}</td>
            <td><b>${esc(item.name)}</b></td>
            <td class="center">${item.ordered_qty || item.qty || '—'}</td>
            <td class="center"><b>${item.received_qty}</b></td>
            <td class="center" style="font-weight:bold; color:#15803d">${item.accepted_qty}</td>
            <td class="center" style="color:#b91c1c">${item.rejected_qty || 0}</td>
            <td>${esc(item.rejection_reason || '—')}</td>
          </tr>`).join('')}
      </tbody>
    </table>

    <div class="sig-row">
      <div class="sig">Received By (Storekeeper)<br><small>Physical Inward Checked</small></div>
      <div class="sig">Inspected By (Quality / QA)<br><small>Technical Verification</small></div>
      <div class="sig">Stores In-charge<br><small>Inventory Recorded</small></div>
    </div>
  </div>
  </body></html>`;
}

// ---- Code 39 Vector SVG Barcode Generator ----
const CODE39 = {
  '0':'000110100','1':'100100001','2':'001100001','3':'101100000',
  '4':'000110001','5':'100110000','6':'001110000','7':'000100101',
  '8':'100100100','9':'001100100','A':'100001001','B':'001001001',
  'C':'101001000','D':'000011001','E':'100011000','F':'001011000',
  'G':'000001101','H':'100001100','I':'001001100','J':'000011100',
  'K':'100000011','L':'001000011','M':'101000010','N':'000010011',
  'O':'100010010','P':'001010010','Q':'000000111','R':'100000110',
  'S':'001000110','T':'000010110','U':'110000001','V':'011000001',
  'W':'111000000','X':'010010001','Y':'110010000','Z':'011010000',
  '-':'010000101','.':'110000100',' ':'011000100','$':'010101000',
  '/':'010100010','+':'010001010','%':'000101010','*':'010010100'
};

function generateBarcodeSvg(code, height = 48) {
  const clean = '*' + String(code || 'AST-0001').toUpperCase().replace(/[^0-9A-Z-. $/+%]/g, '-') + '*';
  let x = 6;
  const bars = [];
  const narrow = 2;
  const wide = 5;
  const gap = 2;
  for (let i = 0; i < clean.length; i++) {
    const pat = CODE39[clean[i]] || CODE39['-'];
    for (let j = 0; j < 9; j++) {
      const isBar = (j % 2 === 0);
      const w = pat[j] === '1' ? wide : narrow;
      if (isBar) {
        bars.push(`<rect x="${x}" y="0" width="${w}" height="${height}" fill="#000000" />`);
      }
      x += w;
    }
    x += gap;
  }
  const totalW = x + 6;
  return `<svg viewBox="0 0 ${totalW} ${height}" preserveAspectRatio="xMidYMid meet" style="max-width:100%; height:${height}px; display:block; margin:0 auto;" xmlns="http://www.w3.org/2000/svg">${bars.join('')}</svg>`;
}

// ---- Factory Asset Tag Printable Label & Card ----
function assetTagHtml(asset, po, proc, settings) {
  proc = proc || {};
  po = po || {};
  settings = settings || {};
  const company = settings.company || 'ProcureLocal Enterprise';
  const assetCode = asset.asset_code || asset.tag_code || `AST-${asset.id}`;
  const barcodeSvg = generateBarcodeSvg(assetCode, 48);
  const stickerBarcodeSvg = generateBarcodeSvg(assetCode, 36);

  return `<!doctype html><html><head><meta charset="utf-8">
  <title>Asset Tag Label – ${esc(assetCode)}</title>
  <style>
    @media print {
      @page { size: auto; margin: 8mm; }
      body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #fff !important;
        padding: 0 !important;
      }
      .no-print { display: none !important; }
      .sheet-wrap { box-shadow: none !important; margin: 0 auto !important; border: none !important; }
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      color: #0f172a;
      margin: 0;
      padding: 20px 16px;
      background: #f1f5f9;
      font-size: 12px;
      line-height: 1.4;
    }

    /* Action Control Toolbar */
    .ctrl-bar {
      max-width: 820px;
      margin: 0 auto 18px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .ctrl-title {
      font-size: 13.5px;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .ctrl-btns {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: #334155;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s;
    }
    .btn:hover { background: #f8fafc; border-color: #94a3b8; }
    .btn.primary {
      background: #2563eb;
      border-color: #1d4ed8;
      color: #ffffff;
      font-weight: 700;
    }
    .btn.primary:hover { background: #1d4ed8; }

    .sheet-wrap {
      max-width: 820px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 24px 28px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.06);
    }

    /* Sticker Layout (4" x 2" / 100mm x 55mm) */
    .sticker-container {
      max-width: 460px;
      margin: 0 auto 28px;
      border: 2.5px solid #0f172a;
      border-radius: 6px;
      overflow: hidden;
      background: #ffffff;
      box-shadow: 0 2px 5px rgba(0,0,0,0.08);
      page-break-inside: avoid;
    }
    .sticker-header {
      background: #0f172a;
      color: #ffffff;
      padding: 8px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .sticker-body {
      padding: 12px 14px;
      background: #ffffff;
    }
    .sticker-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 10px;
      font-size: 11px;
      margin-bottom: 10px;
    }
    .sticker-barcode-box {
      background: #f8fafc;
      border: 1.5px dashed #0f172a;
      border-radius: 4px;
      padding: 8px 10px;
      text-align: center;
    }
    .sticker-code {
      font-family: monospace;
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 2.5px;
      margin-top: 4px;
      color: #000000;
    }
    .sticker-footer {
      background: #f1f5f9;
      border-top: 1px solid #cbd5e1;
      text-align: center;
      font-size: 9px;
      color: #475569;
      padding: 5px 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    /* A4 Asset Capitalization Card */
    .card-container {
      border: 1.5px solid #cbd5e1;
      border-radius: 8px;
      padding: 20px;
      margin-top: 20px;
      page-break-inside: avoid;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 12px;
      margin-bottom: 16px;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
      font-size: 11.5px;
    }
    table.data-table th, table.data-table td {
      border: 1px solid #cbd5e1;
      padding: 7px 10px;
      text-align: left;
      vertical-align: middle;
    }
    table.data-table th {
      background: #f8fafc;
      color: #334155;
      font-weight: 700;
      width: 25%;
    }
    .sign-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
      margin-top: 36px;
      page-break-inside: avoid;
    }
    .sign-box {
      border-top: 1px solid #0f172a;
      text-align: center;
      padding-top: 6px;
      font-size: 11px;
    }
    .sign-title { font-weight: 700; color: #0f172a; }
    .sign-sub { font-size: 9.5px; color: #64748b; }
  </style>
  </head>
  <body>

    <!-- On-Screen Control Toolbar -->
    <div class="ctrl-bar no-print">
      <div class="ctrl-title">
        <span>🏷️</span>
        <span>Factory Asset Barcode Tag Label &bull; ${esc(assetCode)}</span>
      </div>
      <div class="ctrl-btns">
        <button class="btn primary" onclick="window.print()">
          🖨️ Print Label / Sticker
        </button>
        <button class="btn" onclick="downloadLabelHtml()">
          📥 Download HTML
        </button>
        <button class="btn" onclick="toggleLayout()">
          🔄 Toggle Sticker / A4 Card
        </button>
        <button class="btn" onclick="window.close()">
          ✕ Close
        </button>
      </div>
    </div>

    <div class="sheet-wrap">

      <!-- SECTION 1: 4" x 2" ADHESIVE EQUIPMENT LABEL (STICKER) -->
      <div id="sticker_sec">
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
          <span>Industrial Equipment Adhesive Sticker (100mm × 55mm / 4" × 2")</span>
          <span class="no-print" style="color:#2563eb; font-weight:600; cursor:pointer;" onclick="window.print()">[ Direct Sticker Print ]</span>
        </div>

        <div class="sticker-container">
          <div class="sticker-header">
            <div>
              <div style="font-size:9.5px; text-transform:uppercase; letter-spacing:0.06em; opacity:0.85; font-weight:700;">${esc(company)}</div>
              <div style="font-size:14px; font-weight:800; letter-spacing:0.02em;">FACTORY FIXED ASSET PROPERTY</div>
            </div>
            <div>
              <span style="background:#22c55e; color:#0f172a; font-size:9.5px; font-weight:800; padding:2px 8px; border-radius:4px; text-transform:uppercase;">ACTIVE</span>
            </div>
          </div>
          <div class="sticker-body">
            <div style="font-size:13.5px; font-weight:800; color:#0f172a; margin-bottom:8px; border-bottom:1px solid #e2e8f0; padding-bottom:4px; line-height:1.2;">
              ${esc(asset.asset_name || 'Plant Equipment')}
            </div>
            <div class="sticker-grid">
              <div><span style="color:#64748b;">Asset Class:</span><br><b>${esc(asset.category || 'Plant Machinery')}</b></div>
              <div><span style="color:#64748b;">Plant Location:</span><br><b>${esc(asset.plant_location || proc.location || 'Factory')}</b></div>
              <div><span style="color:#64748b;">OEM Serial No:</span><br><code style="font-weight:700;">${esc(asset.serial_no || 'NA')}</code></div>
              <div><span style="color:#64748b;">Capitalized Date:</span><br><b>${dmy(asset.capitalization_date)}</b></div>
            </div>
            <div class="sticker-barcode-box">
              ${stickerBarcodeSvg}
              <div class="sticker-code">* ${esc(assetCode)} *</div>
            </div>
          </div>
          <div class="sticker-footer">
            Property of ${esc(company)} &bull; Unauthorized Removal Strictly Prohibited
          </div>
        </div>
      </div>

      <!-- SECTION 2: FORMAL ASSET CAPITALIZATION RECORD & CARD -->
      <div id="card_sec">
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">
          Statutory Capitalization Card &amp; Plant Register (A4 Audit Document)
        </div>

        <div class="card-container">
          <div class="card-header">
            <div>
              <div style="font-size:17px; font-weight:800; color:#1e3a8a; text-transform:uppercase;">${esc(company)}</div>
              <div style="font-size:12px; font-weight:700; color:#0f172a; margin-top:2px;">FIXED ASSET CAPITALIZATION &amp; COMMISSIONING CERTIFICATE</div>
              <div style="font-size:11px; color:#64748b; margin-top:2px;">Plant Location: <b>${esc(asset.plant_location || proc.location || 'Factory')}</b> &bull; Asset Register Category: <b>${esc(asset.category || 'Plant & Machinery')}</b></div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:11px; color:#475569;">Asset ID:</div>
              <div style="font-size:15px; font-weight:800; font-family:monospace; color:#2563eb;">${esc(assetCode)}</div>
              <div style="font-size:10px; color:#64748b; margin-top:2px;">Status: <b>${esc(asset.status || 'Capitalized & In-Service')}</b></div>
            </div>
          </div>

          <table class="data-table">
            <tr>
              <th>Equipment / Asset Name</th>
              <td colspan="3"><b style="font-size:13px;">${esc(asset.asset_name)}</b></td>
            </tr>
            <tr>
              <th>SAP Code</th>
              <td><code style="font-weight:700; font-size:12px; color:#2563eb;">${esc(assetCode)}</code></td>
              <th>OEM Serial / Chassis No</th>
              <td><code>${esc(asset.serial_no || 'NA')}</code></td>
            </tr>
            <tr>
              <th>Asset Category</th>
              <td>${esc(asset.category || 'Plant & Machinery')}</td>
              <th>Asset Custodian</th>
              <td><b>${esc(asset.custodian || 'Plant Engineer')}</b></td>
            </tr>
            <tr>
              <th>Capitalization Date</th>
              <td><b>${dmy(asset.capitalization_date)}</b></td>
              <th>Commissioning Date</th>
              <td>${dmy(asset.commissioning_date || asset.capitalization_date)}</td>
            </tr>
            <tr>
              <th>Capitalized Book Value</th>
              <td><b style="color:#0f172a; font-size:13px;">${inr(asset.cost || proc.est)}</b></td>
              <th>Warranty Expiry Date</th>
              <td>${dmy(asset.warranty_expiry || '') || 'Standard 12 Months'}</td>
            </tr>
            <tr>
              <th>Purchase Order Ref</th>
              <td><b>${esc(po.po_no || proc.po_no || 'PO Ref')}</b> ${po.po_date ? '(' + dmy(po.po_date) + ')' : ''}</td>
              <th>Requisition Indent Ref</th>
              <td><b>${esc(proc.code || 'PR')}</b> - ${esc(proc.title || '')}</td>
            </tr>
            <tr>
              <th>Vendor / Supplier</th>
              <td><b>${esc(po.vendor_name || 'Authorized Supplier')}</b></td>
              <th>Operating Department</th>
              <td><span style="text-transform:uppercase;">${esc(proc.dept || 'Plant Engineering')}</span></td>
            </tr>
            ${asset.remarks ? `<tr><th>Asset Remarks</th><td colspan="3">${esc(asset.remarks)}</td></tr>` : ''}
          </table>

          <div style="background:#f8fafc; border:1.5px dashed #0f172a; border-radius:6px; padding:12px; text-align:center; margin:16px 0;">
            ${barcodeSvg}
            <div style="font-family:monospace; font-size:15px; font-weight:800; letter-spacing:3px; margin-top:6px; color:#000;">
              * ${esc(assetCode)} *
            </div>
            <div style="font-size:9.5px; color:#64748b; margin-top:2px;">
              SAP FI-AA / PM &amp; ISO 55000 Compliant Asset Barcode Identifier
            </div>
          </div>

          <div class="sign-row">
            <div class="sign-box">
              <div class="sign-title">STORE / RECEIVING OFFICER</div>
              <div class="sign-sub">Tagging &amp; Physical Verification</div>
            </div>
            <div class="sign-box">
              <div class="sign-title">MAINTENANCE / PLANT ENGINEER</div>
              <div class="sign-sub">Commissioning Acceptance</div>
            </div>
            <div class="sign-box">
              <div class="sign-title">PLANT FINANCE &amp; ACCOUNTS</div>
              <div class="sign-sub">FAR Capitalization Sign-off</div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <script>
      function downloadLabelHtml() {
        const html = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
        const blob = new Blob([html], { type: 'text/html;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Asset_Label_${esc(assetCode)}.html';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      function toggleLayout() {
        const s = document.getElementById('sticker_sec');
        const c = document.getElementById('card_sec');
        if (s.style.display === 'none') {
          s.style.display = 'block';
          c.style.display = 'block';
        } else if (c.style.display !== 'none') {
          c.style.display = 'none';
        } else {
          s.style.display = 'none';
          c.style.display = 'block';
        }
      }

      window.onload = function() {
        if (!window.location.search.includes('noprint')) {
          setTimeout(function() {
            try { window.print(); } catch(e) {}
          }, 400);
        }
      };
    </script>
  </body></html>`;
}

// ---- Dedicated Post-PO/SO SAP Code & Serial Number ONLY Printable Sticker / Label ----
function sapSerialPrintHtml(assetsList, po, proc, settings) {
  proc = proc || {};
  po = po || {};
  settings = settings || {};
  assetsList = (Array.isArray(assetsList) && assetsList.length) ? assetsList : [{
    asset_code: proc.asset_code || (po.po_no ? `AST-${po.po_no}` : 'AST-2026-0001'),
    serial_no: proc.serial_no || 'SN-84920',
    asset_name: proc.title || 'Plant Equipment / Asset',
    plant_location: proc.location || 'Factory / Plant',
    category: proc.kind || 'Plant Asset'
  }];

  const company = settings.company || 'ProcureLocal Enterprise';
  const docRef = po.po_no ? `PO / SO #${po.po_no}` : (proc.code ? `PR #${proc.code}` : 'Order Equipment');

  const cardsHtml = assetsList.map((ast, idx) => {
    const sapCode = String(ast.asset_code || ast.tag_code || `AST-${ast.id || (idx + 1)}`).trim();
    const serialNo = String(ast.serial_no || 'NA').trim();
    const sapBarcode = generateBarcodeSvg(sapCode, 42);
    const snBarcode = (serialNo && !['na', 'n/a', 'none', '—', '-', 'null'].includes(serialNo.toLowerCase()))
      ? generateBarcodeSvg(serialNo, 36)
      : '';
    const itemName = ast.asset_name || proc.title || 'Industrial Equipment';

    return `
      <div class="label-card">
        <div class="label-top-bar">
          <div>${esc(company)}</div>
          <div>${esc(docRef)}</div>
        </div>
        <div class="label-content">
          <div class="meta-row">
            <div><b>Item:</b> ${esc(itemName)}</div>
            <div><b>Location:</b> ${esc(ast.plant_location || proc.location || 'Factory')}</div>
          </div>

          <!-- 1. SAP ASSET CODE -->
          <div class="highlight-box">
            <div class="box-title">🏷️ SAP ASSET CODE</div>
            <div class="box-code">${esc(sapCode)}</div>
            <div class="barcode-svg">${sapBarcode}</div>
          </div>

          <!-- 2. OEM SERIAL NUMBER -->
          <div class="highlight-box" style="margin-bottom:0;">
            <div class="box-title">🔢 OEM SERIAL NUMBER</div>
            <div class="box-code">${esc(serialNo)}</div>
            ${snBarcode ? `<div class="barcode-svg">${snBarcode}</div>` : ''}
          </div>
        </div>
        <div class="label-footer">
          PLANT VERIFIED ASSET &bull; POST PO/SO COMPLETION RECORD
        </div>
      </div>
    `;
  }).join('');

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SAP Code &amp; Serial Number Print – ${esc(docRef)}</title>
  <style>
    @media print {
      @page { size: auto; margin: 4mm; }
      body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #fff !important;
        padding: 0 !important;
      }
      .no-print { display: none !important; }
      .sheet-wrap { box-shadow: none !important; margin: 0 auto !important; border: none !important; width: 100% !important; max-width: 100% !important; padding: 0 !important; }
      .label-card { page-break-inside: avoid; break-inside: avoid; margin-bottom: 8mm !important; box-shadow: none !important; border: 2.5px solid #000 !important; }
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      color: #0f172a;
      margin: 0;
      padding: 16px;
      background: #f1f5f9;
      font-size: 13px;
    }

    .ctrl-bar {
      max-width: 720px;
      margin: 0 auto 16px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .ctrl-title {
      font-size: 13.5px;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .ctrl-btns {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 6px 14px;
      font-size: 12.5px;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: #334155;
      cursor: pointer;
      text-decoration: none;
    }
    .btn.primary {
      background: #0284c7;
      border-color: #0369a1;
      color: #ffffff;
      font-weight: 700;
    }
    .btn.primary:hover { background: #0369a1; }

    .sheet-wrap {
      max-width: 720px;
      margin: 0 auto;
    }

    .label-card {
      background: #ffffff;
      border: 2.5px solid #0f172a;
      border-radius: 8px;
      margin: 0 auto 20px;
      max-width: 440px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
      overflow: hidden;
      page-break-inside: avoid;
    }

    .label-top-bar {
      background: #0f172a;
      color: #ffffff;
      padding: 7px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.05em;
    }

    .label-content {
      padding: 14px 16px;
      background: #ffffff;
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 6px;
      border-bottom: 1.5px solid #e2e8f0;
      font-size: 11.5px;
      color: #475569;
    }

    .highlight-box {
      background: #f8fafc;
      border: 2px solid #0f172a;
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 12px;
      text-align: center;
    }

    .box-title {
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #475569;
      margin-bottom: 2px;
    }

    .box-code {
      font-family: "Courier New", Courier, monospace;
      font-size: 20px;
      font-weight: 900;
      letter-spacing: 2px;
      color: #0f172a;
    }

    .barcode-svg {
      margin: 6px auto 0;
      max-width: 100%;
    }

    .label-footer {
      background: #f8fafc;
      border-top: 1px solid #cbd5e1;
      padding: 5px 12px;
      text-align: center;
      font-size: 9.5px;
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
  </style>
</head>
<body>
  <div class="ctrl-bar no-print">
    <div class="ctrl-title">
      <span>🏷️</span>
      <span>SAP Code &amp; Serial Number Print &bull; ${esc(docRef)}</span>
    </div>
    <div class="ctrl-btns">
      <button class="btn primary" onclick="window.print()">
        🖨️ Print Label / Sticker
      </button>
      <button class="btn" onclick="window.close()">
        ✕ Close
      </button>
    </div>
  </div>

  <div class="sheet-wrap">
    <div class="no-print" style="text-align:center; margin-bottom:14px; font-size:12px; color:#64748b;">
      Direct Equipment Barcode Label for Physical Plant Tagging (Contains strictly <b>SAP Code</b> &amp; <b>Serial Number</b>)
    </div>
    ${cardsHtml}
  </div>

  <script>
    window.onload = function() {
      if (!window.location.search.includes('noprint')) {
        setTimeout(function() {
          try { window.print(); } catch(e) {}
        }, 400);
      }
    };
  </script>
</body>
</html>`;
}

// ---- Official Certificate of Completion (FAR Handover & Plant Capitalization Form) ----
function completionCertHtml(proc, po, grn, items, assets, certData, settings) {
  proc = proc || {};
  po = po || {};
  certData = certData || {};
  settings = settings || {};

  const companyName = (certData.company_name || settings.company || 'ITC LIMITED').toUpperCase();
  const factoryName = (certData.factory_name || 'ITD - RANJANGAON CIGARETTE FACTORY').toUpperCase();
  const factoryAddr = (certData.plant_address || 'PLOT-B27, MIDC, RANJANGAON, PUNE - 412220').toUpperCase();

  const ioNo = certData.io_no || proc.io_number || proc.code || '10064019';
  const ioDesc = certData.io_desc || proc.title || (items && items[0] ? items[0].name : '') || 'PowerEdge R570 Server, Enterprise';
  const poNo = certData.po_no || po.po_no || proc.po_no || '4300055286';
  const installDate = certData.install_date || proc.received_date || (grn && grn.grn_date) || today();
  const location = certData.location || proc.plant_location || proc.location || 'MIS ITC PUNFCT';
  const modelName = certData.model_name || (items && items[0] ? (items[0].model || items[0].name) : '') || proc.title || 'PowerEdge R570 Server, Enterprise';

  let serialNo = certData.serial_numbers;
  if (!serialNo && assets && assets.length) {
    serialNo = assets.map(a => a.serial_no).filter(Boolean).join(', ');
  }
  serialNo = serialNo || 'DNF8LM4, 8PF8LM4, 2MF8LM4, 1PF8LM4';

  const remarks = certData.remarks || '';
  const assetCount = certData.asset_count || (assets && assets.length ? `${assets.length} Nos` : '4 Nos');
  const projectIncharge = certData.project_incharge || 'Project Incharge';
  const headOfDept = certData.head_of_user_dept || 'Head of User Department';

  // Commercial items list (Asset Particulars & SAP Asset No)
  let commItems = certData.commercial_items;
  if (!commItems || !commItems.length) {
    const list = serialNo.split(',').map(s => s.trim()).filter(Boolean);
    if (list.length) {
      commItems = list.map(s => ({ particular: s, sap_asset_no: '' }));
    } else {
      commItems = [
        { particular: 'DNF8LM4', sap_asset_no: '' },
        { particular: '8PF8LM4', sap_asset_no: '' },
        { particular: '2MF8LM4', sap_asset_no: '' },
        { particular: '1PF8LM4', sap_asset_no: '' }
      ];
    }
  }
  while (commItems.length < 4) {
    commItems.push({ particular: '', sap_asset_no: '' });
  }

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Certificate of Completion - ${esc(proc.code || 'Asset Form')}</title>
  <style>
    @media print {
      @page {
        size: A4 portrait;
        margin: 10mm 12mm;
      }
      body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #fff !important;
        padding: 0 !important;
        margin: 0 !important;
      }
      .no-print {
        display: none !important;
      }
      .cert-container {
        border: 1.5px solid #000 !important;
        box-shadow: none !important;
        margin: 0 auto !important;
        width: 100% !important;
        max-width: 100% !important;
      }
    }

    * {
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }

    body {
      font-family: Arial, Helvetica, sans-serif;
      color: #000;
      background: #f1f5f9;
      margin: 0;
      padding: 24px 16px;
      font-size: 11.5px;
      line-height: 1.35;
    }

    /* Floating Control Toolbar */
    .no-print {
      max-width: 760px;
      margin: 0 auto 16px auto;
      background: #0f172a;
      color: #fff;
      padding: 10px 18px;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .no-print h4 {
      margin: 0;
      font-size: 13.5px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .no-print .btn-group {
      display: flex;
      gap: 8px;
    }
    .no-print button {
      background: #2563eb;
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: 5px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .no-print button:hover {
      background: #1d4ed8;
    }
    .no-print button.secondary {
      background: #334155;
    }
    .no-print button.secondary:hover {
      background: #475569;
    }

    /* Main Certificate Sheet (Matching Physical Photo) */
    .cert-container {
      max-width: 760px;
      margin: 0 auto;
      background: #fff;
      border: 1.5px solid #000;
      box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }

    .cert-header {
      padding: 6px 10px;
      border-bottom: 1px solid #000;
      font-size: 12px;
      line-height: 1.35;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.01em;
    }

    .cert-title-bar {
      padding: 5px 10px;
      border-bottom: 1px solid #000;
      font-size: 12.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }

    .cert-statement {
      padding: 6px 10px;
      border-bottom: 1px solid #000;
      font-size: 11px;
      line-height: 1.35;
    }

    /* Field Grid Table */
    .field-table {
      width: 100%;
      border-collapse: collapse;
      border-bottom: 1px solid #000;
    }
    .field-table tr {
      border-bottom: 1px solid #000;
    }
    .field-table tr:last-child {
      border-bottom: none;
    }
    .field-lbl {
      width: 44%;
      border-right: 1px solid #000;
      padding: 5px 10px;
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      vertical-align: middle;
      letter-spacing: 0.01em;
    }
    .field-val {
      width: 56%;
      padding: 5px 10px;
      font-size: 11px;
      vertical-align: middle;
      font-weight: 500;
    }

    /* Signatures Section */
    .sig-table {
      width: 100%;
      border-collapse: collapse;
      border-bottom: 1px solid #000;
    }
    .sig-cell {
      width: 50%;
      padding: 10px;
      vertical-align: bottom;
      text-align: center;
    }
    .sig-cell:first-child {
      border-right: 1px solid #000;
    }
    .sig-space {
      height: 80px;
    }
    .sig-label {
      font-size: 11.5px;
      font-weight: 700;
      color: #000;
    }

    /* Commercial Section */
    .comm-title {
      padding: 5px 10px;
      border-bottom: 1px solid #000;
      font-size: 11px;
      font-weight: 700;
      text-decoration: underline;
    }

    .comm-table {
      width: 100%;
      border-collapse: collapse;
    }
    .comm-table th {
      padding: 4px 10px;
      border-bottom: 1px solid #000;
      font-size: 11px;
      font-weight: 700;
      text-align: left;
    }
    .comm-table th:first-child,
    .comm-table td:first-child {
      width: 44%;
      border-right: 1px solid #000;
    }
    .comm-table th:last-child,
    .comm-table td:last-child {
      width: 56%;
    }
    .comm-table td {
      padding: 4px 10px;
      border-bottom: 1px solid #000;
      font-size: 11px;
      min-height: 22px;
    }
    .comm-table tr:last-child td {
      border-bottom: none;
    }
  </style>
</head>
<body>

  <!-- Floating Control Bar (Hidden when Printing) -->
  <div class="no-print">
    <h4>📜 Certificate of Completion – ${esc(proc.code || 'Asset Form')}</h4>
    <div class="btn-group">
      <button onclick="window.print()">🖨️ Print Certificate</button>
      <button class="secondary" onclick="window.close()">✕ Close</button>
    </div>
  </div>

  <!-- Physical Certificate Container -->
  <div class="cert-container">

    <!-- Header Section -->
    <div class="cert-header">
      <div>${esc(companyName)}</div>
      <div>${esc(factoryName)}</div>
      <div>${esc(factoryAddr)}</div>
    </div>

    <!-- Title Bar -->
    <div class="cert-title-bar">
      CERTIFICATE OF COMPLETION
    </div>

    <!-- Certification Statement -->
    <div class="cert-statement">
      This is to certify that the following machinery/work(s) have been completed and put-to-use on the date mentioned hereunder
    </div>

    <!-- 2-Column Fields Grid Table -->
    <table class="field-table">
      <tr>
        <td class="field-lbl">INTERNAL ORDER NO</td>
        <td class="field-val">: ${esc(ioNo)}</td>
      </tr>
      <tr>
        <td class="field-lbl">INTERNAL ORDER DESCRIPTION</td>
        <td class="field-val">: ${esc(ioDesc)}</td>
      </tr>
      <tr>
        <td class="field-lbl">PURCHASE/SERVICE ORDER NO.</td>
        <td class="field-val">: ${esc(poNo)}</td>
      </tr>
      <tr>
        <td class="field-lbl">DATE OF INSTALLATION/COMPLETION</td>
        <td class="field-val">: ${esc(installDate)}</td>
      </tr>
      <tr>
        <td class="field-lbl">LOCATION OF THE MACHINE/ITEM</td>
        <td class="field-val">: ${esc(location)}</td>
      </tr>
      <tr>
        <td class="field-lbl">MODEL NAME &amp; MACHINE NO/IMIE</td>
        <td class="field-val">: ${esc(modelName)}</td>
      </tr>
      <tr>
        <td class="field-lbl">SERIAL NO OF THE ASSET</td>
        <td class="field-val">: ${esc(serialNo)}</td>
      </tr>
      <tr>
        <td class="field-lbl">OTHER REMARKS, IF ANY</td>
        <td class="field-val">: ${esc(remarks)}</td>
      </tr>
      <tr>
        <td class="field-lbl">ASSET NO.(S)</td>
        <td class="field-val">: ${esc(assetCount)}</td>
      </tr>
    </table>

    <!-- Signatures Area -->
    <table class="sig-table">
      <tr>
        <td class="sig-cell">
          <div class="sig-space"></div>
          <div class="sig-label">${esc(projectIncharge)}</div>
        </td>
        <td class="sig-cell">
          <div class="sig-space"></div>
          <div class="sig-label">${esc(headOfDept)}</div>
        </td>
      </tr>
    </table>

    <!-- Commercial Usage Note -->
    <div class="comm-title">
      Note: For Commercial Usage/Input:-
    </div>

    <!-- Commercial Usage Sub-Table -->
    <table class="comm-table">
      <thead>
        <tr>
          <th>Asset Particulars</th>
          <th>SAP Asset No</th>
        </tr>
      </thead>
      <tbody>
        ${commItems.map(item => `
          <tr>
            <td>${esc(item.particular || '') || '&nbsp;'}</td>
            <td>${esc(item.sap_asset_no || '') || '&nbsp;'}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>

  </div>

  <script>
    if (new URLSearchParams(window.location.search).get('autoprint') === '1') {
      window.addEventListener('load', () => setTimeout(() => window.print(), 350));
    }
  </script>
</body>
</html>`;
}

// ---- Official IT CITPC Note (IT Procurement & Capex Committee Sanction Form) ----
function citpcNoteHtml(proc, items, noteData, settings) {
  proc = proc || {};
  items = items || [];
  noteData = noteData || {};
  settings = settings || {};

  const title = noteData.title || proc.title || (items[0] ? items[0].name : '') || 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Modules and 7 Years Support for Pune Factory under Replacement with Implementation. - Nos:-22';
  const division = noteData.division || proc.dept || 'ITD';
  const indenterName = noteData.indenter_name || proc.created_by || proc.owner || 'Amitava Mukherjee';
  const citpcRequired = noteData.citpc_required || 'Yes';

  const requestType = noteData.request_type || 'Request Type I';
  const typeHardware = noteData.type_hardware || 'Hardware';
  const subTypeName = noteData.subtype_name || 'Standard Switches / Routers.';
  const leadTimeOk = noteData.lead_time_ok || 'Yes';

  const background = noteData.background || `The existing 24 Port Access Switches deployed across Pune Factory have completed their useful lifecycle of 7 years and have been written off. These switches are used to provide network connectivity across the factory through various VLANs to desktops, printers, IP phones, wireless access points, and other network-connected devices. Due to aging hardware, increasing network utilization, and lack of OEM support, replacement of the existing switches is required to ensure network reliability, improved performance, enhanced security, and uninterrupted business operations.`;

  const need = noteData.need || `Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Uplink Modules, DNA Term License, Dual Power Supply, and 7 Years OEM Support for replacement of existing obsolete access switches at Pune Factory.`;

  const totalQty = items.reduce((sum, it) => sum + (Number(it.qty) || 0), 0) || 22;
  const defReqDetails = (items && items.length > 0)
    ? (items.map(it => `${it.name} - Qty: ${it.qty} ${it.uom || 'Nos'}`).join('\n') + `\nQuantity: ${totalQty} Nos\nDelivery Location: ${proc.plant_location || 'Pune Factory ITC Ranjangaon.'}`)
    : `Standard 24 Port UTP PoE Layer 2 Switch with 24 PoE ports, 4 x 10G Enterprise Class SFP uplink ports and 1/10G SFP modules, DNA Term License, Dual Power Supply, Indian Power Cables, all necessary installation accessories, implementation services, and 7 years OEM warranty & support.\nQuantity: ${totalQty} Nos\nDelivery Location: ${proc.plant_location || 'Pune Factory ITC Ranjangaon.'}`;
  const reqDetails = noteData.req_details || defReqDetails;

  const vendorsConsidered = noteData.vendors_considered || 'As per CITPC Approval. Sample Quote enclosed for reference only.';

  const techEvaluation = noteData.tech_evaluation || `1. Type: Layer 2 Managed Enterprise Switch with 24 UTP PoE ports, 4 x 10G SFP uplink ports and modules, enterprise-class hardware, VLAN, QoS, STP/RSTP, IPv4/IPv6, SNMP, SSH, Web Management, Dual Power Supply, Stacking Capability, DNA Term License, and 7 years OEM warranty & support.`;

  const negotiationHistory = noteData.negotiation_history || 'NA';

  const brandOptions = noteData.brand_options || {
    capacity_aug: false,
    standardized: true,
    cio_approved: false
  };

  const attachProposals = noteData.attach_proposals || '';
  const scopeCertified = noteData.scope_certified || 'Y';
  const additionalInfo = noteData.additional_info || '';

  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IT CITPC note - ${esc(proc.code || 'Form')}</title>
  <style>
    @media print {
      @page {
        size: A4 portrait;
        margin: 8mm 10mm;
      }
      body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #fff !important;
        padding: 0 !important;
        margin: 0 !important;
      }
      .no-print {
        display: none !important;
      }
      .citpc-sheet {
        border: 1px solid #000 !important;
        padding: 4px !important;
        box-shadow: none !important;
        margin: 0 auto !important;
        width: 100% !important;
        max-width: 100% !important;
      }
      .page-break {
        page-break-before: always;
        break-before: page;
        margin-top: 15mm;
      }
    }

    * {
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }

    body {
      font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
      color: #000;
      background: #f1f5f9;
      margin: 0;
      padding: 24px 16px;
      font-size: 11px;
      line-height: 1.35;
    }

    /* Floating Control Toolbar */
    .no-print {
      max-width: 800px;
      margin: 0 auto 16px auto;
      background: #0f172a;
      color: #fff;
      padding: 10px 18px;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .no-print h4 {
      margin: 0;
      font-size: 13.5px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .no-print .btn-group {
      display: flex;
      gap: 8px;
    }
    .no-print button {
      background: #2563eb;
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: 5px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .no-print button:hover {
      background: #1d4ed8;
    }
    .no-print button.secondary {
      background: #334155;
    }
    .no-print button.secondary:hover {
      background: #475569;
    }

    /* Double Border Outer Container (Matching Physical Form) */
    .citpc-sheet {
      max-width: 800px;
      margin: 0 auto 24px auto;
      background: #fff;
      border: 1px solid #000;
      padding: 4px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }

    .citpc-inner-frame {
      border: 1.5px solid #000;
      padding: 18px 22px;
    }

    .citpc-title {
      font-size: 14px;
      font-weight: 800;
      margin-bottom: 12px;
      color: #000;
    }

    /* Top 4-Row Table */
    .top-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 12px;
    }
    .top-table td {
      border: 1px solid #000;
      padding: 6px 8px;
      vertical-align: top;
      font-size: 11px;
    }
    .top-table td.lbl {
      width: 32%;
      font-weight: 700;
    }
    .top-table td.val {
      width: 68%;
    }

    .request-type-header {
      font-size: 11px;
      margin: 8px 0 6px 0;
      line-height: 1.4;
    }

    .request-type-box {
      margin: 4px 0 14px 12px;
      font-size: 11px;
      line-height: 1.5;
    }

    /* Section Tables */
    .sec-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 10px;
    }
    .sec-table td {
      border: 1px solid #000;
      padding: 6px 8px;
      vertical-align: top;
      font-size: 11px;
      line-height: 1.4;
    }
    .sec-table td.sec-lbl {
      width: 32%;
      font-weight: 700;
    }
    .sec-table td.sec-val {
      width: 68%;
      white-space: pre-wrap;
    }

    .chk-box {
      display: inline-block;
      width: 13px;
      height: 13px;
      border: 1px solid #000;
      text-align: center;
      line-height: 12px;
      font-size: 11px;
      font-weight: bold;
      vertical-align: middle;
      margin-right: 6px;
    }
  </style>
</head>
<body>

  <!-- Floating Control Bar -->
  <div class="no-print">
    <h4>📋 IT CITPC note – ${esc(proc.code || 'Form')}</h4>
    <div class="btn-group">
      <button onclick="window.print()">🖨️ Print Form</button>
      <button class="secondary" onclick="window.close()">✕ Close</button>
    </div>
  </div>

  <!-- Page 1 / Sheet 1 -->
  <div class="citpc-sheet">
    <div class="citpc-inner-frame">

      <div class="citpc-title">IT CITPC note:</div>

      <table class="top-table">
        <tr>
          <td class="lbl">Title</td>
          <td class="val">${esc(title)}</td>
        </tr>
        <tr>
          <td class="lbl">Division</td>
          <td class="val">${esc(division)}</td>
        </tr>
        <tr>
          <td class="lbl">Name of the indenter</td>
          <td class="val">${esc(indenterName)}</td>
        </tr>
        <tr>
          <td class="lbl">CITPC Approval Is Required (Yes/No)</td>
          <td class="val">${esc(citpcRequired)}</td>
        </tr>
      </table>

      <div class="request-type-header">
        Select either one of the request type &ndash; Select Sub Type Name Correctly from the .txt file enclosed.
      </div>

      <div class="request-type-box">
        <div style="font-weight:700; margin-bottom:4px;">${esc(requestType)}</div>
        <div style="margin-left:14px;">
          <div>A. Type: ${esc(typeHardware)}</div>
          <div>B. Sub Type Name: ${esc(subTypeName)}</div>
          <div>C. OK with CITPC Lead Time: ${esc(leadTimeOk)}</div>
          <div style="font-size:10.5px; color:#333;">(If no, attach DMM's approval along with the expected lead time, to take this request in fast track)</div>
        </div>
      </div>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Background:</td>
          <td class="sec-val">${esc(background)}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Need:</td>
          <td class="sec-val">${esc(need)}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Requirement details with breakup of Delivery Location(s):</td>
          <td class="sec-val">${esc(reqDetails)}</td>
        </tr>
      </table>

    </div>
  </div>

  <!-- Page 2 / Sheet 2 (Continuous / Page-break for Print) -->
  <div class="citpc-sheet page-break">
    <div class="citpc-inner-frame">

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Vendors Considered:</td>
          <td class="sec-val">${esc(vendorsConsidered)}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Attach Technical Evaluation (if any):</td>
          <td class="sec-val">${esc(techEvaluation)}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">
            If negotiation carried out by division<br>
            Please provide Negotiation history &amp; Price movement:
          </td>
          <td class="sec-val">${esc(negotiationHistory)}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">
            In case you are seeking approval of a specific Service Provider/Product Brand, please tick any of the following:
          </td>
          <td class="sec-val" style="white-space:normal;">
            <div style="margin-bottom:6px;">
              <span class="chk-box">${brandOptions.capacity_aug ? '✓' : ''}</span>
              I. Capacity Augmentation of existing infrastructure
            </div>
            <div style="margin-bottom:6px;">
              <span class="chk-box">${brandOptions.standardized ? '✓' : ''}</span>
              II. Software/ Hardware item(s) standardized by ITSC
            </div>
            <div style="margin-bottom:8px;">
              <span class="chk-box">${brandOptions.cio_approved ? '✓' : ''}</span>
              III. Approved by CIO in writing
            </div>
            <div style="font-weight:700; margin-top:4px;">Please attach CIO's approval (if any)</div>
          </td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Attach Proposals</td>
          <td class="sec-val">${esc(attachProposals) || '&nbsp;'}</td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">
            I certify that the above proposals meet our scope of work/ Technical Specifications (Y/N)
          </td>
          <td class="sec-val" style="white-space:normal;">
            <div style="font-weight:700; margin-bottom:14px;">${esc(scopeCertified)}</div>
            <div style="margin-top:20px; border-top:1px dashed #666; width:180px; text-align:center; padding-top:4px; font-size:10px; color:#444;">
              ${esc(indenterName)}<br>(Indenter Signature)
            </div>
          </td>
        </tr>
      </table>

      <table class="sec-table">
        <tr>
          <td class="sec-lbl">Additional Information (if any)</td>
          <td class="sec-val">${esc(additionalInfo) || '&nbsp;'}</td>
        </tr>
      </table>

    </div>
  </div>

  <script>
    if (new URLSearchParams(window.location.search).get('autoprint') === '1') {
      window.addEventListener('load', () => setTimeout(() => window.print(), 350));
    }
  </script>
</body>
</html>`;
}

// ---- Official 3-Way Match & Invoice Clearance Certificate HTML ----
function invoiceVoucherHtml(inv, po, proc, vendor, settings) {
  const matchPass = inv.match_status === 'MATCHED' || !inv.match_status;
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>3-Way Match Audit Certificate - ${esc(inv.invoice_no)}</title>
<style>
  @media print {
    @page { size: portrait; margin: 10mm 12mm; }
    body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; padding: 0 !important; }
    .no-print { display: none !important; }
  }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 0; padding: 20px; color: #0f172a; font-size: 12px; background: #fff; line-height: 1.5; }
  .no-print { position: sticky; top: 0; z-index: 1000; background: #0f172a; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.25); margin-bottom: 16px; border-radius: 6px; }
  .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 14px; margin-bottom: 18px; }
  .co-name { font-size: 20px; font-weight: 800; color: #1e3a8a; }
  .co-sub { font-size: 11.5px; color: #475569; margin-top: 3px; }
  .doc-title { text-align: center; margin: 16px 0; padding: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; }
  .doc-title h2 { margin: 0; font-size: 16px; color: #0f172a; letter-spacing: 0.03em; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 18px; }
  .card { border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 14px; background: #f8fafc; }
  .card-h { font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 11.5px; }
  th, td { border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }
  th { background: #f1f5f9; font-weight: 700; color: #1e293b; font-size: 11px; }
  .num { text-align: right; }
  .center { text-align: center; }
  .badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 11px; }
  .b-green { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
  .b-red { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
  .sign-sec { margin-top: 50px; display: flex; justify-content: space-between; page-break-inside: avoid; }
  .sign-box { width: 30%; border-top: 1px solid #0f172a; text-align: center; padding-top: 8px; font-size: 11px; }
</style>
</head><body>
  <div class="no-print">
    <div style="font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 10px;">
      <span>🧾 3-Way Match & Invoice Clearance Certificate — ${esc(inv.invoice_no)}</span>
      <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">(${esc(vendor ? vendor.name : 'Supplier')})</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span style="font-size: 11px; color: #cbd5e1;">Tip: Select "Save as PDF" to download</span>
      <button onclick="window.print()" style="background: #2563eb; color: #fff; border: 0; padding: 7px 18px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
        🖨️ Print / Save as PDF
      </button>
      <button onclick="window.close()" style="background: rgba(255,255,255,0.15); color: #fff; border: 0; padding: 7px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">
        ✕ Close
      </button>
    </div>
  </div>
  <div class="header">
    <div>
      <div class="co-name">${esc(settings.company || 'Enterprise Supply Chain Ltd')}</div>
      <div class="co-sub">${esc(settings.company_address || '')} &bull; GSTIN: <b>${esc(settings.company_gst || 'N/A')}</b> &bull; PAN: <b>${esc(settings.company_pan || 'N/A')}</b></div>
    </div>
    <div style="text-align:right; font-size:11px; color:#475569;">
      <div><b>Certificate Ref:</b> 3WM-${esc(inv.id)}-${esc(inv.invoice_no)}</div>
      <div><b>Generated:</b> ${new Date().toLocaleString('en-IN')}</div>
    </div>
  </div>

  <div class="doc-title">
    <h2>OFFICIAL 3-WAY MATCHING &amp; TAX INVOICE CLEARANCE CERTIFICATE</h2>
    <div style="font-size:11.5px; color:#64748b; margin-top:3px;">Statutory Verification of Purchase Order &bull; Physical Store GRN &bull; Vendor Tax Invoice</div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-h">VENDOR / CLAIMANT DETAILS</div>
      <div style="font-size:13px; font-weight:700; color:#0f172a;">${esc((vendor && vendor.name) || (po && po.vendor_name) || 'Vendor')}</div>
      <div style="color:#475569; font-size:11.5px; margin-top:4px;">GSTIN: <b>${esc((vendor && vendor.gst) || 'N/A')}</b></div>
      <div style="color:#475569; font-size:11.5px;">Address: ${esc((vendor && vendor.address) || '—')}</div>
    </div>
    <div class="card">
      <div class="card-h">INVOICE &amp; ORDER REFERENCES</div>
      <div>Invoice Number: <b>${esc(inv.invoice_no)}</b></div>
      <div>Invoice Date: <b>${dmy(inv.invoice_date)}</b></div>
      <div>Linked PO Number: <b>${esc(po ? po.po_no : proc.po_no || 'PO Linked')}</b></div>
      <div>Requisition Indent: <b>${esc(proc.code)} — ${esc(proc.title)}</b></div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Verification Component</th>
        <th>Reference Code</th>
        <th>Audited Entity</th>
        <th class="num">Audited Financial Amount (₹)</th>
        <th class="center">Audit Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><b>1. Purchase Order Sanction</b></td>
        <td>${esc(po ? po.po_no : 'PO Linked')}</td>
        <td>Commercial Price &amp; Quantity Sanction</td>
        <td class="num"><b>${money(po ? po.total_landed : inv.total_amount)}</b></td>
        <td class="center"><span class="badge b-green">✔ Sanctioned</span></td>
      </tr>
      <tr>
        <td><b>2. Store Material Receipt (GRN)</b></td>
        <td>GRN Inward</td>
        <td>Physical Inward &amp; Quality Inspection (QC)</td>
        <td class="num">${money(po ? po.total_landed : inv.total_amount)}</td>
        <td class="center"><span class="badge b-green">✔ 100% Inward OK</span></td>
      </tr>
      <tr>
        <td><b>3. Vendor Tax Invoice Claim</b></td>
        <td>${esc(inv.invoice_no)}</td>
        <td>Tax Invoice Breakdown (Base: ${money(inv.amount)} + GST: ${money(inv.gst_amount)})</td>
        <td class="num"><b>${money(inv.total_amount)}</b></td>
        <td class="center"><span class="badge ${matchPass ? 'b-green' : 'b-red'}">${matchPass ? '✔ MATCHED' : 'DISCREPANCY'}</span></td>
      </tr>
    </tbody>
    <tfoot>
      <tr style="background:#f1f5f9; font-weight:700;">
        <td colspan="3">FINAL PASSED SETTLEMENT AMOUNT</td>
        <td class="num" style="color:#1e3a8a; font-size:13px;">${money(inv.total_amount)}</td>
        <td class="center"><span class="badge b-green">${esc(inv.payment_status || 'Paid')}</span></td>
      </tr>
    </tfoot>
  </table>

  <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; margin-top:16px;">
    <b>Settlement &amp; Statutory Payment Details:</b>
    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin-top:6px; font-size:11.5px;">
      <div>Payment Status: <b>${esc(inv.payment_status || 'Unpaid')}</b></div>
      <div>Payment Date: <b>${inv.payment_date ? dmy(inv.payment_date) : 'N/A'}</b></div>
      <div>UTR / RTGS Ref: <b>${esc(inv.utr_no || 'Direct RTGS / NEFT')}</b></div>
    </div>
    ${inv.remarks ? `<div style="margin-top:6px; color:#475569; font-size:11px;">Remarks: <i>${esc(inv.remarks)}</i></div>` : ''}
  </div>

  <div class="sign-sec">
    <div class="sign-box">
      <div style="font-weight:700;">PREPARED &amp; CHECKED BY</div>
      <div style="color:#64748b; font-size:10px;">Accounts Officer (Inward Verification)</div>
    </div>
    <div class="sign-box">
      <div style="font-weight:700;">AUDITED &amp; CERTIFIED BY</div>
      <div style="color:#64748b; font-size:10px;">Internal Audit &amp; Taxation Lead</div>
    </div>
    <div class="sign-box">
      <div style="font-weight:700;">PASSED FOR PAYMENT</div>
      <div style="color:#64748b; font-size:10px;">Plant Finance Controller / Head of Finance</div>
    </div>
  </div>
  <script>window.onload = () => { if (!window.location.search.includes('noprint')) setTimeout(() => window.print(), 350); };</script>
</body></html>`;
}

// ---- Standard Corporate Logic Note (Pixel-Perfect Match to Photo) ----
const NATURE = [
  ['Repair of machinery', 'Repair of building', 'Project Work', 'Housekeeping', 'Painting', 'Electrical', 'Others -'],
  ['Installation/Commissioning', 'EHS incl. fire safety', 'Material handling', 'Machine movement', 'Fabrication', 'Civil work'],
  ['Landscaping/gardening', 'Waste sorting', 'Loading/unloading', 'Process Improvement', 'Piping/plumbing', 'Carpentry work']
];

function dmyDots(d) {
  if (!d) return '';
  const s = String(d).slice(0, 10);
  const parts = s.split(/[-./]/);
  if (parts.length === 3) {
    if (parts[0].length === 4) return `${parts[2].padStart(2, '0')}.${parts[1].padStart(2, '0')}.${parts[0]}`;
    return `${parts[0].padStart(2, '0')}.${parts[1].padStart(2, '0')}.${parts[2]}`;
  }
  return s;
}

const numFmt = n => Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function logicHtml(p, s, items, qs, fv, comms, files, u) {
  const qtype = p.type === 'capex' ? 'initial' : 'final';
  const use = validOf(qs, qtype);
  const ini = validOf(qs, 'initial');
  const quoteList = use.length ? use : ini;

  const cols = quoteList.map(q => {
    let b = 0, l = 0, n = 0;
    for (const x of q.qitems) {
      const it = items.find(i => i.id === x.item_id);
      if (it && x.rate > 0) {
        b += x.rate * it.qty;
        l += gt(x.rate, x.gst) * it.qty;
        n++;
      }
    }
    return { q, b, l, n, full: n === items.length };
  });

  const full = cols.filter(c => c.full).sort((a, b) => a.l - b.l);
  cols.forEach(c => (c.rank = c.full ? 'L' + (full.indexOf(c) + 1) : `Partial (${c.n}/${items.length})`));

  const tot = fv.reduce((a, i) => a + gt(i.final_rate || 0, i.final_gst) * i.qty, 0);
  const nv = new Set(quoteList.map(q => q.vendor_id || q.vendor)).size;
  const rec = p.awarded_vendor_name || p.citpc_vendor || [...new Set(fv.map(i => i.v).filter(Boolean))].join(', ') || (full[0]?.q?.vendor) || (quoteList[0]?.vendor) || '—';

  // Triangle logo emblem matching the photo
  const defaultEmblem = `
    <svg width="44" height="38" viewBox="0 0 44 38" fill="none" style="display:block; margin:0 auto;">
      <polygon points="22,2 42,35 2,35" stroke="#000" stroke-width="2" fill="none"/>
      <text x="22" y="24" font-family="Arial, sans-serif" font-size="11" font-weight="bold" text-anchor="middle" fill="#000">A</text>
      <text x="22" y="32" font-family="Arial, sans-serif" font-size="5" text-anchor="middle" fill="#000">Leadership with Trust</text>
    </svg>`;
  const logoHtml = s.logo ? `<img src="${s.logo}" style="max-height:44px; display:block; margin:0 auto;">` : defaultEmblem;

  const noteDate = dmyDots(p.hod_date || p.pr_date || today());

  const css = `
    <style>
      @page { size: A4 portrait; margin: 8mm 12mm; }
      * { box-sizing: border-box; }
      body { font-family: Arial, sans-serif; font-size: 11px; line-height: 1.35; color: #000; margin: 0; padding: 0; background: #fff; }
      .box { border: 1.5px solid #000; width: 100%; }
      .sec { border-bottom: 1px solid #000; padding: 4px 8px; }
      .sec-last { padding: 4px 8px; }
      table { border-collapse: collapse; }
      .q-table td, .q-table th { border: 1px solid #000; padding: 3px 6px; }
      .q-table th { background: #fff; text-align: center; font-weight: bold; font-size: 10.5px; }
      .text-justify { text-align: justify; }
      @media print {
        .an { page-break-before: always; }
        .no-print { display: none !important; }
      }
    </style>`;

  return `<!doctype html><html><head><meta charset="utf-8"><title>Logic Note – ${p.code}</title>${css}</head><body>
  <div class="no-print" style="position: sticky; top: 0; z-index: 1000; background: #0f172a; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.25); margin-bottom: 16px; border-radius: 6px;">
    <div style="font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 10px;">
      <span>📄 Logic Note Sanction Memo — ${esc(p.code)}</span>
      <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">(${esc(p.title)})</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span style="font-size: 11px; color: #cbd5e1;">Tip: Select "Save as PDF" to download official file</span>
      <button onclick="window.print()" style="background: #2563eb; color: #fff; border: 0; padding: 7px 18px; border-radius: 6px; font-weight: 700; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(37,99,235,0.4);">
        🖨️ Print / Save as PDF
      </button>
      <button onclick="window.close()" style="background: rgba(255,255,255,0.15); color: #fff; border: 0; padding: 7px 14px; border-radius: 6px; font-size: 12px; cursor: pointer;">
        ✕ Close
      </button>
    </div>
  </div>
  <script>
    window.onload = () => {
      if (!window.location.search.includes('noprint')) {
        setTimeout(() => window.print(), 350);
      }
    };
  </script>
  <div class="box">
    <!-- Top Header: Date, Logo -->
    <div style="border-bottom: 1.5px solid #000; padding: 4px 8px; display: flex; justify-content: space-between; align-items: center; min-height: 44px;">
      <div style="font-weight: bold; font-size: 11px;">Date - ${noteDate}</div>
      <div style="text-align: center;">
        ${logoHtml}
      </div>
      <div style="width: 100px;"></div>
    </div>

    <!-- HOD Box Row -->
    <table style="width: 100%; border-collapse: collapse; border-bottom: 1.5px solid #000;">
      <tr>
        <td style="width: 50%; border-right: 1.5px solid #000; text-align: center; vertical-align: top; padding: 4px 8px; height: 38px;">
          <b style="font-size: 11px;">HOD</b>
        </td>
        <td style="width: 50%; vertical-align: top; padding: 4px 8px;"></td>
      </tr>
    </table>

    <!-- Background -->
    <div class="sec">
      <b>Background:</b><br>
      <div class="text-justify" style="margin-top: 2px;">${nl(p.business_req)}</div>
    </div>

    <!-- Technical Details -->
    <div class="sec">
      <b>Technical Details:</b><br>
      <div class="text-justify" style="margin-top: 2px;">${nl(p.tech)}</div>
    </div>

    <!-- Nature of work -->
    <div class="sec">
      <b>Nature of work :</b> ${esc(p.nature_text)}
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 4px; font-size: 10px; line-height: 1.25;">
        <div>
          Repair of machinery<br>
          Repair of building<br>
          Project Work<br>
          Housekeeping<br>
          Painting<br>
          Electrical<br>
          Others -
        </div>
        <div>
          Installation/Commissioning<br>
          EHS incl. fire safety<br>
          Material handling<br>
          Machine movement<br>
          Fabrication<br>
          Civil work
        </div>
        <div>
          Landscaping/gardening<br>
          Waste sorting<br>
          Loading/unloading<br>
          Process Improvement<br>
          Piping/plumbing<br>
          Carpentry work
        </div>
      </div>
    </div>

    <!-- Budget Heads -->
    <div class="sec">
      <b>Budget Heads:</b>
      <table style="width: 100%; border-collapse: collapse; font-size: 10.5px; margin-top: 2px;">
        <tr>
          <td style="width: 50%; padding: 1px 0; border: none;">Cost Centre - <b>${esc(p.cost_centre || '')}</b></td>
          <td style="width: 50%; padding: 1px 0; border: none;">Capex/HOPE (Pls tick as appropriate)</td>
        </tr>
        <tr>
          <td style="padding: 1px 0; border: none;">GL code - ${esc(p.gl_code || '')}</td>
          <td style="padding: 1px 0; border: none;">IO Number - ${esc(p.io_number || '')}</td>
        </tr>
        <tr>
          <td style="padding: 1px 0; border: none;">Is budget available - ${esc(p.budget_available || 'Yes/No')}</td>
          <td style="padding: 1px 0; border: none;">GL code - ${esc(p.io_gl || '')}</td>
        </tr>
        <tr>
          <td style="padding: 1px 0; border: none;">Estimated cash flow (Rs) ${p.cash_flow ? `- ${esc(p.cash_flow)}` : ''}</td>
          <td style="padding: 1px 0; border: none;"></td>
        </tr>
      </table>
    </div>

    <!-- Justification -->
    <div class="sec">
      <b>Justification:-</b> ${nl(p.final_reason)}
    </div>

    <!-- Competitive Quotation Table -->
    <table style="width: 100%; border-collapse: collapse; border-bottom: 1.5px solid #000; font-size: 10.5px;">
      <tr style="border-bottom: 1px solid #000;">
        <td style="width: 62%; padding: 3px 8px; border-right: 1.5px solid #000;">Is competitive quotation available</td>
        <td style="width: 38%; padding: 3px 8px;">Yes / No</td>
      </tr>
      <tr>
        <td style="padding: 3px 8px; border-right: 1.5px solid #000;">No of Competitive quotes</td>
        <td style="padding: 3px 8px;">${nv}</td>
      </tr>
    </table>

    <!-- Quantitative Analysis Table -->
    <div class="sec">
      <b>Quantitative analysis</b>
      <div style="margin: 6px 20px 8px;">
        <table class="q-table" style="width: 100%; border-collapse: collapse; font-size: 10px; border: 1.5px solid #000;">
          <thead>
            <tr>
              <th style="width: 120px; border: 1px solid #000; padding: 4px;"></th>
              ${cols.map(c => `<th style="border: 1px solid #000; padding: 4px; text-align: center; text-transform: uppercase;">${esc(c.q.vendor)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #000; padding: 3px 6px;">Quotation ref</td>
              ${cols.map(c => `<td style="border: 1px solid #000; padding: 3px 6px; text-align: center;">${esc(c.q.ref || '—')}</td>`).join('')}
            </tr>
            <tr>
              <td style="border: 1px solid #000; padding: 3px 6px;">Quotation date</td>
              ${cols.map(c => `<td style="border: 1px solid #000; padding: 3px 6px; text-align: center;">${dmy(c.q.qdate)}</td>`).join('')}
            </tr>
            <tr style="height: 10px;">
              <td style="border: 1px solid #000; padding: 0;">&nbsp;</td>
              ${cols.map(() => `<td style="border: 1px solid #000; padding: 0;">&nbsp;</td>`).join('')}
            </tr>
            <tr>
              <td style="border: 1px solid #000; padding: 3px 6px;">Basic price</td>
              ${cols.map(c => `<td style="border: 1px solid #000; padding: 3px 6px; text-align: center;">${numFmt(c.b)}</td>`).join('')}
            </tr>
            <tr>
              <td style="border: 1px solid #000; padding: 3px 6px;">Landed Price</td>
              ${cols.map(c => `<td style="border: 1px solid #000; padding: 3px 6px; text-align: center;">${numFmt(c.l)}</td>`).join('')}
            </tr>
            <tr style="height: 10px;">
              <td style="border: 1px solid #000; padding: 0;">&nbsp;</td>
              ${cols.map(() => `<td style="border: 1px solid #000; padding: 0;">&nbsp;</td>`).join('')}
            </tr>
            <tr>
              <td style="border: 1px solid #000; padding: 3px 6px; font-weight: bold;">Ranking</td>
              ${cols.map(c => `<td style="border: 1px solid #000; padding: 3px 6px; text-align: center; font-weight: bold;">${c.rank}</td>`).join('')}
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Qualitative Evaluation -->
    <div class="sec">
      <b>Qualitative Evaluation</b>
      <div style="border: 1px solid #000; padding: 8px 12px; margin: 4px 20px; min-height: 24px; font-size: 10.5px;">
        ${nl(p.qual_eval || 'Vendor has the required expertise and tools for the scope of work.')}
      </div>
    </div>

    <!-- Recommended Vendor & Indenter Signature -->
    <div class="sec-last" style="min-height: 48px; position: relative;">
      <b>Name of Vendor recommended for above job</b>
      <div style="text-align: center; font-size: 12.5px; font-weight: bold; margin: 4px 0 2px;">
        ${esc(rec)}
      </div>
      ${p.selection_basis ? `<div style="text-align: center; font-size: 10px; color: #475569; margin-bottom: 12px;">(Basis of Award: ${esc(p.selection_basis)})</div>` : '<div style="margin-bottom: 12px;"></div>'}
      <div style="text-align: right; font-size: 10.5px; font-weight: bold;">
        Signature of Indenter
      </div>
    </div>
  </div>
  </body></html>`;
}

// ---- Workflow Actions ----
function setStage(p, st, msg, u) {
  if (st === 'completed') {
    run("update proc set stage=?,is_locked=1,unlock_status=coalesce(nullif(unlock_status,''),'locked'),updated=? where id=?", st, now(), p.id);
    p.is_locked = 1;
    if (!p.unlock_status) p.unlock_status = 'locked';
  } else {
    run('update proc set stage=?,updated=? where id=?', st, now(), p.id);
  }
  audit(u, p.id, msg);
  p.stage = st;
}

function act(p, a, j, u) {
  const s = S();
  const items = all('select * from items where proc_id=?', p.id);
  const qs = loadQuotes(p, s, items);
  const exp = st => { if (p.stage !== st) throw E('This action is not available at the current stage'); };

  if (!items.length && a !== 'back') throw E('Add at least one item first');
  const qtype = p.type === 'capex' ? 'initial' : 'final';

  if (a === 'to_negotiation') {
    exp('quotations');
    if (p.type !== 'revenue') throw E('Not for capex');
    const v = vendorsOf(validOf(qs, 'initial'));
    const n = need(p, s);
    if (v < n) throw E(`Need ${n} valid vendor quotations (have ${v})`);
    const m = covered(validOf(qs, 'initial'), items);
    if (m.length) throw E('No valid quotation yet for: ' + m.map(i => i.name).join(', '));
    setStage(p, 'negotiation', 'Moved to negotiation stage', u);
  } else if (a === 'to_final') {
    exp('negotiation');
    setStage(p, 'final', 'Moved to final quotations stage', u);
  } else if (a === 'finalize') {
    exp(p.type === 'capex' ? 'quotations' : 'final');
    const v = validOf(qs, qtype);
    if (!v.length) throw E('No valid ' + qtype + ' quotation');
    const m = covered(v, items);
    if (m.length) throw E('No valid quotation for: ' + m.map(i => i.name).join(', '));

    // Audit Rule: All initial quotation vendors must submit final revised quotations
    if (p.type === 'revenue' && !j.force) {
      const initQuotes = validOf(qs, 'initial');
      const finalQuotes = validOf(qs, 'final');
      const finalVendorIds = new Set(finalQuotes.map(q => q.vendor_id));
      const missingVendors = initQuotes.filter(iq => !finalVendorIds.has(iq.vendor_id));
      if (missingVendors.length > 0) {
        throw E(`Final Revised Quotations are required for all Round 1 vendors. Missing final quotes for: ${missingVendors.map(q => q.vendor).join(', ')}`);
      }
    }
    for (const i of items) {
      let b = null;
      for (const q of v) {
        const x = q.qitems.find(y => y.item_id === i.id && y.rate > 0);
        if (x && (!b || gt(x.rate, x.gst) < gt(b.x.rate, b.x.gst))) b = { q, x };
      }
      run('update items set final_vendor_id=?,final_rate=?,final_gst=? where id=?', b.q.vendor_id || 0, b.x.rate, b.x.gst, i.id);
    }
    setStage(p, 'pr', 'Quotations finalised (lowest valid rate per item selected)', u);
  } else if (a === 'pr_done') {
    exp('pr');
    const prNo = j.pr_no || `SAP-PR-${p.code.replace(/[^\d]/g, '') || '0001'}`;
    run('update proc set pr_no=?,pr_date=? where id=?', prNo, j.date || today(), p.id);
    setStage(p, 'logic', 'SAP PR recorded: ' + prNo, u);
  } else if (a === 'gen_logic') {
    if (['quotations', 'negotiation', 'final', 'pr', 'cst'].includes(p.stage)) {
      setStage(p, 'logic', 'Advanced to Logic Note stage', u);
    }
    if (!['logic', 'hod', 'commercial', 'approvals', 'order', 'completed'].includes(p.stage)) {
      exp('logic');
    }
    // Auto-finalize items if quotes exist
    const qtype = p.type === 'capex' ? 'initial' : 'final';
    const v = validOf(qs, qtype).length ? validOf(qs, qtype) : validOf(qs, 'initial');
    if (v.length) {
      for (const i of items) {
        if (!i.final_rate) {
          let b = null;
          for (const q of v) {
            const x = q.qitems.find(y => y.item_id === i.id && y.rate > 0);
            if (x && (!b || gt(x.rate, x.gst) < gt(b.x.rate, b.x.gst))) b = { q, x };
          }
          if (b) {
            run('update items set final_vendor_id=?,final_rate=?,final_gst=? where id=?', b.q.vendor_id || 0, b.x.rate, b.x.gst, i.id);
            i.final_vendor_id = b.q.vendor_id || 0;
            i.final_rate = b.x.rate;
            i.final_gst = b.x.gst;
          }
        }
      }
    }
    const fv = items.map(i => ({ ...i, v: one('select name from vendors where id=?', i.final_vendor_id)?.name || '' }));
    const comms = all('select * from comms where proc_id=? order by at', p.id);
    const att = path.join(DOCS, p.code, 'LogicNote', 'attachments');
    fs.mkdirSync(att, { recursive: true });
    const files = all("select * from docs where proc_id=? and category in ('Quotations','FinalQuotations','Emails')", p.id);
    for (const f of files) try { fs.copyFileSync(path.join(DD, f.path), path.join(att, f.name)); } catch {}
    const html = logicHtml(p, s, items, qs, fv, comms, files, u);
    saveDoc(p, 'LogicNote', '', 'logic-note.html', Buffer.from(html), u);
    setStage(p, 'hod', 'Official Logic Note generated', u);
  } else if (a === 'hod_done') {
    exp('hod');
    if (!j.date) throw E('Enter the HOD sign date');
    run('update proc set hod_date=? where id=?', j.date, p.id);
    setStage(p, 'commercial', 'HOD signed on ' + j.date, u);
  } else if (a === 'comm_done') {
    exp('commercial');
    if (!j.date) throw E('Enter the commercial submission date');
    run('update proc set comm_date=? where id=?', j.date, p.id);
    s.approvers.forEach((x, k) => run('insert into approvals(proc_id,seq,name,desig) values(?,?,?,?)', p.id, k + 1, x.name, x.desig || ''));
    p.comm_date = j.date;
    setStage(p, s.approvers.length ? 'approvals' : 'order', 'Submitted to commercial on ' + j.date, u);
  } else if (a === 'approve_step') {
    exp('approvals');
    const r = one('select * from approvals where proc_id=? and date is null order by seq', p.id);
    if (!r) throw E('Nothing pending');
    if (!j.date) throw E('Enter approval date');
    const prev = one('select date from approvals where proc_id=? and seq<? order by seq desc', p.id, r.seq)?.date || p.comm_date;
    if (prev && j.date < prev) throw E('Approval date cannot be before ' + prev);
    run('update approvals set date=?,remark=?,by=? where id=?', j.date, j.remark || '', u.username, r.id);
    audit(u, p.id, `${r.name} approved on ${j.date}`);
    if (!one('select 1 from approvals where proc_id=? and date is null', p.id)) {
      setStage(p, 'order', 'All SAP approvals complete – Ready for PO generation', u);
    } else {
      run('update proc set updated=? where id=?', now(), p.id);
    }
  } else if (a === 'set_order') {
    if (!['order', 'completed'].includes(p.stage)) throw E('PO/SO numbers are entered after all approvals');
    if (!j.no) throw E('Enter SAP PO/SO number');
    if (!(j.item_ids || []).length) throw E('Select at least one item');
    for (const id of j.item_ids) run('update items set sap_no=?,sap_date=? where id=? and proc_id=?', j.no, j.date || today(), id, p.id);
    audit(u, p.id, `SAP ${p.kind.toUpperCase()} ${j.no} recorded for ${j.item_ids.length} item(s)`);
    const op = one("select 1 from items where proc_id=? and (sap_no is null or sap_no='')", p.id);
    if (!op && p.stage === 'order') {
      setStage(p, 'completed', 'All items have SAP order numbers – Requisition completed', u);
    } else {
      run('update proc set updated=? where id=?', now(), p.id);
    }
  } else if (a === 'close_proc') {
    const remarks = j.remarks || 'Material received and Factory Asset capitalized – Requisition formally closed';
    run("update proc set is_locked=1,unlock_status='locked',closed_at=?,closed_by=?,close_remarks=?,updated=? where id=?", now(), u.name || u.username, remarks, now(), p.id);
    p.is_locked = 1;
    p.unlock_status = 'locked';
    setStage(p, 'completed', remarks, u);
  } else if (a === 'back') {
    const f = FLOW[p.type];
    const i = f.indexOf(p.stage);
    if (i <= 0) throw E('Already at first stage');
    if (p.stage === 'approvals' || f[i - 1] === 'approvals') run('delete from approvals where proc_id=?', p.id);
    setStage(p, f[i - 1], 'Moved back to ' + f[i - 1], u);
  } else {
    throw E('Unknown action');
  }
}

// ---- Backup & Restore ----
const stamp = () => new Date().toISOString().replace(/[-:T]/g, '').slice(0, 12);
function backup(label) {
  const n = 'backup-' + stamp() + (label ? '-' + label : '');
  const d = path.join(BAK, n);
  fs.mkdirSync(d, { recursive: true });
  db.exec(`VACUUM INTO '${path.join(d, 'procure.db').replace(/'/g, "''")}'`);
  if (S().backupDocs) fs.cpSync(DOCS, path.join(d, 'documents'), { recursive: true });
  const l = fs.readdirSync(BAK).filter(x => x.startsWith('backup-') && !x.includes('prerestore')).sort();
  while (l.length > S().backupKeep) fs.rmSync(path.join(BAK, l.shift()), { recursive: true, force: true });

  // Remote Network Share Backup Sync
  const remoteBackupDir = cfg.remoteBackupDir || process.env.REMOTE_BACKUP_DIR || (typeof S === 'function' && S().remoteBackupDir);
  if (remoteBackupDir) {
    try {
      const rd = path.join(remoteBackupDir, n);
      fs.mkdirSync(rd, { recursive: true });
      fs.copyFileSync(path.join(d, 'procure.db'), path.join(rd, 'procure.db'));
      if (S().backupDocs && fs.existsSync(DOCS)) {
        fs.cpSync(DOCS, path.join(rd, 'documents'), { recursive: true });
      }
      console.log(`[Remote Backup] Successfully synced snapshot '${n}' to: ${rd}`);
      try {
        const rl = fs.readdirSync(remoteBackupDir).filter(x => x.startsWith('backup-') && !x.includes('prerestore')).sort();
        while (rl.length > S().backupKeep) fs.rmSync(path.join(remoteBackupDir, rl.shift()), { recursive: true, force: true });
      } catch {}
    } catch (rErr) {
      console.warn(`[Remote Backup Warning] Could not mirror snapshot to remote share (${remoteBackupDir}): ${rErr.message}`);
    }
  }

  return n;
}

function restore(n) {
  const d = path.join(BAK, path.basename(n));
  if (!fs.existsSync(path.join(d, 'procure.db'))) throw E('Backup not found', 404);
  backup('prerestore');
  db.close();
  fs.copyFileSync(path.join(d, 'procure.db'), DBF);
  if (fs.existsSync(path.join(d, 'documents'))) fs.cpSync(path.join(d, 'documents'), DOCS, { recursive: true, force: true });
  open();
  sessions.clear();
}

// ---- Quotation CRUD ----
function saveQuote(p, id, j) {
  const v = one('select * from vendors where id=?', j.vendor_id);
  if (!v) throw E('Select a vendor from the vendor list');
  const items = all('select * from items where proc_id=?', p.id);
  if (id) {
    run('update quotes set vendor_id=?,vendor=?,address=?,gst=?,recipient=?,qdate=?,delivery=?,ref=?,delivery_days=?,payment_terms=?,warranty=?,freight=? where id=?',
      v.id, v.name, v.address, v.gst, j.recipient, j.qdate, j.delivery, j.ref || '', j.delivery_days || 'Immediate', j.payment_terms || '30 days', j.warranty || '1 Year', +j.freight || 0, id);
    if (j.doc_id !== undefined) run('update quotes set doc_id=? where id=?', j.doc_id, id);
    if (j.mail_doc_id !== undefined) run('update quotes set mail_doc_id=? where id=?', j.mail_doc_id, id);
  } else {
    id = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms,warranty,freight,doc_id,mail_doc_id) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      p.id, j.type === 'final' ? 'final' : 'initial', v.id, v.name, v.address, v.gst, j.recipient, j.qdate, j.delivery, j.ref || '', j.delivery_days || 'Immediate', j.payment_terms || '30 days', j.warranty || '1 Year', +j.freight || 0, j.doc_id || null, j.mail_doc_id || null).lastInsertRowid);
  }
  run('delete from qitems where quote_id=?', id);
  for (const x of j.items || []) {
    if (+x.rate > 0 && items.some(i => i.id == x.item_id)) {
      run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', id, x.item_id, +x.rate, +x.gst || 0);
    }
  }
  return id;
}

// ---- Sample Demo Data Generator ----
function seedDemoData(force = false) {
  const user = { username: 'admin' };
  // Check if vendors exist, else seed
  if (!one('select 1 from vendors')) {
    const demoVendors = [
      { name: 'Siemens India Industrial Ltd', gst: '27AAACS1234A1Z5', address: 'Plot 2, Kalwa Industrial Estate, Thane, Maharashtra 400601', contact: 'Rajesh Sharma', phone: '+91 98201 12345', email: 'rajesh.sharma@siemens.com', pan: 'AAACS1234A', msme_type: 'Medium', bank_name: 'HDFC Bank', bank_ac: '50200012345678', ifsc: 'HDFC0000123', rating: 4.8 },
      { name: 'Larsen & Toubro Electrical Systems', gst: '27AAACL0123B1Z2', address: 'Gate 1, Powai Campus, Saki Vihar Road, Mumbai 400072', contact: 'Amit Deshmukh', phone: '+91 98334 56789', email: 'amit.d@larsentoubro.com', pan: 'AAACL0123B', msme_type: 'Large', bank_name: 'State Bank of India', bank_ac: '31234567890', ifsc: 'SBIN0000456', rating: 4.9 },
      { name: 'Schneider Electric India Pvt Ltd', gst: '29AAACS5678C1Z8', address: 'Attibele Industrial Area, Bangalore, Karnataka 562107', contact: 'Pooja Iyer', phone: '+91 97401 23456', email: 'pooja.iyer@se.com', pan: 'AAACS5678C', msme_type: 'Large', bank_name: 'Citibank', bank_ac: '0123456789', ifsc: 'CITI0000002', rating: 4.7 },
      { name: 'Polycab Wires & Cables Ltd', gst: '24AAACP4321D1Z1', address: 'Halol Industrial Area, Vadodara, Gujarat 389350', contact: 'Nitin Patel', phone: '+91 98980 98765', email: 'nitin.patel@polycab.com', pan: 'AAACP4321D', msme_type: 'Large', bank_name: 'Axis Bank', bank_ac: '912010023456789', ifsc: 'UTIB0000123', rating: 4.6 },
      { name: 'Atlas Copco India Compressor Ltd', gst: '27AAACA9876E1Z4', address: 'Dapodi Industrial Area, Pune, Maharashtra 411012', contact: 'Manoj Joshi', phone: '+91 98220 54321', email: 'manoj.joshi@atlascopco.com', pan: 'AAACA9876E', msme_type: 'Medium', bank_name: 'Kotak Mahindra Bank', bank_ac: '7812345678', ifsc: 'KKBK0000123', rating: 4.8 }
    ];
    for (const v of demoVendors) {
      run('insert into vendors(name,gst,address,contact,phone,email,pan,msme_type,bank_name,bank_ac,ifsc,rating) values(?,?,?,?,?,?,?,?,?,?,?,?)',
        v.name, v.gst, v.address, v.contact, v.phone, v.email, v.pan, v.msme_type, v.bank_name, v.bank_ac, v.ifsc, v.rating);
    }
  }

  // Seed Item Master Catalog
  if (!one('select 1 from item_master')) {
    const catalog = [
      { code: 'ITM-EL-001', name: '4-Core 16 sq mm Armoured Copper Cable', descr: '1100V grade, XLPE insulated, galvanized steel wire armoured', category: 'Electrical', unit: 'mtr', hsn: '8544', citpc_rate: 650 },
      { code: 'ITM-ME-002', name: 'Industrial Cast Steel Gate Valve 4 inch', descr: 'Class 150 flanged ends, API 600 compliant, with handwheel', category: 'Mechanical', unit: 'nos', hsn: '8481', citpc_rate: 18500 },
      { code: 'ITM-EL-003', name: '15 HP 3-Phase Squirrel Cage Induction Motor', descr: '415V, 1440 RPM, Foot Mounted (B3), IE3 High Efficiency', category: 'Electrical', unit: 'nos', hsn: '8501', citpc_rate: 48000 },
      { code: 'ITM-IT-004', name: 'Dell Precision 3660 Workstation Tower', descr: 'Intel i7 13th Gen, 32GB DDR5 RAM, 1TB NVMe SSD, RTX A2000', category: 'IT & Automation', unit: 'nos', hsn: '8471', citpc_rate: 145000 },
      { code: 'ITM-SR-005', name: 'Annual Maintenance Service for Plant Chillers', descr: 'Comprehensive quarterly preventive maintenance and breakdown coverage', category: 'Service & Maintenance', unit: 'job', hsn: '9987', citpc_rate: 180000 }
    ];
    for (const c of catalog) {
      run('insert into item_master(code,name,descr,category,unit,hsn,citpc_rate,created) values(?,?,?,?,?,?,?,?)',
        c.code, c.name, c.descr, c.category, c.unit, c.hsn, c.citpc_rate, today());
    }
  }

  // Create Sample Requisitions if none exist
  if (!one('select 1 from proc')) {
    const s = S();
    // 1. Completed Procurement with full PO, GRN & 3-Way Match
    const p1Code = `${s.prefix}-0001-2026`;
    const r1 = run('insert into proc(code,type,kind,title,dept,location,est,stage,requester,created,updated,priority,po_no,po_date,grn_status,invoice_status,business_req,tech,cost_centre,gl_code,budget_type,final_reason) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      p1Code, 'revenue', 'po', 'Substation Transformer Feeder Cables Replacement', 'Electrical & Utilities', 'Plant Substation 3', 380000, 'completed', 'admin', today(), today(), 'urgent', 'PO-2026-0001', today(), 'completed', 'matched',
      'The existing feeder cables from Substation 3 to MCC-2 showed insulation breakdown and high thermal heating during routine infrared thermography inspection. Immediate replacement is critical to avoid unplanned factory shutdown.',
      '4-Core 16 sq mm copper armoured cable compliant with IS 7098 (Part 1). Length 500 meters required with test certificates.',
      'CC-ELEC-401', 'GL-720100', 'HOPE', 'Polycab Wires Ltd is L1 technically and commercially qualified. Quoted lowest landed rate after negotiation.');
    const pid1 = Number(r1.lastInsertRowid);
    const itm1 = Number(run('insert into items(proc_id,name,descr,model,qty,unit,hsn,final_vendor_id,final_rate,final_gst,sap_no,sap_date,received_qty,accepted_qty) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, '4-Core 16 sq mm Armoured Copper Cable', '1100V XLPE insulated, IS 7098', 'Polycab Heavy Duty', 500, 'mtr', '8544', 4, 620, 18, 'PO-2026-0001', today(), 500, 500).lastInsertRowid);

    // Initial and Final Quotes
    const q1 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, 'initial', 4, 'Polycab Wires & Cables Ltd', 'Halol, Gujarat', '24AAACP4321D1Z1', s.company, today(), 'Plant Substation 3', 'POL/2026/901', '7 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q1, itm1, 660, 18);

    const q2 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, 'initial', 2, 'Larsen & Toubro Electrical Systems', 'Powai, Mumbai', '27AAACL0123B1Z2', s.company, today(), 'Plant Substation 3', 'LT/QT/8842', '10 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q2, itm1, 690, 18);

    const q3 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, 'initial', 3, 'Schneider Electric India Pvt Ltd', 'Bangalore, Karnataka', '29AAACS5678C1Z8', s.company, today(), 'Plant Substation 3', 'SE/2026/041', '14 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q3, itm1, 710, 18);

    // Final Quotes (after negotiation)
    const qf = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, 'final', 4, 'Polycab Wires & Cables Ltd', 'Halol, Gujarat', '24AAACP4321D1Z1', s.company, today(), 'Plant Substation 3', 'POL/2026/901-REV', '5 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', qf, itm1, 620, 18);

    // Purchase Order
    const po1 = Number(run('insert into pos(proc_id,po_no,po_date,vendor_id,vendor_name,total_basic,total_gst,total_landed,payment_terms,delivery_terms,billing_address,delivery_address,status,terms_text,created_by,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, 'PO-2026-0001', today(), 4, 'Polycab Wires & Cables Ltd', 310000, 55800, 365800, '30 days from GRN', 'Within 7 days', s.company_address, 'Plant Substation 3', 'Closed', s.po_terms, 'admin', now()).lastInsertRowid);
    run('insert into po_items(po_id,item_id,name,descr,qty,unit,rate,gst,hsn,total) values(?,?,?,?,?,?,?,?,?,?)',
      po1, itm1, '4-Core 16 sq mm Armoured Copper Cable', '1100V XLPE insulated', 500, 'mtr', 620, 18, '8544', 365800);

    // GRN (Material Received)
    const grn1 = Number(run('insert into grns(proc_id,po_id,grn_no,grn_date,challan_no,challan_date,vehicle_no,received_by,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?)',
      pid1, po1, 'GRN-2026-0001', today(), 'DC-POL-5489', today(), 'MH-04-AB-4567', 'Kailash Patil (Store Officer)', 'All 500 meters received on drum, visual and insulation tests verified OK.', now()).lastInsertRowid);
    run('insert into grn_items(grn_id,item_id,po_item_id,received_qty,accepted_qty,rejected_qty,rejection_reason) values(?,?,?,?,?,?,?)',
      grn1, itm1, 1, 500, 500, 0, '');

    // Invoice with 3-Way Match Verified
    run('insert into invoices(proc_id,po_id,invoice_no,invoice_date,amount,gst_amount,total_amount,match_status,payment_status,payment_date,utr_no,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?)',
      pid1, po1, 'INV-POL-2026-088', today(), 310000, 55800, 365800, 'MATCHED', 'Paid', today(), 'HDFCR52026048921', '3-Way Match 100% verified. Payment released via RTGS.', now());

    // 2. Active Revenue Requisition in Negotiation / Comparative Statement stage
    const p2Code = `${s.prefix}-0002-2026`;
    const r2 = run('insert into proc(code,type,kind,title,dept,location,est,stage,requester,created,updated,priority,business_req,tech,cost_centre,gl_code,budget_type) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      p2Code, 'revenue', 'po', 'Procurement of High-Pressure Gate Valves for Boiler Line', 'Mechanical Maintenance', 'Boiler House Unit 1', 190000, 'negotiation', 'admin', today(), today(), 'normal',
      'Regular overhaul and replacement of worn steam valves during scheduled annual shutdown in Boiler House 1.',
      '4-inch Class 150 flanged ends, carbon steel body ASTM A216 WCB with SS 316 trim, pressure rating 150#.',
      'CC-MECH-204', 'GL-710200', 'HOPE');
    const pid2 = Number(r2.lastInsertRowid);
    const itm2 = Number(run('insert into items(proc_id,name,descr,model,qty,unit,hsn) values(?,?,?,?,?,?,?)',
      pid2, 'Industrial Cast Steel Gate Valve 4 inch', 'Class 150 flanged, API 600 compliant', 'Audco / L&T', 10, 'nos', '8481').lastInsertRowid);

    // Add 3 vendor quotes for comparative evaluation
    const q21 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid2, 'initial', 2, 'Larsen & Toubro Electrical Systems', 'Powai, Mumbai', '27AAACL0123B1Z2', s.company, today(), 'Boiler House Unit 1', 'LT/VLV/409', '15 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q21, itm2, 17800, 18);

    const q22 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid2, 'initial', 1, 'Siemens India Industrial Ltd', 'Thane, Maharashtra', '27AAACS1234A1Z5', s.company, today(), 'Boiler House Unit 1', 'SIE/QT/552', '21 days', '30 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q22, itm2, 18900, 18);

    const q23 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
      pid2, 'initial', 3, 'Schneider Electric India Pvt Ltd', 'Bangalore, Karnataka', '29AAACS5678C1Z8', s.company, today(), 'Boiler House Unit 1', 'SE/VAL/889', '25 days', '45 days').lastInsertRowid);
    run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', q23, itm2, 19500, 18);

    // 3. Active Capex Requisition with CITPC deadline
    const p3Code = `${s.prefix}-0003-2026`;
    const deadlineDate = new Date(Date.now() + 4 * 864e5).toISOString().slice(0, 10);
    const r3 = run('insert into proc(code,type,kind,title,dept,location,est,stage,requester,created,updated,priority,citpc_ref,citpc_date,citpc_vendor,business_req,tech,cost_centre,gl_code,budget_type) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      p3Code, 'capex', 'po', 'High Performance CAD/CAM Engineering Workstations (CITPC Approved)', 'Engineering & Design', 'Design Centre - 4th Floor', 435000, 'quotations', 'admin', today(), today(), 'urgent',
      'CITPC/2026/CAP-412', today(), 'Larsen & Toubro Electrical Systems',
      'Capacity expansion for new EV component CAD 3D modeling and structural simulation.',
      'Precision CAD Workstation Tower, 32GB DDR5, RTX Professional GPU.',
      'CC-ENG-102', 'GL-120500', 'Capex');
    const pid3 = Number(r3.lastInsertRowid);
    run('insert into items(proc_id,name,descr,model,qty,unit,hsn,citpc_rate,last_date) values(?,?,?,?,?,?,?,?,?)',
      pid3, 'Dell Precision 3660 Workstation Tower', 'Intel i7 13th Gen, 32GB RAM, 1TB SSD, RTX A2000', 'Dell Precision 3660', 3, 'nos', '8471', 145000, deadlineDate);

    audit(user, null, 'Demo enterprise sample data initialized successfully.');
  }

  // Ensure rich IT Capex Requisition exists with CITPC Note & Completion Certificate
  if (force || !one("select 1 from proc where citpc_note is not null and citpc_note != ''")) {
    const s = S();
    const existingCapex = one("select id from proc where citpc_note is not null and citpc_note != ''");
    if (!existingCapex) {
      const nextId = (one('select max(id) as m from proc')?.m || 0) + 1;
      const pCode = `${s.prefix}-${String(nextId).padStart(4, '0')}-2026`;
      const citpcJson = JSON.stringify({
        title: 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Modules and 7 Years Support for Pune Factory under Replacement with Implementation. - Nos:-22',
        division: 'ITD',
        indenter_name: 'Amitava Mukherjee',
        citpc_required: 'Yes',
        request_type: 'Request Type I',
        type_hardware: 'Hardware',
        subtype_name: 'Standard Switches / Routers.',
        lead_time_ok: 'Yes',
        background: 'The existing 24 Port Access Switches deployed across Pune Factory have completed their useful lifecycle of 7 years and have been written off. These switches are used to provide network connectivity across the factory through various VLANs to desktops, printers, IP phones, wireless access points, and other network-connected devices. Due to aging hardware, increasing network utilization, and lack of OEM support, replacement of the existing switches is required to ensure network reliability, improved performance, enhanced security, and uninterrupted business operations.',
        need: 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Uplink Modules, DNA Term License, Dual Power Supply, and 7 Years OEM Support for replacement of existing obsolete access switches at Pune Factory.',
        req_details: 'Standard 24 Port UTP PoE Layer 2 Switch with 24 PoE ports, 4 x 10G Enterprise Class SFP uplink ports and 1/10G SFP modules, DNA Term License, Dual Power Supply, Indian Power Cables, all necessary installation accessories, implementation services, and 7 years OEM warranty & support.\nQuantity: 22 Nos\nDelivery Location: Pune Factory ITC Ranjangaon.',
        vendors_considered: 'As per CITPC Approval. Considered: Cisco Systems, Aruba HPE, Dell Technologies. Sample Quote enclosed for reference only.',
        tech_evaluation: '1. Type: Layer 2 Managed Enterprise Switch with 24 UTP PoE ports, 4 x 10G SFP uplink ports and modules, enterprise-class hardware, VLAN, QoS, STP/RSTP, IPv4/IPv6, SNMP, SSH, Web Management, Dual Power Supply, Stacking Capability, DNA Term License, and 7 years OEM warranty & support.',
        negotiation_history: 'NA',
        brand_options: { capacity_aug: false, standardized: true, cio_approved: false },
        attach_proposals: 'Sample Quote enclosed for reference only.',
        scope_certified: 'Y',
        additional_info: ''
      });

      const certJson = JSON.stringify({
        company_name: s.company || 'ITC LIMITED',
        factory_name: 'ITD - RANJANGAON CIGARETTE FACTORY',
        plant_address: 'PLOT-B27, MIDC, RANJANGAON, PUNE - 412220',
        io_no: '10064019',
        io_desc: 'Standard 24 Port UTP PoE Layer 2 Switch, Enterprise Rackmount',
        po_no: 'PO-2026-0002',
        install_date: today(),
        location: 'MIS ITC PUNFCT',
        model_name: 'Cisco Catalyst 24-Port PoE Switch C9200L',
        serial_numbers: 'SN-84920-01, SN-84920-02, SN-84920-03, SN-84920-04',
        remarks: 'Installation and Commissioning successfully completed and verified.',
        asset_count: '22 Nos',
        project_incharge: 'Amitava Mukherjee',
        head_of_user_dept: 'Head of IT Department',
        commercial_items: [
          { particular: 'SN-84920-01', sap_asset_no: 'AST-2026-001' },
          { particular: 'SN-84920-02', sap_asset_no: 'AST-2026-002' },
          { particular: 'SN-84920-03', sap_asset_no: 'AST-2026-003' },
          { particular: 'SN-84920-04', sap_asset_no: 'AST-2026-004' }
        ]
      });

      const rCapex = run(`insert into proc(code,type,kind,title,dept,location,est,stage,requester,created,updated,priority,po_no,po_date,grn_status,invoice_status,citpc_ref,citpc_date,citpc_vendor,business_req,tech,cost_centre,gl_code,budget_type,io_number,citpc_note,completion_cert,final_reason) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        pCode, 'capex', 'po', 'Standard 24 Port UTP PoE Layer 2 Switch Replacement for Pune Factory', 'ITD', 'Pune Factory ITC Ranjangaon', 2850000, 'completed', 'Amitava Mukherjee', today(), today(), 'urgent',
        'PO-2026-0002', today(), 'completed', 'matched', 'CITPC/2026/IT-SW-042', today(), 'Siemens India Industrial Ltd',
        'Replacement of obsolete 7-year-old network access switches across plant floor to prevent production downtime.',
        'Layer 2 Managed Enterprise Switch with 24 UTP PoE ports, 4 x 10G SFP uplinks, Dual Power Supply, DNA License, 7 Years OEM warranty.',
        'CC-IT-901', 'GL-120500', 'Capex', '10064019', citpcJson, certJson,
        'Siemens India Industrial Ltd is L1 technically and commercially qualified as per CITPC approved benchmark.');
      const capId = Number(rCapex.lastInsertRowid);

      const itmCap = Number(run('insert into items(proc_id,name,descr,model,qty,unit,hsn,citpc_rate,final_vendor_id,final_rate,final_gst,sap_no,sap_date,received_qty,accepted_qty) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, 'Standard 24 Port UTP PoE Layer 2 Switch', '24 PoE ports, 4x10G SFP, Dual PSU, DNA License', 'Cisco C9200L-24P-4X', 22, 'nos', '8517', 125000, 1, 118000, 18, 'PO-2026-0002', today(), 22, 22).lastInsertRowid);

      const qCap1 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, 'initial', 1, 'Siemens India Industrial Ltd', 'Kalwa, Thane', '27AAACS1234A1Z5', s.company, today(), 'Pune Factory ITC Ranjangaon', 'SIE/IT/409', '14 days', '30 days').lastInsertRowid);
      run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', qCap1, itmCap, 118000, 18);

      const qCap2 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, 'initial', 2, 'Larsen & Toubro Electrical Systems', 'Powai, Mumbai', '27AAACL0123B1Z2', s.company, today(), 'Pune Factory ITC Ranjangaon', 'LT/NET/884', '21 days', '30 days').lastInsertRowid);
      run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', qCap2, itmCap, 122000, 18);

      const qCap3 = Number(run('insert into quotes(proc_id,type,vendor_id,vendor,address,gst,recipient,qdate,delivery,ref,delivery_days,payment_terms) values(?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, 'initial', 3, 'Schneider Electric India Pvt Ltd', 'Bangalore, Karnataka', '29AAACS5678C1Z8', s.company, today(), 'Pune Factory ITC Ranjangaon', 'SE/NET/991', '30 days', '30 days').lastInsertRowid);
      run('insert into qitems(quote_id,item_id,rate,gst) values(?,?,?,?)', qCap3, itmCap, 126000, 18);

      const poCap = Number(run('insert into pos(proc_id,po_no,po_date,vendor_id,vendor_name,total_basic,total_gst,total_landed,payment_terms,delivery_terms,billing_address,delivery_address,status,terms_text,created_by,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, 'PO-2026-0002', today(), 1, 'Siemens India Industrial Ltd', 2596000, 467280, 3063280, '30 days after GRN & Verification', 'Within 14 days', s.company_address, 'Pune Factory ITC Ranjangaon', 'Closed', s.po_terms, 'admin', now()).lastInsertRowid);
      run('insert into po_items(po_id,item_id,name,descr,qty,unit,rate,gst,hsn,total) values(?,?,?,?,?,?,?,?,?,?)',
        poCap, itmCap, 'Standard 24 Port UTP PoE Layer 2 Switch', '24 PoE ports, 4x10G SFP, Dual PSU, DNA License', 22, 'nos', 118000, 18, '8517', 3063280);

      const grnCap = Number(run('insert into grns(proc_id,po_id,grn_no,grn_date,challan_no,challan_date,vehicle_no,received_by,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?)',
        capId, poCap, 'GRN-2026-0002', today(), 'DC-SIE-8819', today(), 'MH-12-CD-9988', 'Amitava Mukherjee (IT Engineer)', 'All 22 Nos switches received in factory sealed boxes, verified serial numbers & MAC IDs OK.', now()).lastInsertRowid);
      run('insert into grn_items(grn_id,item_id,po_item_id,received_qty,accepted_qty,rejected_qty,rejection_reason) values(?,?,?,?,?,?,?)',
        grnCap, itmCap, 1, 22, 22, 0, '');

      run('insert into invoices(proc_id,po_id,invoice_no,invoice_date,amount,gst_amount,total_amount,match_status,payment_status,payment_date,utr_no,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        capId, poCap, 'INV-SIE-2026-042', today(), 2596000, 467280, 3063280, 'MATCHED', 'Paid', today(), 'HDFCR52026099412', '3-Way Match 100% verified against PO and Store GRN.', now());

      for (let k = 1; k <= 4; k++) {
        const sapCode = `AST-2026-00${k}`;
        const serialNo = `SN-84920-0${k}`;
        run(`insert into assets(proc_id,po_id,item_id,asset_code,asset_name,category,capitalization_date,commissioning_date,put_to_use_date,plant_location,custodian,serial_no,cost,warranty_expiry,status,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
          capId, poCap, itmCap, sapCode, 'Cisco Catalyst 24-Port PoE Switch C9200L', 'IT Hardware', today(), today(), today(), 'Pune Factory ITC Ranjangaon', 'Amitava Mukherjee', serialNo, 139240, '2033-03-31', 'Capitalized & In-Service', 'Put-to-use certificate signed and tagged.', now());
      }
      audit(user, capId, 'Enterprise IT Capex Requisition and statutory forms initialized.');
    }
  }
}

// ---- HTTP Server & Router ----
const sessions = new Map();
const fails = new Map();
const send = (res, c, o, h = {}) => {
  res.writeHead(c, { 'Content-Type': 'application/json', ...h });
  res.end(JSON.stringify(o));
};
const sendHtml = (res, html) => {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html);
};
const body = req => new Promise(r => {
  const c = [];
  let n = 0;
  req.on('data', d => { n += d.length; if (n < 2e8) c.push(d); });
  req.on('end', () => r(Buffer.concat(c)));
});

const mime = {
  '.html': 'text/html;charset=utf-8',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain',
  '.csv': 'text/csv',
  '.doc': 'application/msword',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.xls': 'application/vnd.ms-excel',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
};
const CATS = ['Quotations', 'FinalQuotations', 'Emails', 'LogicNote', 'CompletionCert', 'CITPCNote', 'HOD', 'SAP', 'Invoices', 'PurchaseOrder', 'GRN', 'Challan', 'Bills', 'Warranty', 'CapexDocs', 'Other'];

const requestHandler = async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const P = url.pathname;
    const M = req.method;

    // Static SPA HTML
    if (!P.startsWith('/api/')) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(fs.readFileSync(path.join(__dirname, 'public', 'index.html')));
    }

    if (P === '/api/health') {
      return send(res, 200, { ok: 1, name: 'ProcureLocal', port: cfg.port, time: now() });
    }

    if (P === '/api/system/network-info' && M === 'GET') {
      const os = require('os');
      const nets = os.networkInterfaces();
      const lanIps = [];
      for (const name of Object.keys(nets)) {
        for (const net of nets[name]) {
          if (net.family === 'IPv4' && !net.internal) {
            lanIps.push({ iface: name, ip: net.address });
          }
        }
      }
      const isRemote = DD.startsWith('\\\\') || (/^[a-zA-Z]:/.test(DD) && path.resolve(DD) !== path.resolve(__dirname, 'DB'));
      return send(res, 200, {
        ok: 1,
        name: 'ProcureLocal Enterprise Central Server',
        port: cfg.port,
        host: cfg.host,
        dataDir: DD,
        isRemote,
        remoteType: DD.startsWith('\\\\') ? 'Windows UNC Network Share (NAS)' : (isRemote ? 'Mapped Network Drive' : 'Local Standalone Directory'),
        remoteStatus: fs.existsSync(DD) ? 'Connected & Active' : 'Offline / Inaccessible',
        dbFile: DBF,
        docsVault: DOCS,
        lanIps,
        serverUrls: lanIps.map(x => `http://${x.ip}:${cfg.port}`).concat([`http://localhost:${cfg.port}`]),
        polyglot: {
          cs: { name: 'C# Native Windows Launcher & Direct Thermal Spooler', file: 'ProcureLocal.exe', status: 'Active' },
          python: { name: 'Python Spend Analytics, Tally Bridge & Excel Automation', dir: 'python/', status: 'Active' },
          java: { name: 'Java Enterprise SAP RFC & Batch Processor', dir: 'java/', status: 'Active' },
          node: { name: 'Node.js 22 LTS Embedded SQLite Core Engine', version: process.version, status: 'Active' }
        }
      });
    }

    if (P === '/api/heartbeat') {
      lastUiPing = Date.now();
      uiConnected = true;
      return send(res, 200, { ok: 1, time: lastUiPing });
    }

    if (P === '/api/shutdown' && M === 'POST') {
      send(res, 200, { ok: 1, message: 'Shutting down server' });
      setTimeout(() => process.exit(0), 400);
      return;
    }

    const raw = await body(req);
    let j = {};
    if (raw.length && (req.headers['content-type'] || '').includes('json')) {
      try { j = JSON.parse(raw.toString()); } catch {}
    }

    // Remote Shared Storage Configuration & Diagnostics Endpoints
    if (P === '/api/system/test-storage' && M === 'POST') {
      const target = (j.dataDir || '').trim();
      if (!target) return send(res, 400, { ok: 0, error: 'Target directory path is required' });
      try {
        fs.mkdirSync(target, { recursive: true });
        const probeFile = path.join(target, '.procure_rw_probe');
        fs.writeFileSync(probeFile, 'test');
        fs.unlinkSync(probeFile);
        return send(res, 200, { ok: 1, accessible: true, path: target, message: 'Network share is accessible with Read/Write permissions.' });
      } catch (err) {
        return send(res, 400, { ok: 0, error: 'Cannot access network shared path: ' + err.message });
      }
    }

    if (P === '/api/system/configure-storage' && M === 'POST') {
      const target = (j.dataDir || '').trim();
      if (!target) return send(res, 400, { ok: 0, error: 'Target directory path is required' });
      try {
        fs.mkdirSync(target, { recursive: true });
        const probeFile = path.join(target, '.procure_rw_probe');
        fs.writeFileSync(probeFile, 'test');
        fs.unlinkSync(probeFile);

        const cfgPath = path.join(__dirname, 'config.json');
        let curCfg = {};
        try { curCfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8')); } catch {}
        curCfg.dataDir = target;
        fs.writeFileSync(cfgPath, JSON.stringify(curCfg, null, 2), 'utf8');

        return send(res, 200, { ok: 1, dataDir: target, message: 'Remote Shared Database path saved to config.json. Please restart ProcureLocal to mount the remote network share.' });
      } catch (err) {
        return send(res, 400, { ok: 0, error: 'Cannot configure remote shared path: ' + err.message });
      }
    }

    // Remote Backup Mirroring Diagnostics & Configuration Endpoints
    if (P === '/api/system/test-backup-remote' && M === 'POST') {
      const target = (j.remoteBackupDir || '').trim();
      if (!target) return send(res, 400, { ok: 0, error: 'Target remote backup path is required' });
      try {
        fs.mkdirSync(target, { recursive: true });
        const probeFile = path.join(target, '.procure_bak_probe');
        fs.writeFileSync(probeFile, 'backup_test');
        fs.unlinkSync(probeFile);
        return send(res, 200, { ok: 1, accessible: true, path: target, message: 'Remote backup destination is accessible with Write permissions.' });
      } catch (err) {
        return send(res, 400, { ok: 0, error: 'Cannot access remote backup path: ' + err.message });
      }
    }

    if (P === '/api/system/configure-backup-remote' && M === 'POST') {
      const target = (j.remoteBackupDir || '').trim();
      try {
        if (target) {
          fs.mkdirSync(target, { recursive: true });
          const probeFile = path.join(target, '.procure_bak_probe');
          fs.writeFileSync(probeFile, 'backup_test');
          fs.unlinkSync(probeFile);
        }

        const cfgPath = path.join(__dirname, 'config.json');
        let curCfg = {};
        try { curCfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8')); } catch {}
        curCfg.remoteBackupDir = target;
        cfg.remoteBackupDir = target;
        fs.writeFileSync(cfgPath, JSON.stringify(curCfg, null, 2), 'utf8');

        if (target) {
          try { backup('remote-init'); } catch (e) { console.warn('Initial remote backup note:', e.message); }
        }

        return send(res, 200, { ok: 1, remoteBackupDir: target, message: target ? 'Remote backup destination saved and verified. Database snapshots will automatically sync to this location.' : 'Remote backup destination disabled.' });
      } catch (err) {
        return send(res, 400, { ok: 0, error: 'Cannot configure remote backup path: ' + err.message });
      }
    }

    if (P === '/api/system/backup-info' && M === 'GET') {
      const remote = cfg.remoteBackupDir || '';
      let remoteOnline = false;
      let remoteCount = 0;
      if (remote) {
        try {
          if (fs.existsSync(remote)) {
            remoteOnline = true;
            remoteCount = fs.readdirSync(remote).filter(x => x.startsWith('backup-')).length;
          }
        } catch {}
      }
      return send(res, 200, {
        localBackupDir: BAK,
        remoteBackupDir: remote,
        remoteOnline: remoteOnline,
        remoteCount: remoteCount,
        backupHours: (typeof S === 'function' && S().backupHours) || 12,
        backupKeep: (typeof S === 'function' && S().backupKeep) || 14
      });
    }

    const ck = (req.headers.cookie || '').match(/sid=(\w+)/);
    let u = ck && sessions.get(ck[1]);

    // Public / Auth routes
    if (P === '/api/login' && M === 'POST') {
      const ip = req.socket.remoteAddress;
      if ((fails.get(ip) || 0) >= 10) return send(res, 429, { error: 'Too many failed login attempts. Please wait 15 minutes.' });
      const r = one('select * from users where username=? and active=1', String(j.username || ''));
      if (!r || !chk(String(j.password || ''), r.pw)) {
        fails.set(ip, (fails.get(ip) || 0) + 1);
        setTimeout(() => fails.delete(ip), 9e5);
        return send(res, 401, { error: 'Invalid username or password.' });
      }
      fails.delete(ip);
      const t = crypto.randomBytes(24).toString('hex');
      sessions.set(t, { id: r.id, username: r.username, name: r.name, role: r.role });
      audit(r, null, 'User signed in: ' + r.username);
      return send(res, 200, { ok: 1, user: { id: r.id, username: r.username, name: r.name, role: r.role } }, { 'Set-Cookie': `sid=${t}; HttpOnly; SameSite=Strict; Path=/` });
    }

    if (!u) return send(res, 401, { error: 'Authentication required. Please sign in.' });

    const adm = u.role === 'admin';
    const can = u.role !== 'viewer';
    const W = () => { if (!can) throw E('Viewer accounts have read-only access.', 403); };
    const getP = id => {
      const p = one('select * from proc where id=?', id);
      if (!p) throw E('Procurement requisition not found', 404);
      return p;
    };

    let m;

    if (P === '/api/me') return send(res, 200, { user: u, roles: ROLES, settings: S(), flow: FLOW });
    if (P === '/api/logout') {
      sessions.delete(ck[1]);
      return send(res, 200, { ok: 1 });
    }
    if (P === '/api/password' && M === 'POST') {
      if (String(j.password || '').length < 8) return send(res, 400, { error: 'Password must be at least 8 characters long.' });
      run('update users set pw=? where id=?', hash(j.password), u.id);
      audit(u, null, 'Password updated');
      return send(res, 200, { ok: 1 });
    }

    // 1-Click Demo Data Seed Endpoint
    if (P === '/api/demo-data' && M === 'POST') {
      W();
      seedDemoData();
      return send(res, 200, { ok: 1, message: 'Enterprise demo sample data loaded successfully!' });
    }

    // Executive Analytics Dashboard API
    if (P === '/api/analytics' && M === 'GET') {
      const procs = all('select * from proc');
      const allItems = all('select * from items');
      const allPos = all('select * from pos');
      const allInvoices = all('select * from invoices');

      // Helper to compute each requisition's true procurement value:
      // 1. If PO(s) issued: use sum of po.total_landed (or total_basic)
      // 2. Else if items have negotiated final_rate: use sum of gt(final_rate, final_gst) * qty
      // 3. Else: use p.est (Estimated Budget entered by user)
      const getProcVal = p => {
        const pPos = allPos.filter(po => po.proc_id === p.id);
        if (pPos.length > 0) {
          const poSum = pPos.reduce((sum, po) => sum + (Number(po.total_landed) || Number(po.total_basic) || 0), 0);
          if (poSum > 0) {
            return {
              val: poSum,
              hasPo: true,
              basic: pPos.reduce((s, po) => s + (Number(po.total_basic) || 0), 0),
              gst: pPos.reduce((s, po) => s + (Number(po.total_gst) || 0), 0)
            };
          }
        }
        const pItems = allItems.filter(i => i.proc_id === p.id && Number(i.final_rate) > 0);
        if (pItems.length > 0) {
          const itemSum = pItems.reduce((acc, i) => acc + (gt(i.final_rate || 0, i.final_gst) * (Number(i.qty) || 0)), 0);
          if (itemSum > 0) {
            return {
              val: itemSum,
              hasPo: false,
              basic: pItems.reduce((s, i) => s + ((Number(i.final_rate) || 0) * (Number(i.qty) || 0)), 0),
              gst: itemSum - pItems.reduce((s, i) => s + ((Number(i.final_rate) || 0) * (Number(i.qty) || 0)), 0)
            };
          }
        }
        const est = Number(p.est) || 0;
        return { val: est, hasPo: false, basic: est, gst: 0 };
      };

      let totalProcurementValue = 0;
      let capexSpend = 0;
      let revenueSpend = 0;
      let totalPoCommitted = 0;
      let totalPoBasic = 0;
      let totalPoGst = 0;
      let pipelineSpend = 0;
      let totalBudget = 0;

      const deptMap = {};

      procs.forEach(p => {
        const res = getProcVal(p);
        const pVal = res.val;
        totalProcurementValue += pVal;
        totalBudget += Number(p.est) || 0;

        if (res.hasPo) {
          totalPoCommitted += pVal;
          totalPoBasic += res.basic;
          totalPoGst += res.gst;
        } else {
          pipelineSpend += pVal;
        }

        if (p.type === 'capex') {
          capexSpend += pVal;
        } else {
          revenueSpend += pVal;
        }

        const deptName = p.dept || 'General';
        deptMap[deptName] = (deptMap[deptName] || 0) + pVal;
      });

      // Spend by Vendor (based on issued POs and finalized items)
      const vendorMap = {};
      allPos.forEach(po => {
        const vName = po.vendor_name || 'Unknown Vendor';
        vendorMap[vName] = (vendorMap[vName] || 0) + (Number(po.total_landed) || Number(po.total_basic) || 0);
      });
      allItems.filter(i => i.final_vendor_id && !allPos.some(po => po.proc_id === i.proc_id)).forEach(i => {
        const v = one('select name from vendors where id=?', i.final_vendor_id);
        const vName = v ? v.name : 'Unknown Vendor';
        vendorMap[vName] = (vendorMap[vName] || 0) + (gt(i.final_rate || 0, i.final_gst) * (Number(i.qty) || 0));
      });

      // Invoiced and Matched
      const totalInvoiced = allInvoices.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);
      const totalPaid = allInvoices.filter(inv => inv.payment_status === 'Paid').reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);

      // Pending action stats
      const pendingWithMap = {};
      procs.filter(p => !isProcLocked(p)).forEach(p => {
        const pend = pendingWith(p) || 'Unassigned';
        pendingWithMap[pend] = (pendingWithMap[pend] || 0) + 1;
      });

      return send(res, 200, {
        totalSpend: totalProcurementValue,
        totalProcurementValue,
        totalPoCommitted,
        totalPoBasic,
        totalPoGst,
        pipelineSpend,
        totalBudget,
        capexSpend,
        revenueSpend,
        totalInvoiced,
        totalPaid,
        activeCount: procs.filter(p => !isProcLocked(p)).length,
        completedCount: procs.filter(p => isProcLocked(p)).length,
        deptSpend: deptMap,
        vendorSpend: vendorMap,
        pendingWith: pendingWithMap
      });
    }

    // Enterprise 360° Deep Record Search & Equipment Tracking API
    if (P === '/api/search' && M === 'GET') {
      const q = (url.searchParams.get('q') || '').trim();
      const qType = (url.searchParams.get('type') || 'all').toLowerCase();
      if (!q) return send(res, 200, []);
      const qLower = q.toLowerCase();
      const qLike = '%' + qLower + '%';

      const isAll = !qType || qType === 'all';
      const isSap = isAll || qType === 'sap';
      const isSerial = isAll || qType === 'serial';
      const isItem = isAll || qType === 'item';
      const isInv = isAll || qType === 'invoice';
      const isPo = isAll || qType === 'po';
      const isVendor = isAll || qType === 'vendor';

      const matchesByProc = new Map();
      function addMatch(pid, tag, value, highlight) {
        if (!pid) return;
        if (!matchesByProc.has(pid)) matchesByProc.set(pid, []);
        const list = matchesByProc.get(pid);
        if (!list.some(m => m.tag === tag && String(m.value).toLowerCase() === String(value).toLowerCase())) {
          list.push({ tag, value: String(value), highlight: !!highlight });
        }
      }

      // 1. proc: code, title, dept, location, po_no, asset_code, pr_no, awarded_vendor_name, io_number, cost_centre
      if (isAll || isSap || isPo || isVendor || isItem) {
        const procs = all(`
          select id, code, title, dept, location, po_no, asset_code, pr_no, awarded_vendor_name, io_number, cost_centre
          from proc
          where lower(code) like ? or lower(title) like ? or lower(dept) like ? or lower(location) like ? or lower(po_no) like ? or lower(asset_code) like ? or lower(pr_no) like ? or lower(awarded_vendor_name) like ? or lower(io_number) like ? or lower(cost_centre) like ?
        `, qLike, qLike, qLike, qLike, qLike, qLike, qLike, qLike, qLike, qLike);

        for (const p of procs) {
          if (isAll && p.code && p.code.toLowerCase().includes(qLower)) addMatch(p.id, 'Requisition Code', p.code, true);
          if ((isAll || isItem) && p.title && p.title.toLowerCase().includes(qLower)) addMatch(p.id, 'Title', p.title, true);
          if (isAll && p.dept && p.dept.toLowerCase().includes(qLower)) addMatch(p.id, 'Department', p.dept, false);
          if (isAll && p.location && p.location.toLowerCase().includes(qLower)) addMatch(p.id, 'Location', p.location, false);
          if (isPo && p.po_no && p.po_no.toLowerCase().includes(qLower)) addMatch(p.id, 'Purchase Order', p.po_no, true);
          if (isSap && p.asset_code && p.asset_code.toLowerCase().includes(qLower)) addMatch(p.id, 'SAP Asset Code', p.asset_code, true);
          if (isVendor && p.awarded_vendor_name && p.awarded_vendor_name.toLowerCase().includes(qLower)) addMatch(p.id, 'Awarded Vendor', p.awarded_vendor_name, true);
          if (isAll && p.io_number && p.io_number.toLowerCase().includes(qLower)) addMatch(p.id, 'Internal Order (IO)', p.io_number, true);
        }
      }

      // 2. items: name, descr, model, sap_no, asset_code
      if (isAll || isItem || isSap) {
        const items = all(`
          select proc_id, id, name, descr, model, sap_no, asset_code
          from items
          where lower(name) like ? or lower(descr) like ? or lower(model) like ? or lower(sap_no) like ? or lower(asset_code) like ?
        `, qLike, qLike, qLike, qLike, qLike);

        for (const it of items) {
          if (isItem && it.name && it.name.toLowerCase().includes(qLower)) addMatch(it.proc_id, 'Item Name', it.name, true);
          if (isItem && it.model && it.model.toLowerCase().includes(qLower)) addMatch(it.proc_id, 'Model / Spec', it.model, true);
          if (isItem && it.descr && it.descr.toLowerCase().includes(qLower)) addMatch(it.proc_id, 'Description', it.descr, false);
          if (isSap && it.sap_no && it.sap_no.toLowerCase().includes(qLower)) addMatch(it.proc_id, 'SAP Material Code', it.sap_no, true);
          if (isSap && it.asset_code && it.asset_code.toLowerCase().includes(qLower)) addMatch(it.proc_id, 'SAP Asset Code', it.asset_code, true);
        }
      }

      // 3. assets: asset_code, serial_no, asset_name, plant_location, custodian
      if (isAll || isSap || isSerial || isItem) {
        const assets = all(`
          select proc_id, id, asset_code, serial_no, asset_name, plant_location, custodian
          from assets
          where lower(asset_code) like ? or lower(serial_no) like ? or lower(asset_name) like ? or lower(plant_location) like ? or lower(custodian) like ?
        `, qLike, qLike, qLike, qLike, qLike);

        for (const a of assets) {
          if (isSap && a.asset_code && a.asset_code.toLowerCase().includes(qLower)) addMatch(a.proc_id, 'SAP Asset Code', a.asset_code, true);
          if (isSerial && a.serial_no && a.serial_no.toLowerCase().includes(qLower)) addMatch(a.proc_id, 'OEM Serial No', a.serial_no, true);
          if (isItem && a.asset_name && a.asset_name.toLowerCase().includes(qLower)) addMatch(a.proc_id, 'Asset Name', a.asset_name, true);
          if (isAll && a.custodian && a.custodian.toLowerCase().includes(qLower)) addMatch(a.proc_id, 'Custodian', a.custodian, false);
        }
      }

      // 4. invoices: invoice_no, utr_no, remarks
      if (isAll || isInv) {
        const invoices = all(`
          select proc_id, id, invoice_no, utr_no, remarks
          from invoices
          where lower(invoice_no) like ? or lower(utr_no) like ? or lower(remarks) like ?
        `, qLike, qLike, qLike);

        for (const inv of invoices) {
          if (inv.invoice_no && inv.invoice_no.toLowerCase().includes(qLower)) addMatch(inv.proc_id, 'Vendor Invoice No', inv.invoice_no, true);
          if (inv.utr_no && inv.utr_no.toLowerCase().includes(qLower)) addMatch(inv.proc_id, 'Payment UTR No', inv.utr_no, true);
        }
      }

      // 5. pos: po_no, vendor_name, remarks
      if (isAll || isPo || isVendor) {
        const pos = all(`
          select proc_id, id, po_no, vendor_name, remarks
          from pos
          where lower(po_no) like ? or lower(vendor_name) like ? or lower(remarks) like ?
        `, qLike, qLike, qLike);

        for (const po of pos) {
          if (isPo && po.po_no && po.po_no.toLowerCase().includes(qLower)) addMatch(po.proc_id, 'PO Number', po.po_no, true);
          if (isVendor && po.vendor_name && po.vendor_name.toLowerCase().includes(qLower)) addMatch(po.proc_id, 'PO Vendor', po.vendor_name, true);
        }
      }

      // 6. grns: grn_no, challan_no, vehicle_no, received_by
      if (isAll) {
        const grns = all(`
          select proc_id, id, grn_no, challan_no, vehicle_no, received_by
          from grns
          where lower(grn_no) like ? or lower(challan_no) like ? or lower(vehicle_no) like ? or lower(received_by) like ?
        `, qLike, qLike, qLike, qLike);

        for (const g of grns) {
          if (g.grn_no && g.grn_no.toLowerCase().includes(qLower)) addMatch(g.proc_id, 'GRN / Inward No', g.grn_no, true);
          if (g.challan_no && g.challan_no.toLowerCase().includes(qLower)) addMatch(g.proc_id, 'Delivery Challan No', g.challan_no, true);
        }
      }

      // 7. vendors: name, gst, pan, contact
      if (isAll || isVendor) {
        const vendors = all(`
          select id, name from vendors
          where lower(name) like ? or lower(gst) like ? or lower(pan) like ? or lower(contact) like ?
        `, qLike, qLike, qLike, qLike);

        for (const v of vendors) {
          const qMatches = all('select proc_id from quotes where vendor_id = ? or lower(vendor) like ?', v.id, '%' + v.name.toLowerCase() + '%');
          for (const q of qMatches) {
            addMatch(q.proc_id, 'Vendor Directory', v.name, false);
          }
        }
      }

      const results = [];
      const s = S();
      for (const [procId, matches] of matchesByProc.entries()) {
        const proc = one('select * from proc where id=?', procId);
        if (!proc) continue;

        const procItems = all('select * from items where proc_id=?', procId);
        const procPos = all(`
          select po.*, d.name as doc_name
          from pos po
          left join docs d on d.id = po.doc_id
          where po.proc_id=?
          order by po.id desc
        `, procId);
        const procGrns = all('select * from grns where proc_id=? order by id desc', procId);
        const procInvoices = all(`
          select inv.*, d.name as doc_name
          from invoices inv
          left join docs d on d.id = inv.doc_id
          where inv.proc_id=?
          order by inv.id desc
        `, procId);
        const procAssets = all('select * from assets where proc_id=? order by id desc', procId);
        const procDocs = all('select id, category, name, orig, at, by from docs where proc_id=? order by id desc', procId);
        const quotes = loadQuotes(proc, s, procItems);

        results.push({
          procId,
          proc,
          isLocked: isProcLocked(proc),
          matches,
          items: procItems,
          pos: procPos,
          grns: procGrns,
          invoices: procInvoices,
          assets: procAssets,
          quotesCount: quotes.length,
          docsCount: procDocs.length
        });
      }

      return send(res, 200, results);
    }

    // Requisitions (procs)
    if (P === '/api/procs' && M === 'GET') {
      const s = S();
      return send(res, 200, all('select * from proc order by id desc').map(p => {
        const items = all('select * from items where proc_id=?', p.id);
        const qs = loadQuotes(p, s, items);
        const dl = items.filter(i => !i.sap_no && i.last_date).map(i => i.last_date).sort()[0];
        const poCount = all('select 1 from pos where proc_id=?', p.id).length;
        const grnCount = all('select 1 from grns where proc_id=?', p.id).length;
        const latestPo = one('select po_no, po_date, vendor_name from pos where proc_id=? order by id desc', p.id);
        return {
          ...p,
          po_no: p.po_no || latestPo?.po_no || null,
          po_date: p.po_date || latestPo?.po_date || null,
          vendor_name: latestPo?.vendor_name || null,
          items: items.length,
          need: need(p, s),
          validVendors: vendorsOf(validOf(qs, 'initial')),
          pending: pendingWith(p),
          deadline: p.type === 'capex' && p.stage !== 'completed' ? dl || null : null,
          value: items.reduce((a, i) => a + gt(i.final_rate || 0, i.final_gst) * i.qty, 0),
          poCount,
          grnCount
        };
      }));
    }

    if (P === '/api/procs' && M === 'POST') {
      W();
      const s = S();
      const code = getNextProcCode(s.prefix || 'PRC', s.fy_format || 'YYYY');
      if (!j.title || !j.location || !['capex', 'revenue'].includes(j.type) || !['po', 'so'].includes(j.kind)) {
        throw E('Type, PO/SO, Title and Delivery Location are mandatory.');
      }
      if (j.type === 'revenue' && !(+j.est > 0)) {
        throw E('Enter estimated value (required for the quotation threshold policy).');
      }
      const r = run('insert into proc(code,type,kind,title,dept,location,est,requester,created,updated,priority,notes,citpc_ref,citpc_date,citpc_vendor,business_req,tech,cost_centre,gl_code,budget_type) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        code, j.type, j.kind, j.title, j.dept || '', j.location, +j.est || 0, u.username, now(), now(), j.priority || 'normal', j.notes || '', j.citpc_ref || '', j.citpc_date || '', j.citpc_vendor || '', j.business_req || '', j.tech || '', j.cost_centre || '', j.gl_code || '', j.budget_type || '');
      fs.mkdirSync(path.join(DOCS, code), { recursive: true });
      const id = Number(r.lastInsertRowid);
      if (j.copy_from) {
        for (const i of all('select * from items where proc_id=?', j.copy_from)) {
          run('insert into items(proc_id,name,descr,model,qty,unit,hsn) values(?,?,?,?,?,?,?)', id, i.name, i.descr, i.model, i.qty, i.unit, i.hsn);
        }
      }
      audit(u, id, `Requisition created: ${code} (${j.title})`);
      return send(res, 200, { id });
    }

    if ((m = P.match(/^\/api\/procs\/(\d+)$/))) {
      const p = getP(m[1]);
      if (M === 'GET') {
        const s = S();
        const items = all('select * from items where proc_id=?', p.id);
        const quotes = loadQuotes(p, s, items).map(q => ({
          ...q,
          file: q.doc_id ? one('select name from docs where id=?', q.doc_id)?.name : null
        }));
        const hist = {};
        for (const i of items) {
          hist[i.id] = all(`select q.vendor,qi.rate,qi.gst,q.qdate,p.code from qitems qi join quotes q on q.id=qi.quote_id join proc p on p.id=q.proc_id join items i on i.id=qi.item_id where lower(i.name)=lower(?) and q.proc_id!=? order by q.qdate desc limit 3`, i.name, p.id);
        }
        const pos = all(`
          select po.*, d.name as doc_name
          from pos po
          left join docs d on d.id = po.doc_id
          where po.proc_id=?
          order by po.id desc
        `, p.id);
        const grns = all('select * from grns where proc_id=? order by id desc', p.id).map(g => ({
          ...g,
          items: all('select gi.*, i.name, i.qty as ordered_qty from grn_items gi left join items i on i.id=gi.item_id where gi.grn_id=?', g.id)
        }));
        const assets = all('select * from assets where proc_id=? order by id desc', p.id);
        const invoices = all(`
          select inv.*, d.name as doc_name, po.po_no, po.vendor_name
          from invoices inv
          left join docs d on d.id = inv.doc_id
          left join pos po on po.id = inv.po_id
          where inv.proc_id=?
          order by inv.id desc
        `, p.id);
        const cst = buildCstData(p, s, items, quotes);
        const unlockRequests = all('select * from unlock_requests where proc_id=? order by id desc', p.id);
        const lockedFlag = isProcLocked(p) ? 1 : 0;

        return send(res, 200, {
          p: {
            ...p,
            is_locked: lockedFlag
          },
          unlock_requests: unlockRequests,
          items: items.map(i => ({
            ...i,
            final_vendor: one('select name from vendors where id=?', i.final_vendor_id)?.name || ''
          })),
          quotes,
          need: need(p, s),
          hist,
          comms: all('select * from comms where proc_id=? order by at', p.id),
          docs: all('select * from docs where proc_id=? order by at', p.id),
          approvals: all('select * from approvals where proc_id=? order by seq', p.id),
          audit: all('select * from audit where proc_id=? order by id desc', p.id),
          pos,
          grns,
          assets,
          invoices,
          cst
        });
      }

      if (M === 'PUT') {
        W();
        checkProcNotLocked(p, u);
        const f = ['title', 'type', 'kind', 'dept', 'location', 'est', 'priority', 'po_no', 'po_date', 'business_req', 'tech', 'final_reason', 'citpc_ref', 'citpc_date', 'citpc_vendor', 'awarded_vendor_id', 'awarded_vendor_name', 'selection_basis', 'pr_no', 'pr_date', 'hod_date', 'comm_date', 'notes', 'nature_text', 'nature_ticks', 'cost_centre', 'gl_code', 'budget_available', 'cash_flow', 'budget_type', 'io_number', 'io_gl', 'qual_eval', 'payment_terms', 'delivery_terms', 'received_date', 'grn_status', 'asset_status', 'asset_code', 'capitalization_date', 'commissioning_date', 'plant_location', 'custodian', 'closed_at', 'closed_by', 'close_remarks'];
        const ch = [];
        for (const k of f) {
          if (j[k] !== undefined && String(j[k]) !== String(p[k] ?? '')) ch.push(`${k}: ${p[k] ?? ''} → ${j[k]}`);
        }
        run(`update proc set ${f.map(k => k + '=?').join(',')},updated=? where id=?`, ...f.map(k => j[k] ?? p[k]), now(), p.id);
        audit(u, p.id, 'Edited: ' + (ch.join('; ') || 'no change'));
        return send(res, 200, { ok: 1 });
      }

      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Requisitions');
        checkProcNotLocked(p, u);
        const del = path.join(DOCS, '_Deleted');
        fs.mkdirSync(del, { recursive: true });
        try { fs.renameSync(path.join(DOCS, p.code), path.join(del, p.code + '_' + stamp())); } catch {}
        run('delete from qitems where quote_id in (select id from quotes where proc_id=?)', p.id);
        for (const t of ['quotes', 'items', 'comms', 'docs', 'approvals', 'pos', 'po_items', 'grns', 'grn_items', 'invoices', 'assets']) {
          try { run(`delete from ${t} where proc_id=?`, p.id); } catch {}
        }
        run('delete from proc where id=?', p.id);
        audit(u, null, `SECURE DELETE: Requisition ${p.code} ("${p.title || ''}") permanently deleted by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/procs\/(\d+)\/action$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      if (isProcLocked(p) && j.act !== 'close_proc') {
        checkProcNotLocked(p, u);
      }
      act(p, j.act, j, u);
      return send(res, 200, { ok: 1 });
    }


    // ---- Statutory & Enterprise Standalone Form Templates Center ----
    if (P === '/api/forms/templates' && M === 'GET') {
      return send(res, 200, {
        templates: [
          { id: 'citpc_note', name: 'IT CITPC note', type: 'IT Committee Technical Sanction & Capex', desc: 'Corporate IT Procurement Committee sanction memo for switches, routers, workstations & IT infrastructure.', preview: '/api/forms/citpc-note/print', blank: '/api/forms/citpc-note/print?blank=1' },
          { id: 'completion_cert', name: 'Certificate of Completion', type: 'Commercial Put-to-Use & Handover', desc: 'Plant capitalization handover certificate with IO #, PO #, IMIE/Serial #, and dual signatures.', preview: '/api/forms/completion-cert/print', blank: '/api/forms/completion-cert/print?blank=1' },
          { id: 'logic_note', name: 'Sanction Logic Note', type: 'Vendor Selection & Financial Recommendation', desc: 'Official commercial justification document with multi-vendor comparison and L1 recommendation.', preview: '/api/forms/logic/print', blank: '/api/forms/logic/print?blank=1' },
          { id: 'cst_matrix', name: 'Comparative Statement (CST Matrix)', type: 'Tender Evaluation Matrix', desc: 'Statutory bid comparison matrix showing unit rates, GST, freight, landed cost comparisons, and L1/L2 ranking.', preview: '/api/forms/cst/print', blank: '/api/forms/cst/print?blank=1' },
          { id: 'po_template', name: 'Official Legal Purchase Order (PO/SO)', type: 'Commercial Plant Order Contract', desc: 'Standard plant Purchase Order format with GST, payment terms, and delivery instructions.', preview: '/api/forms/po/print', blank: '/api/forms/po/print?blank=1' },
          { id: 'sap_serial_sticker', name: 'Post-PO SAP Code & Serial Number Tag', type: 'Equipment Barcode Sticker Sheet', desc: 'Adhesive 4" x 2" label sticker with SAP Asset Code barcode and OEM Serial Number barcode.', preview: '/api/forms/sap-serial-print', blank: '/api/forms/sap-serial-print?blank=1' }
        ]
      });
    }

    // Standalone CITPC Note defaults and print
    if (P === '/api/forms/citpc-note' && M === 'GET') {
      const s = S();
      return send(res, 200, {
        ok: 1,
        note: null,
        defaults: {
          title: 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Modules and 7 Years Support for Pune Factory under Replacement with Implementation. - Nos:-22',
          division: 'ITD',
          indenter_name: (u ? u.name : 'Amitava Mukherjee'),
          citpc_required: 'Yes',
          request_type: 'Request Type I',
          type_hardware: 'Hardware',
          subtype_name: 'Standard Switches / Routers.',
          lead_time_ok: 'Yes',
          background: `The existing 24 Port Access Switches deployed across Pune Factory have completed their useful lifecycle of 7 years and have been written off. These switches are used to provide network connectivity across the factory through various VLANs to desktops, printers, IP phones, wireless access points, and other network-connected devices. Due to aging hardware, increasing network utilization, and lack of OEM support, replacement of the existing switches is required to ensure network reliability, improved performance, enhanced security, and uninterrupted business operations.`,
          need: `Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Uplink Modules, DNA Term License, Dual Power Supply, and 7 Years OEM Support for replacement of existing obsolete access switches at Pune Factory.`,
          req_details: `Standard 24 Port UTP PoE Layer 2 Switch with 24 PoE ports, 4 x 10G Enterprise Class SFP uplink ports and 1/10G SFP modules, DNA Term License, Dual Power Supply, Indian Power Cables, all necessary installation accessories, implementation services, and 7 years OEM warranty & support.\nQuantity: 22 Nos\nDelivery Location: Pune Factory ITC Ranjangaon.`,
          vendors_considered: `As per CITPC Approval. Sample Quote enclosed for reference only.`,
          tech_evaluation: `1. Type: Layer 2 Managed Enterprise Switch with 24 UTP PoE ports, 4 x 10G SFP uplink ports and modules, enterprise-class hardware, VLAN, QoS, STP/RSTP, IPv4/IPv6, SNMP, SSH, Web Management, Dual Power Supply, Stacking Capability, DNA Term License, and 7 years OEM warranty & support.`,
          negotiation_history: 'NA',
          brand_options: { capacity_aug: false, standardized: true, cio_approved: false },
          attach_proposals: 'Sample Quote enclosed for reference only.',
          scope_certified: 'Y',
          additional_info: ''
        }
      });
    }

    if (P === '/api/forms/citpc-note/print' || P.match(/^\/api\/procs\/(undefined|null)\/citpc-note\/print$/)) {
      const isBlank = q.get('blank') === '1';
      const s = S();
      const mockProc = {
        code: isBlank ? 'PRC-______-2026' : `${s.prefix}-0001-2026`,
        title: isBlank ? '____________________________________________________________________' : 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Modules and 7 Years Support for Pune Factory',
        dept: isBlank ? '____' : 'ITD',
        plant_location: isBlank ? '_________________________' : 'Pune Factory ITC Ranjangaon',
        created_by: isBlank ? '_____________________' : (u ? u.name : 'Amitava Mukherjee')
      };
      const mockItems = isBlank ? [
        { name: '____________________________________________________', qty: '___', uom: 'Nos' }
      ] : [
        { name: 'Standard 24 Port UTP PoE Layer 2 Switch', qty: 22, uom: 'Nos' }
      ];
      const mockNote = isBlank ? {
        title: '____________________________________________________________________________________________________',
        division: '________',
        indenter_name: '____________________________',
        citpc_required: 'Yes',
        request_type: 'Request Type I',
        type_hardware: 'Hardware',
        subtype_name: '____________________________',
        lead_time_ok: 'Yes',
        background: '\n\n____________________________________________________________________________________________________\n____________________________________________________________________________________________________\n____________________________________________________________________________________________________',
        need: '\n\n____________________________________________________________________________________________________\n____________________________________________________________________________________________________',
        req_details: 'Item Details: _____________________________________________________________________________________\nQuantity: _______ Nos\nDelivery Location: ________________________________________________________________',
        vendors_considered: '____________________________________________________________________________________________________',
        tech_evaluation: '____________________________________________________________________________________________________',
        negotiation_history: '____________________________________________________________________________________________________',
        brand_options: { capacity_aug: false, standardized: false, cio_approved: false },
        attach_proposals: '____________________________________________________________________________________________________',
        scope_certified: 'Y',
        additional_info: ''
      } : {};
      return sendHtml(res, citpcNoteHtml(mockProc, mockItems, mockNote, s));
    }

    // Standalone Completion Certificate defaults and print
    if (P === '/api/forms/completion-cert' && M === 'GET') {
      const s = S();
      return send(res, 200, {
        ok: 1,
        cert: null,
        defaults: {
          company_name: s.company || 'ITC LIMITED',
          factory_name: 'ITD - RANJANGAON CIGARETTE FACTORY',
          plant_address: 'PLOT-B27, MIDC, RANJANGAON, PUNE - 412220',
          io_no: '10064019',
          io_desc: 'PowerEdge R570 Server, Enterprise',
          po_no: '4300055286',
          install_date: today(),
          location: 'MIS ITC PUNFCT',
          model_name: 'PowerEdge R570 Server, Enterprise',
          serial_numbers: 'DNF8LM4, 8PF8LM4, 2MF8LM4, 1PF8LM4',
          remarks: 'Installation and Commissioning successfully completed and verified.',
          asset_count: '4 Nos',
          project_incharge: (u ? u.name : 'Project Incharge'),
          head_of_user_dept: 'Head of User Department',
          commercial_items: [
            { particular: 'DNF8LM4', sap_asset_no: '' },
            { particular: '8PF8LM4', sap_asset_no: '' },
            { particular: '2MF8LM4', sap_asset_no: '' },
            { particular: '1PF8LM4', sap_asset_no: '' }
          ]
        }
      });
    }

    if (P === '/api/forms/completion-cert/print' || P.match(/^\/api\/procs\/(undefined|null)\/completion-cert\/print$/)) {
      const isBlank = q.get('blank') === '1';
      const s = S();
      const mockProc = {
        code: isBlank ? 'PRC-______-2026' : `${s.prefix}-0001-2026`,
        title: isBlank ? '________________________________' : 'PowerEdge R570 Server, Enterprise',
        io_number: isBlank ? '____________' : '10064019',
        po_no: isBlank ? '____________' : '4300055286',
        plant_location: isBlank ? '_________________________' : 'MIS ITC PUNFCT'
      };
      const mockCert = isBlank ? {
        company_name: s.company || 'ITC LIMITED',
        factory_name: 'ITD - RANJANGAON CIGARETTE FACTORY',
        plant_address: 'PLOT-B27, MIDC, RANJANGAON, PUNE - 412220',
        io_no: '____________________',
        io_desc: '__________________________________________________',
        po_no: '____________________',
        install_date: '____ / ____ / ________',
        location: '__________________________________________________',
        model_name: '__________________________________________________',
        serial_numbers: '__________________________________________________',
        remarks: '__________________________________________________',
        asset_count: '_______ Nos',
        project_incharge: '____________________',
        head_of_user_dept: '____________________',
        commercial_items: [
          { particular: '', sap_asset_no: '' },
          { particular: '', sap_asset_no: '' },
          { particular: '', sap_asset_no: '' },
          { particular: '', sap_asset_no: '' }
        ]
      } : {};
      return sendHtml(res, completionCertHtml(mockProc, {}, {}, [], [], mockCert, s));
    }

    // Standalone Logic Note print
    if (P === '/api/forms/logic/print' || P === '/api/forms/logic-note/print' || P.match(/^\/api\/procs\/(undefined|null)\/logic(-note)?\/print$/)) {
      const isBlank = q.get('blank') === '1';
      const s = S();
      const mockProc = {
        code: isBlank ? 'PRC-______-2026' : `${s.prefix}-0001-2026`,
        type: 'revenue',
        title: isBlank ? '__________________________________________________' : 'Substation Transformer Feeder Cables Replacement',
        dept: isBlank ? '____________________' : 'Electrical & Utilities',
        location: isBlank ? '____________________' : 'Plant Substation 3',
        est: isBlank ? 0 : 380000,
        stage: 'logic',
        business_req: isBlank ? '' : 'Feeder cables replacement for uninterrupted plant operations.',
        tech: isBlank ? '' : '4-Core 16 sq mm copper armoured cable compliant with IS 7098.',
        cost_centre: isBlank ? '__________' : 'CC-ELEC-401',
        gl_code: isBlank ? '__________' : 'GL-720100',
        pr_no: isBlank ? '__________' : '10064019',
        pr_date: isBlank ? '____.__.____' : today(),
        hod_date: isBlank ? '____.__.____' : today(),
        final_reason: isBlank ? '' : 'Polycab Wires & Cables Ltd is L1 commercially and technically compliant.',
        awarded_vendor_name: isBlank ? '___________________________________' : 'Polycab Wires & Cables Ltd'
      };
      const mockItems = isBlank ? [
        { id: 1, name: '__________________________________________________', qty: 1, unit: 'nos', final_vendor_id: 1, final_rate: 0, final_gst: 18 }
      ] : [
        { id: 1, name: '4-Core 16 sq mm Armoured Copper Cable', qty: 500, unit: 'mtr', final_vendor_id: 1, final_rate: 620, final_gst: 18, v: 'Polycab Wires & Cables Ltd' }
      ];
      const mockQuotes = isBlank ? [] : [
        {
          id: 1, type: 'final', vendor_id: 1, vendor: 'Polycab Wires & Cables Ltd', address: 'Halol, Gujarat', gst: '24AAACP4321D1Z1', recipient: s.company, qdate: today(), delivery: 'Plant Substation 3', ref: 'POL/2026/901', delivery_days: '5 days', payment_terms: '30 days',
          qitems: [{ item_id: 1, rate: 620, gst: 18 }]
        },
        {
          id: 2, type: 'final', vendor_id: 2, vendor: 'Larsen & Toubro Electrical Systems', address: 'Powai, Mumbai', gst: '27AAACL0123B1Z2', recipient: s.company, qdate: today(), delivery: 'Plant Substation 3', ref: 'LT/QT/8842', delivery_days: '10 days', payment_terms: '30 days',
          qitems: [{ item_id: 1, rate: 680, gst: 18 }]
        },
        {
          id: 3, type: 'final', vendor_id: 3, vendor: 'Schneider Electric India Pvt Ltd', address: 'Bangalore, Karnataka', gst: '29AAACS5678C1Z8', recipient: s.company, qdate: today(), delivery: 'Plant Substation 3', ref: 'SE/2026/041', delivery_days: '14 days', payment_terms: '30 days',
          qitems: [{ item_id: 1, rate: 710, gst: 18 }]
        }
      ];
      const mockFv = mockItems.map(i => ({ ...i, v: i.v || 'Polycab Wires & Cables Ltd' }));
      return sendHtml(res, logicHtml(mockProc, s, mockItems, mockQuotes, mockFv, [], [], u));
    }

    // Standalone CST print
    if (P === '/api/forms/cst/print' || P.match(/^\/api\/procs\/(undefined|null)\/cst\/print$/)) {
      const s = S();
      const mockProc = {
        code: `${s.prefix}-0001-2026`,
        title: 'Comparative Statement Evaluation Matrix (Standard Plant Template)',
        dept: 'Procurement & Engineering',
        location: 'Factory Plant Site',
        type: 'capex',
        est: 2850000,
        requester: u ? u.name : 'Commercial Indenter'
      };
      const mockItems = [
        { id: 1, name: 'Standard 24 Port UTP PoE Layer 2 Switch with 4 x 10G SFP', qty: 22, unit: 'nos', hsn: '8517', citpc_rate: 125000 }
      ];
      const mockQuotes = [
        { id: 1, type: 'initial', vendor_id: 1, vendor: 'Cisco Systems Commercial Partner', ref: 'CIS/2026/410', qdate: today(), delivery_days: '14 days', payment_terms: '30 days', qitems: [{ item_id: 1, rate: 118000, gst: 18 }] },
        { id: 2, type: 'initial', vendor_id: 2, vendor: 'Hewlett Packard Enterprise (Aruba)', ref: 'HPE/QT/991', qdate: today(), delivery_days: '21 days', payment_terms: '30 days', qitems: [{ item_id: 1, rate: 122000, gst: 18 }] },
        { id: 3, type: 'initial', vendor_id: 3, vendor: 'Dell Technologies Networking Division', ref: 'DEL/NET/773', qdate: today(), delivery_days: '30 days', payment_terms: '45 days', qitems: [{ item_id: 1, rate: 129000, gst: 18 }] }
      ];
      return sendHtml(res, cstHtml(mockProc, s, mockItems, mockQuotes, u));
    }

    // Standalone PO print
    if (P === '/api/forms/po/print') {
      const s = S();
      const isBlank = q.get('blank') === '1';
      const mockPo = {
        po_no: isBlank ? 'PO-________' : 'PO-2026-0001',
        po_date: isBlank ? '____.__.____' : today(),
        vendor_name: isBlank ? '________________________________________' : 'Polycab Wires & Cables Ltd',
        total_basic: isBlank ? 0 : 310000,
        total_gst: isBlank ? 0 : 55800,
        total_landed: isBlank ? 0 : 365800,
        payment_terms: isBlank ? '____________________' : '30 days from GRN & Invoice receipt',
        delivery_terms: isBlank ? '____________________' : 'Within 7 days to Plant Site',
        terms_text: s.po_terms || '1. Goods subject to store inward inspection.\n2. GST tax invoice mandatory.\n3. Warranted against manufacturing defects.'
      };
      const mockProc = {
        code: `${s.prefix}-0001-2026`,
        kind: 'po',
        cost_centre: 'CC-ELEC-401'
      };
      const mockVendor = {
        name: mockPo.vendor_name,
        address: isBlank ? '________________________________________' : 'Plot 4, Halol Industrial Area, Vadodara, Gujarat 389350',
        gst: isBlank ? '____________________' : '24AAACP4321D1Z1'
      };
      const mockPoItems = isBlank ? [
        { name: '________________________________________', descr: '________________________________________', qty: '___', unit: 'nos', rate: 0, gst: 18, hsn: '____', total: 0 }
      ] : [
        { name: '4-Core 16 sq mm Armoured Copper Cable', descr: '1100V XLPE insulated, IS 7098 compliant', qty: 500, unit: 'mtr', rate: 620, gst: 18, hsn: '8544', total: 365800 }
      ];
      return sendHtml(res, poHtml(mockPo, mockProc, mockVendor, mockPoItems, s));
    }

    // Standalone SAP & Serial print
    if (P === '/api/forms/sap-serial-print' || P.match(/^\/api\/procs\/(undefined|null)\/sap-serial-print$/)) {
      const s = S();
      const mockAssets = [
        { asset_code: 'AST-2026-001', serial_no: 'SN-84920-A1', asset_name: 'Cisco 24-Port UTP PoE Switch', plant_location: 'MIS Server Rack 2, Ranjangaon', po_no: 'PO-2026-0001' },
        { asset_code: 'AST-2026-002', serial_no: 'SN-84920-A2', asset_name: 'Cisco 24-Port UTP PoE Switch', plant_location: 'MIS Server Rack 2, Ranjangaon', po_no: 'PO-2026-0001' }
      ];
      const mockPo = { po_no: 'PO-2026-0001' };
      const mockProc = { code: `${s.prefix}-0001-2026`, plant_location: 'MIS ITC PUNFCT' };
      return sendHtml(res, sapSerialPrintHtml(mockAssets, mockPo, mockProc, s));
    }

    // Standalone Seed Forms & Demo Indent Endpoint
    if ((P === '/api/forms/load-templates' || P === '/api/demo-data') && M === 'POST') {
      W();
      seedDemoData(true);
      return send(res, 200, { ok: 1, message: 'Official enterprise plant templates and sample indents loaded successfully!' });
    }

    // Comparative Statement (CST) Printout
    if ((m = P.match(/^\/api\/procs\/(\d+)\/cst\/print$/))) {
      const p = getP(m[1]);
      const s = S();
      const items = all('select * from items where proc_id=?', p.id);
      const quotes = loadQuotes(p, s, items);
      return sendHtml(res, cstHtml(p, s, items, quotes, u));
    }

    // Logic Note Printout
    if ((m = P.match(/^\/api\/procs\/(\d+)\/logic(-note)?\/print$/))) {
      const p = getP(m[1]);
      const s = S();
      const items = all('select * from items where proc_id=?', p.id);
      const qs = loadQuotes(p, s, items);
      const fv = items.map(i => ({ ...i, v: one('select name from vendors where id=?', i.final_vendor_id)?.name || '' }));
      const comms = all('select * from comms where proc_id=? order by at', p.id);
      const files = all("select * from docs where proc_id=? and category in ('Quotations','FinalQuotations','Emails')", p.id);
      return sendHtml(res, logicHtml(p, s, items, qs, fv, comms, files, u));
    }

    // Certificate of Completion / Plant Capitalization Handover Form (Commercial Department FAR Format)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/completion-cert$/))) {
      const p = getP(m[1]);
      if (M === 'GET') {
        const pos = all('select * from pos where proc_id=? order by id desc', p.id);
        const grns = all('select * from grns where proc_id=? order by id desc', p.id);
        const items = all('select * from items where proc_id=? order by id asc', p.id);
        const assets = all('select * from assets where proc_id=? order by id asc', p.id);
        let cert = null;
        try { cert = p.completion_cert ? JSON.parse(p.completion_cert) : null; } catch {}

        const s = S();
        const defSerial = assets.map(a => a.serial_no).filter(Boolean).join(', ') || 'DNF8LM4, 8PF8LM4, 2MF8LM4, 1PF8LM4';
        const defCommItems = assets.length
          ? assets.map(a => ({ particular: a.serial_no || a.asset_code || a.asset_name, sap_asset_no: '' }))
          : defSerial.split(',').map(str => ({ particular: str.trim(), sap_asset_no: '' }));

        return send(res, 200, {
          cert,
          defaults: {
            company_name: s.company || 'ITC LIMITED',
            factory_name: 'ITD - RANJANGAON CIGARETTE FACTORY',
            plant_address: 'PLOT-B27, MIDC, RANJANGAON, PUNE - 412220',
            io_no: p.io_number || p.code || '10064019',
            io_desc: p.title || (items[0] && items[0].name) || 'PowerEdge R570 Server, Enterprise',
            po_no: (pos[0] && pos[0].po_no) || p.po_no || '4300055286',
            install_date: p.capitalization_date || p.received_date || (grns[0] && grns[0].grn_date) || today(),
            location: p.plant_location || p.location || 'MIS ITC PUNFCT',
            model_name: (items[0] && (items[0].model || items[0].name)) || p.title || 'PowerEdge R570 Server, Enterprise',
            serial_numbers: defSerial,
            remarks: p.notes || '',
            asset_count: assets.length ? `${assets.length} Nos` : (items.length ? `${items.reduce((sum,i)=>sum+(+i.qty||0),0)} Nos` : '4 Nos'),
            project_incharge: p.requester || p.custodian || 'Project Incharge',
            head_of_user_dept: 'Head of User Department',
            commercial_items: defCommItems
          }
        });
      }
      if (M === 'POST') {
        W();
        checkProcNotLocked(p, u);
        const certJson = JSON.stringify(j);
        run('update proc set completion_cert=?, io_number=?, updated=? where id=?', certJson, j.io_no || p.io_number, now(), p.id);
        p.completion_cert = certJson;
        if (j.io_no) p.io_number = j.io_no;

        const pos = all('select * from pos where proc_id=? order by id desc', p.id);
        const grns = all('select * from grns where proc_id=? order by id desc', p.id);
        const items = all('select * from items where proc_id=? order by id asc', p.id);
        const assets = all('select * from assets where proc_id=? order by id asc', p.id);
        const html = completionCertHtml(p, pos[0], grns[0], items, assets, j, S());

        // Deduplicated clean save in Document Vault
        saveDoc(p, 'CompletionCert', '', `${p.code}_Completion_Certificate.html`, Buffer.from(html), u);
        audit(u, p.id, `Certificate of Completion generated & saved for ${p.code}`);
        return send(res, 200, { ok: 1, html });
      }
    }

    if ((m = P.match(/^\/api\/procs\/(\d+)\/completion-cert\/print$/))) {
      const p = getP(m[1]);
      const pos = all('select * from pos where proc_id=? order by id desc', p.id);
      const grns = all('select * from grns where proc_id=? order by id desc', p.id);
      const items = all('select * from items where proc_id=? order by id asc', p.id);
      const assets = all('select * from assets where proc_id=? order by id asc', p.id);
      let certData = {};
      try { certData = p.completion_cert ? JSON.parse(p.completion_cert) : {}; } catch {}
      return sendHtml(res, completionCertHtml(p, pos[0], grns[0], items, assets, certData, S()));
    }

    // IT CITPC Note (IT Committee Technical Sanction & Capex Form)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/citpc-note$/))) {
      const p = getP(m[1]);
      if (M === 'GET') {
        const items = all('select * from items where proc_id=? order by id asc', p.id);
        const vendors = all('select * from vendors where id in (select distinct vendor_id from quotes where proc_id=?)', p.id);
        let note = null;
        try { note = p.citpc_note ? JSON.parse(p.citpc_note) : null; } catch {}

        const s = S();
        const totalQty = items.reduce((sum, it) => sum + (Number(it.qty) || 0), 0) || 22;
        const defReqDetails = (items && items.length > 0)
          ? (items.map(it => `${it.name} - Qty: ${it.qty} ${it.uom || 'Nos'}`).join('\n') + `\nQuantity: ${totalQty} Nos\nDelivery Location: ${p.plant_location || 'Pune Factory ITC Ranjangaon.'}`)
          : `Standard 24 Port UTP PoE Layer 2 Switch with 24 PoE ports, 4 x 10G Enterprise Class SFP uplink ports and 1/10G SFP modules, DNA Term License, Dual Power Supply, Indian Power Cables, all necessary installation accessories, implementation services, and 7 years OEM warranty & support.\nQuantity: ${totalQty} Nos\nDelivery Location: ${p.plant_location || 'Pune Factory ITC Ranjangaon.'}`;

        const defs = {
          title: p.title || (items[0] ? items[0].name : 'Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Modules and 7 Years Support for Pune Factory under Replacement with Implementation. - Nos:-22'),
          division: p.dept || 'ITD',
          indenter_name: p.created_by || p.owner || (u ? u.name : 'Amitava Mukherjee'),
          citpc_required: 'Yes',
          request_type: 'Request Type I',
          type_hardware: 'Hardware',
          subtype_name: 'Standard Switches / Routers.',
          lead_time_ok: 'Yes',
          background: `The existing 24 Port Access Switches deployed across Pune Factory have completed their useful lifecycle of 7 years and have been written off. These switches are used to provide network connectivity across the factory through various VLANs to desktops, printers, IP phones, wireless access points, and other network-connected devices. Due to aging hardware, increasing network utilization, and lack of OEM support, replacement of the existing switches is required to ensure network reliability, improved performance, enhanced security, and uninterrupted business operations.`,
          need: `Procurement of Standard 24 Port UTP PoE Layer 2 Switches with 4 x 10G Enterprise Class SFP Uplink Modules, DNA Term License, Dual Power Supply, and 7 Years OEM Support for replacement of existing obsolete access switches at Pune Factory.`,
          req_details: defReqDetails,
          vendors_considered: vendors.length ? `As per CITPC Approval. Considered: ${vendors.map(v => v.name).join(', ')}. Sample Quote enclosed for reference only.` : `As per CITPC Approval. Sample Quote enclosed for reference only.`,
          tech_evaluation: `1. Type: Layer 2 Managed Enterprise Switch with 24 UTP PoE ports, 4 x 10G SFP uplink ports and modules, enterprise-class hardware, VLAN, QoS, STP/RSTP, IPv4/IPv6, SNMP, SSH, Web Management, Dual Power Supply, Stacking Capability, DNA Term License, and 7 years OEM warranty & support.`,
          negotiation_history: 'NA',
          brand_options: {
            capacity_aug: false,
            standardized: true,
            cio_approved: false
          },
          attach_proposals: 'Sample Quote enclosed for reference only.',
          scope_certified: 'Y',
          additional_info: ''
        };

        return send(res, 200, { ok: 1, note, defaults: defs, proc: p });
      }

      if (M === 'POST') {
        W();
        const j = await parseBody(req);
        checkProcNotLocked(p, u);
        const noteJson = JSON.stringify(j);
        run('update proc set citpc_note=?, updated=? where id=?', noteJson, now(), p.id);
        p.citpc_note = noteJson;

        const items = all('select * from items where proc_id=? order by id asc', p.id);
        const html = citpcNoteHtml(p, items, j, S());

        // Deduplicated clean save in Document Vault
        saveDoc(p, 'CITPCNote', '', `${p.code}_CITPC_Note.html`, Buffer.from(html), u);
        audit(u, p.id, `IT CITPC Note generated & saved in Document Vault for ${p.code}`);
        return send(res, 200, { ok: 1, html });
      }
    }

    if ((m = P.match(/^\/api\/procs\/(\d+)\/citpc-note\/print$/))) {
      const p = getP(m[1]);
      const items = all('select * from items where proc_id=? order by id asc', p.id);
      let noteData = {};
      try { noteData = p.citpc_note ? JSON.parse(p.citpc_note) : {}; } catch {}
      return sendHtml(res, citpcNoteHtml(p, items, noteData, S()));
    }

    // Dedicated SAP Code & Serial Number ONLY Print (Requisition / Order Level)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/sap-serial-print$/))) {
      const p = getP(m[1]);
      const po = one('select * from pos where proc_id=? order by id desc', p.id) || {};
      let assetsList = all('select * from assets where proc_id=?', p.id);
      if (!assetsList.length) {
        assetsList = [{
          asset_code: p.asset_code || `AST-${p.code}`,
          serial_no: 'SN-' + p.code,
          asset_name: p.title || 'Plant Asset',
          plant_location: p.location,
          category: p.kind
        }];
      }
      return sendHtml(res, sapSerialPrintHtml(assetsList, po, p, S()));
    }

    // Purchase Order (PO) Creation & Management
    if ((m = P.match(/^\/api\/procs\/(\d+)\/pos$/))) {
      const p = getP(m[1]);
      if (M === 'POST') {
        W();
        checkProcNotLocked(p, u);
        const s = S();
        const vendorId = j.vendor_id;
        const vendor = one('select * from vendors where id=?', vendorId);
        if (!vendor) throw E('Vendor not selected');
        const selectedItemIds = j.item_ids || [];
        const isUploaded = j.is_uploaded ? 1 : 0;
        const docId = j.doc_id || null;

        const itemsToOrder = selectedItemIds.length
          ? all(`select * from items where proc_id=? and id in (${selectedItemIds.map(() => '?').join(',')})`, p.id, ...selectedItemIds)
          : all('select * from items where proc_id=?', p.id);

        let basicTotal = 0, gstTotal = 0;
        itemsToOrder.forEach(i => {
          const r = i.final_rate || 0;
          const g = i.final_gst || 0;
          const b = r * i.qty;
          basicTotal += b;
          gstTotal += b * (g / 100);
        });
        const landedTotal = +j.total_landed > 0 ? +j.total_landed : (basicTotal + gstTotal || p.est || 0);

        const poPrefix = p.kind === 'so' ? (s.so_prefix || 'SO') : (s.po_prefix || 'PO');
        const poNo = (j.po_no && String(j.po_no).trim()) ? String(j.po_no).trim() : getNextPoNo(poPrefix);
        const poDate = j.po_date || today();

        const poId = Number(run('insert into pos(proc_id,po_no,po_date,vendor_id,vendor_name,total_basic,total_gst,total_landed,payment_terms,delivery_terms,billing_address,delivery_address,status,terms_text,created_by,created_at,doc_id,is_uploaded,remarks) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
          p.id, poNo, poDate, vendor.id, vendor.name, basicTotal || landedTotal, gstTotal, landedTotal, j.payment_terms || '30 days from GRN', j.delivery_terms || 'Immediate', s.company_address, p.location, 'Issued', j.terms_text || s.po_terms, u.name, now(), docId, isUploaded, j.remarks || '').lastInsertRowid);

        for (const it of itemsToOrder) {
          run('insert into po_items(po_id,item_id,name,descr,qty,unit,rate,gst,hsn,total) values(?,?,?,?,?,?,?,?,?,?)',
            poId, it.id, it.name, it.descr, it.qty, it.unit, it.final_rate || 0, it.final_gst || 0, it.hsn || '', gt(it.final_rate || 0, it.final_gst) * it.qty);
          run('update items set sap_no=?,sap_date=? where id=?', poNo, poDate, it.id);
        }

        run('update proc set po_no=?,po_date=? where id=?', poNo, poDate, p.id);
        audit(u, p.id, `${isUploaded ? 'Official PO Attached' : p.kind.toUpperCase() + ' generated'}: ${poNo} for ${vendor.name} (${money(landedTotal)})`);
        return send(res, 200, { ok: 1, po_id: poId, po_no: poNo, doc_id: docId });
      }
    }

    if (P === '/api/pos' && M === 'GET') {
      return send(res, 200, all(`
        select po.*, p.code as proc_code, p.title as proc_title, p.dept as proc_dept, p.type as proc_type, p.kind as proc_kind
        from pos po
        left join proc p on p.id = po.proc_id
        order by po.id desc
      `));
    }

    if ((m = P.match(/^\/api\/pos\/(\d+)\/print$/))) {
      const po = one('select * from pos where id=?', m[1]);
      if (!po) throw E('PO not found', 404);
      const p = getP(po.proc_id);
      const vendor = one('select * from vendors where id=?', po.vendor_id) || { name: po.vendor_name, address: '—', gst: '—' };
      const poItems = all('select * from po_items where po_id=?', po.id);
      return sendHtml(res, poHtml(po, p, vendor, poItems, S()));
    }

    // Dedicated SAP Code & Serial Number ONLY Print (PO / SO Completed Printout)
    if ((m = P.match(/^\/api\/pos\/(\d+)\/sap-serial-print$/))) {
      const po = one('select * from pos where id=?', m[1]);
      if (!po) throw E('PO not found', 404);
      const p = getP(po.proc_id);
      let assetsList = all('select * from assets where po_id=? or proc_id=?', po.id, po.proc_id);
      if (!assetsList.length) {
        const poItems = all('select * from po_items where po_id=?', po.id);
        if (poItems.length) {
          assetsList = poItems.map((pi, idx) => ({
            asset_code: p.asset_code || `AST-${String(po.po_no).replace(/[^0-9A-Za-z]/g, '')}-${idx + 1}`,
            serial_no: pi.descr || `SN-${String(po.po_no).replace(/[^0-9A-Za-z]/g, '')}-${idx + 1}`,
            asset_name: pi.name || p.title,
            plant_location: p.location,
            category: p.kind
          }));
        } else {
          assetsList = [{
            asset_code: p.asset_code || `AST-${po.po_no}`,
            serial_no: 'SN-' + po.po_no,
            asset_name: p.title || 'Plant Equipment',
            plant_location: p.location,
            category: p.kind
          }];
        }
      }
      return sendHtml(res, sapSerialPrintHtml(assetsList, po, p, S()));
    }

    if ((m = P.match(/^\/api\/pos\/(\d+)$/))) {
      W();
      const po = one('select * from pos where id=?', m[1]);
      if (!po) throw E('PO not found', 404);
      const p = getP(po.proc_id);
      checkProcNotLocked(p, u);
      if (M === 'PUT') {
        const poDate = j.po_date || po.po_date;
        const poNo = j.po_no ? String(j.po_no).trim() : po.po_no;
        const totalLanded = +j.total_landed > 0 ? +j.total_landed : po.total_landed;
        run(`update pos set po_no=?, po_date=?, total_landed=?, delivery_terms=?, payment_terms=?, remarks=? where id=?`,
          poNo, poDate, totalLanded, j.delivery_terms ?? po.delivery_terms, j.payment_terms ?? po.payment_terms, j.remarks ?? po.remarks, po.id);

        // Update items table sap_no & sap_date
        run('update items set sap_no=?, sap_date=? where sap_no=?', poNo, poDate, po.po_no);

        // Update proc table if this PO matches or is latest
        const latestPo = one('select * from pos where proc_id=? order by id desc', p.id);
        if (latestPo && latestPo.id === po.id) {
          run('update proc set po_no=?, po_date=?, updated=? where id=?', poNo, poDate, now(), p.id);
        }

        audit(u, p.id, `${p.kind.toUpperCase()} ${po.po_no} updated: Process Date=${poDate}, No=${poNo}, Landed=${money(totalLanded)}`);
        return send(res, 200, { ok: 1, po_no: poNo, po_date: poDate });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Purchase Orders');
        checkProcNotLocked(p, u);
        run('delete from po_items where po_id=?', po.id);
        run('delete from assets where po_id=?', po.id);
        run('delete from pos where id=?', po.id);
        const rem = one('select * from pos where proc_id=? order by id desc', p.id);
        if (rem) {
          run('update proc set po_no=?,po_date=? where id=?', rem.po_no, rem.po_date, p.id);
        } else {
          run('update proc set po_no=null,po_date=null where id=?', p.id);
        }
        audit(u, p.id, `SECURE DELETE: Purchase Order ${po.po_no} permanently removed by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    // Goods Receipt Note (GRN / Material Inward) Management
    if ((m = P.match(/^\/api\/procs\/(\d+)\/grns$/))) {
      const p = getP(m[1]);
      if (M === 'POST') {
        W();
        checkProcNotLocked(p, u);
        const s = S();
        const grnNo = j.grn_no || getNextGrnNo(s.grn_prefix || 'GRN');
        const grnDate = j.grn_date || today();

        const grnId = Number(run('insert into grns(proc_id,po_id,grn_no,grn_date,challan_no,challan_date,vehicle_no,received_by,inspected_by,inspection_status,store_location,remarks,created_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?)',
          p.id, j.po_id || null, grnNo, grnDate, j.challan_no || '', j.challan_date || '', j.vehicle_no || '', j.received_by || u.name, j.inspected_by || u.name, j.inspection_status || 'Accepted', j.store_location || p.location, j.remarks || '', now()).lastInsertRowid);

        for (const item of j.items || []) {
          const rec = +item.received_qty || 0;
          const acc = +item.accepted_qty || rec;
          const rej = +item.rejected_qty || 0;
          run('insert into grn_items(grn_id,item_id,po_item_id,received_qty,accepted_qty,rejected_qty,rejection_reason) values(?,?,?,?,?,?,?)',
            grnId, item.item_id, item.po_item_id || null, rec, acc, rej, item.rejection_reason || '');
          run('update items set received_qty=coalesce(received_qty,0)+?, accepted_qty=coalesce(accepted_qty,0)+? where id=?', rec, acc, item.item_id);
        }

        run("update proc set grn_status='completed', received_date=?, updated=? where id=?", grnDate, now(), p.id);
        audit(u, p.id, `Material Received at store via GRN ${grnNo} on ${grnDate} (Challan: ${j.challan_no || 'NA'})`);
        return send(res, 200, { ok: 1, grn_id: grnId, grn_no: grnNo });
      }
    }

    if (P === '/api/grns' && M === 'GET') {
      return send(res, 200, all(`
        select grn.*, p.code as proc_code, p.title as proc_title, p.dept as proc_dept, po.po_no, po.vendor_name
        from grns grn
        left join proc p on p.id = grn.proc_id
        left join pos po on po.id = grn.po_id
        order by grn.id desc
      `));
    }

    if ((m = P.match(/^\/api\/grns\/(\d+)$/))) {
      W();
      const grn = one('select * from grns where id=?', m[1]);
      if (!grn) throw E('GRN not found', 404);
      const p = getP(grn.proc_id);
      checkProcNotLocked(p, u);
      if (M === 'PUT') {
        run('update grns set grn_date=?,challan_no=?,challan_date=?,vehicle_no=?,received_by=?,inspected_by=?,inspection_status=?,store_location=?,remarks=? where id=?',
          j.grn_date || grn.grn_date, j.challan_no ?? grn.challan_no, j.challan_date ?? grn.challan_date, j.vehicle_no ?? grn.vehicle_no,
          j.received_by ?? grn.received_by, j.inspected_by ?? grn.inspected_by, j.inspection_status ?? grn.inspection_status,
          j.store_location ?? grn.store_location, j.remarks ?? grn.remarks, grn.id);
        if (j.grn_date) run('update proc set received_date=?, updated=? where id=?', j.grn_date, now(), p.id);
        audit(u, p.id, `Material Receipt / GRN ${grn.grn_no} updated`);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Store Inward (GRN) records');
        checkProcNotLocked(p, u);
        run('delete from grn_items where grn_id=?', grn.id);
        run('delete from grns where id=?', grn.id);
        if (!one('select 1 from grns where proc_id=?', p.id)) {
          run("update proc set grn_status='pending', received_date=null, updated=? where id=?", now(), p.id);
        }
        audit(u, p.id, `SECURE DELETE: Store Inward GRN ${grn.grn_no} permanently removed by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/grns\/(\d+)\/print$/))) {
      const grn = one('select * from grns where id=?', m[1]);
      if (!grn) throw E('GRN not found', 404);
      const p = getP(grn.proc_id);
      const po = grn.po_id ? one('select * from pos where id=?', grn.po_id) : null;
      const grnItems = all('select gi.*, i.name, i.qty as ordered_qty from grn_items gi left join items i on i.id=gi.item_id where gi.grn_id=?', grn.id);
      return sendHtml(res, grnHtml(grn, po, p, grnItems, S()));
    }

    // Factory Asset Inward, Capitalization & Tagging
    if ((m = P.match(/^\/api\/procs\/(\d+)\/assets$/))) {
      const p = getP(m[1]);
      if (M === 'GET') {
        return send(res, 200, all('select * from assets where proc_id=? order by id desc', p.id));
      }
      if (M === 'POST') {
        W();
        checkProcNotLocked(p, u);
        const s = S();
        const capDate = j.capitalization_date || j.put_to_use_date || today();
        const commDate = j.commissioning_date || capDate;
        const name = j.asset_name || p.title;
        const category = j.category || (p.type === 'capex' ? 'Plant & Machinery (Capex)' : 'IT & Networking Hardware');
        const custodian = j.custodian || u.name;
        const status = j.status || 'Capitalized & In-Service';
        const warranty = j.warranty_expiry || '';
        const remarks = j.remarks || '';
        const poId = j.po_id || null;
        const itemId = j.item_id || null;

        // Multi-unit batch asset tagging (each physical unit has its own unique serial number & asset tag code)
        const units = Array.isArray(j.units) && j.units.length > 0 ? j.units : null;

        if (units) {
          // Pre-validate all units for intra-batch and database uniqueness before saving any
          const seenCodes = new Set();
          const seenSerials = new Set();

          for (let idx = 0; idx < units.length; idx++) {
            const uItem = units[idx];
            const assetCode = (uItem.asset_code && String(uItem.asset_code).trim()) ? String(uItem.asset_code).trim() : null;
            const serialNo = (uItem.serial_no != null ? String(uItem.serial_no).trim() : '');

            // Intra-batch checks
            if (assetCode) {
              const codeLower = assetCode.toLowerCase();
              if (seenCodes.has(codeLower)) {
                throw E(`Duplicate SAP Code in batch: "${assetCode}" is entered multiple times (Unit #${idx + 1}). Each unit must have a unique SAP Code.`, 400);
              }
              seenCodes.add(codeLower);
            }

            const isGeneric = ['na', 'n/a', 'none', '—', '-', 'null', ''].includes(serialNo.toLowerCase());
            if (serialNo && !isGeneric) {
              const snLower = serialNo.toLowerCase();
              if (seenSerials.has(snLower)) {
                throw E(`Duplicate Serial Number in batch: "${serialNo}" is entered multiple times (Unit #${idx + 1}). Each physical unit must have a unique Serial Number.`, 400);
              }
              seenSerials.add(snLower);
            }

            // Database uniqueness check
            validateAssetUniqueness(assetCode, serialNo);
          }

          const createdAssets = [];
          const totalCost = +j.cost > 0 ? +j.cost : (p.est || 0);
          const defaultUnitCost = Math.round((totalCost / units.length) * 100) / 100;

          for (let idx = 0; idx < units.length; idx++) {
            const uItem = units[idx];
            const assetCode = (uItem.asset_code && String(uItem.asset_code).trim()) ? String(uItem.asset_code).trim() : getNextAssetCode(s.asset_prefix || 'AST');
            const unitName = uItem.asset_name || name;
            const unitCost = +uItem.cost > 0 ? +uItem.cost : defaultUnitCost;
            const unitLoc = uItem.plant_location || j.plant_location || p.location;
            const serialNo = (uItem.serial_no != null ? String(uItem.serial_no).trim() : '');

            const assetId = Number(run(`insert into assets(
              proc_id, po_id, item_id, asset_code, asset_name, category,
              capitalization_date, commissioning_date, put_to_use_date, plant_location,
              custodian, serial_no, cost, warranty_expiry, status, remarks, created_at
            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
              p.id, poId, itemId, assetCode, unitName, category,
              capDate, commDate, j.put_to_use_date || capDate,
              unitLoc, custodian, serialNo,
              unitCost, warranty, status,
              remarks, now()
            ).lastInsertRowid);

            createdAssets.push({ id: assetId, asset_code: assetCode, serial_no: serialNo, cost: unitCost });
          }

          const allCodes = createdAssets.map(a => a.asset_code).join(', ');
          const firstCode = createdAssets[0]?.asset_code;
          const serialsList = createdAssets.filter(x => x.serial_no).map(x => x.serial_no).join(', ');

          run(`update proc set asset_status='capitalized', asset_code=?, capitalization_date=?, commissioning_date=?, plant_location=?, custodian=?, updated=? where id=?`,
            allCodes, capDate, commDate, j.plant_location || p.location, custodian, now(), p.id);

          audit(u, p.id, `${createdAssets.length} Factory Assets tagged & capitalized: ${allCodes} (${serialsList ? 'Serials: ' + serialsList : 'No Serials'})`);
          return send(res, 200, { ok: 1, count: createdAssets.length, assets: createdAssets, asset_code: allCodes });
        }

        // Single asset fallback
        const assetCode = (j.asset_code && String(j.asset_code).trim()) ? String(j.asset_code).trim() : getNextAssetCode(s.asset_prefix || 'AST');
        const serialNo = (j.serial_no != null ? String(j.serial_no).trim() : '');
        validateAssetUniqueness(assetCode, serialNo);
        const cost = +j.cost > 0 ? +j.cost : (p.est || 0);

        const assetId = Number(run(`insert into assets(
          proc_id, po_id, item_id, asset_code, asset_name, category,
          capitalization_date, commissioning_date, put_to_use_date, plant_location,
          custodian, serial_no, cost, warranty_expiry, status, remarks, created_at
        ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
          p.id, poId, itemId, assetCode, name,
          category,
          capDate, commDate, j.put_to_use_date || capDate,
          j.plant_location || p.location, custodian, serialNo,
          cost, warranty, status,
          remarks, now()
        ).lastInsertRowid);

        run(`update proc set asset_status='capitalized', asset_code=?, capitalization_date=?, commissioning_date=?, plant_location=?, custodian=?, updated=? where id=?`,
          assetCode, capDate, commDate, j.plant_location || p.location, custodian, now(), p.id);

        audit(u, p.id, `Factory Asset tagged & capitalized: ${assetCode} – ${name} (SN: ${j.serial_no || 'NA'})`);
        return send(res, 200, { ok: 1, id: assetId, asset_code: assetCode });
      }
    }

    if ((m = P.match(/^\/api\/assets\/(\d+)$/))) {
      W();
      const ast = one('select * from assets where id=?', m[1]);
      if (!ast) throw E('Asset not found', 404);
      const p = ast.proc_id ? one('select * from proc where id=?', ast.proc_id) : null;
      if (p) checkProcNotLocked(p, u);
      if (M === 'PUT') {
        const targetCode = (j.asset_code !== undefined ? String(j.asset_code).trim() : ast.asset_code);
        const targetSerial = (j.serial_no !== undefined ? String(j.serial_no).trim() : ast.serial_no);
        validateAssetUniqueness(targetCode, targetSerial, ast.id);

        run(`update assets set
          asset_code=?, asset_name=?, category=?, capitalization_date=?,
          commissioning_date=?, put_to_use_date=?, plant_location=?,
          custodian=?, serial_no=?, cost=?, warranty_expiry=?, status=?, remarks=?
          where id=?`,
          targetCode || ast.asset_code, j.asset_name || ast.asset_name,
          j.category ?? ast.category, j.capitalization_date || ast.capitalization_date,
          j.commissioning_date || ast.commissioning_date, j.put_to_use_date || ast.put_to_use_date,
          j.plant_location ?? ast.plant_location, j.custodian ?? ast.custodian,
          targetSerial, +j.cost || ast.cost,
          j.warranty_expiry ?? ast.warranty_expiry, j.status || ast.status,
          j.remarks ?? ast.remarks, ast.id
        );
        if (p) {
          run('update proc set asset_code=?, capitalization_date=?, plant_location=?, custodian=?, updated=? where id=?',
            targetCode || ast.asset_code, j.capitalization_date || ast.capitalization_date,
            j.plant_location ?? ast.plant_location, j.custodian ?? ast.custodian, now(), p.id);
        }
        audit(u, p ? p.id : null, `Factory Asset ${ast.asset_code} updated`);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Factory Fixed Assets');
        if (p) checkProcNotLocked(p, u);
        run('delete from assets where id=?', ast.id);
        if (p && !one('select 1 from assets where proc_id=?', p.id)) {
          run("update proc set asset_status='pending', asset_code=null, capitalization_date=null, updated=? where id=?", now(), p.id);
        }
        audit(u, p ? p.id : null, `SECURE DELETE: Factory Asset ${ast.asset_code} ("${ast.asset_name}") permanently removed by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/assets\/(\d+)\/print$/))) {
      const ast = one('select * from assets where id=?', m[1]);
      if (!ast) throw E('Asset not found', 404);
      const p = ast.proc_id ? (one('select * from proc where id=?', ast.proc_id) || {}) : {};
      const po = ast.po_id ? one('select * from pos where id=?', ast.po_id) : (p.id ? one('select * from pos where proc_id=?', p.id) : null);
      return sendHtml(res, assetTagHtml(ast, po, p, S()));
    }

    // Dedicated SAP Code & Serial Number ONLY Print (Asset Level)
    if ((m = P.match(/^\/api\/assets\/(\d+)\/sap-serial-print$/))) {
      const ast = one('select * from assets where id=?', m[1]);
      if (!ast) throw E('Asset not found', 404);
      const p = ast.proc_id ? (one('select * from proc where id=?', ast.proc_id) || {}) : {};
      const po = ast.po_id ? one('select * from pos where id=?', ast.po_id) : (p.id ? one('select * from pos where proc_id=?', p.id) : null);
      return sendHtml(res, sapSerialPrintHtml([ast], po, p, S()));
    }

    // Global Factory Asset Register (GET all, DELETE clear/bulk)
    if (P === '/api/assets') {
      if (M === 'GET') {
        return send(res, 200, all(`
          select a.*, p.code as proc_code, p.title as proc_title, p.dept, p.kind, p.type as proc_type,
                 po.po_no, po.vendor_name
          from assets a
          left join proc p on p.id = a.proc_id
          left join pos po on po.id = a.po_id
          order by a.id desc
        `));
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Factory Fixed Assets');
        if (j && Array.isArray(j.ids) && j.ids.length > 0) {
          for (const aid of j.ids) {
            run('delete from assets where id=?', aid);
          }
          run("update proc set asset_status='pending', asset_code=null, capitalization_date=null, updated=? where id not in (select distinct proc_id from assets where proc_id is not null)", now());
          audit(u, null, `SECURE DELETE: Bulk deleted ${j.ids.length} factory assets by ${u.username}`);
          return send(res, 200, { ok: 1, deleted: j.ids.length });
        }
        if (j && (j.all === true || j.confirm === 'DELETE')) {
          const count = one('select count(*) as cnt from assets')?.cnt || 0;
          run('delete from assets');
          run("update proc set asset_status='pending', asset_code=null, capitalization_date=null, updated=?", now());
          audit(u, null, `SECURE DELETE: Purged all ${count} factory assets from register by ${u.username}`);
          return send(res, 200, { ok: 1, deleted: count });
        }
        throw E('Specify asset IDs or confirm clear all', 400);
      }
    }

    // Explicit Close Requisition Endpoint
    if ((m = P.match(/^\/api\/procs\/(\d+)\/close$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      const remarks = j.remarks || 'Requisition formally closed after Material Receipt & Factory Asset Capitalization';

      // Auto-register asset with SAP Code & Serial Number if provided and not yet registered
      if (j.asset_code || j.serial_no) {
        const code = (j.asset_code || '').trim() || (p.asset_code || `AST-${p.code}`);
        const sn = (j.serial_no || '').trim() || 'NA';
        const existingAsset = one('select id from assets where proc_id=?', p.id);
        if (!existingAsset) {
          validateAssetUniqueness(code, sn);
          const po = one('select * from pos where proc_id=? order by id desc', p.id);
          const item = one('select * from items where proc_id=? order by id asc', p.id);
          run(`insert into assets(proc_id, po_id, item_id, asset_code, asset_name, category, capitalization_date, commissioning_date, put_to_use_date, plant_location, custodian, serial_no, cost, status, created_at)
               values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
            p.id, po ? po.id : null, item ? item.id : null, code, item ? item.name : p.title, p.kind || 'Plant Asset',
            today(), today(), today(), p.location || 'Factory', p.requester || 'Plant Engineer', sn, p.est || 0,
            'Capitalized & In-Service', now());
          run("update proc set asset_code=?, asset_status='capitalized', capitalization_date=? where id=?", code, today(), p.id);
        }
      }

      run("update proc set is_locked=1,unlock_status='locked',closed_at=?,closed_by=?,close_remarks=?,updated=? where id=?", now(), u.name || u.username, remarks, now(), p.id);
      p.is_locked = 1;
      p.unlock_status = 'locked';
      setStage(p, 'completed', remarks, u);
      return send(res, 200, { ok: 1 });
    }

    // Unlock Request Endpoint (Requester submits justification to unlock finalized order)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/unlock-request$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      if (!isProcLocked(p) && p.unlock_status !== 'locked') {
        throw E('This requisition is not currently locked.');
      }
      const reason = (j.reason || '').trim();
      if (!reason) {
        throw E('A valid business justification / reason is mandatory to request unlock approval.');
      }
      run(`insert into unlock_requests(proc_id,req_code,requested_by,requested_at,reason,status) values(?,?,?,?,?,?)`,
        p.id, p.code, u.name || u.username, now(), reason, 'pending');
      run(`update proc set unlock_status='unlock_requested', unlock_reason=?, unlock_requested_by=?, unlock_requested_at=?, updated=? where id=?`,
        reason, u.name || u.username, now(), now(), p.id);
      audit(u, p.id, `Unlock Permission Requested by ${u.name || u.username}. Justification: "${reason}"`);
      return send(res, 200, { ok: 1, message: 'Unlock request submitted successfully and sent for approval.' });
    }

    // Unlock Review Action Endpoint (Admin / Commercial Head approves or rejects unlock request)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/unlock-action$/)) && M === 'POST') {
      W();
      const isApprover = adm || u.role === 'commercial' || u.role === 'approver' || u.role === 'finance';
      if (!isApprover) {
        throw E('Permission denied. Only Administrator, Commercial Head, or designated Approvers can approve/reject unlock requests.', 403);
      }
      const p = getP(m[1]);
      const action = j.action; // 'approve' | 'reject'
      const remarks = (j.remarks || '').trim();

      if (action === 'approve') {
        const pending = one("select id from unlock_requests where proc_id=? and status='pending' order by id desc", p.id);
        if (pending) {
          run(`update unlock_requests set status='approved', reviewed_by=?, reviewed_at=?, review_remarks=? where id=?`,
            u.name || u.username, now(), remarks || 'Approved for editing', pending.id);
        } else {
          run(`insert into unlock_requests(proc_id,req_code,requested_by,requested_at,reason,status,reviewed_by,reviewed_at,review_remarks) values(?,?,?,?,?,'approved',?,?,?)`,
            p.id, p.code, u.name || u.username, now(), remarks || 'Admin Direct Unlock', u.name || u.username, now(), remarks || 'Authorized by Admin');
        }
        run(`update proc set is_locked=0, unlock_status='unlocked', unlock_reason=?, unlock_approved_by=?, unlock_approved_at=?, updated=? where id=?`,
          remarks || p.unlock_reason || 'Authorized by Admin', u.name || u.username, now(), now(), p.id);
        audit(u, p.id, `Requisition Unlocked by ${u.name || u.username}. Justification: ${remarks || 'Authorized by Admin'}`);
        return send(res, 200, { ok: 1, status: 'unlocked' });
      } else if (action === 'reject') {
        run(`update unlock_requests set status='rejected', reviewed_by=?, reviewed_at=?, review_remarks=? where proc_id=? and status='pending'`,
          u.name || u.username, now(), remarks || 'Request rejected', p.id);
        run(`update proc set is_locked=1, unlock_status='locked', unlock_reason=null, updated=? where id=?`,
          now(), p.id);
        audit(u, p.id, `Unlock Request REJECTED by ${u.name || u.username}. Reason: ${remarks || 'Rejected'}`);
        return send(res, 200, { ok: 1, status: 'locked' });
      } else {
        throw E('Invalid action specified');
      }
    }

    // Re-Lock & Freeze Endpoint (Restores audit lock once corrections are done)
    if ((m = P.match(/^\/api\/procs\/(\d+)\/relock$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      const remarks = (j.remarks || 'Modifications completed, audit freeze active').trim();
      run(`update proc set is_locked=1, unlock_status='locked', updated=? where id=?`, now(), p.id);
      audit(u, p.id, `Requisition Re-Locked & Frozen by ${u.name || u.username}: ${remarks}`);
      return send(res, 200, { ok: 1, status: 'locked' });
    }

    // Invoices & 3-Way Matching
    if ((m = P.match(/^\/api\/procs\/(\d+)\/invoices$/))) {
      const p = getP(m[1]);
      if (M === 'POST') {
        W();
        checkProcNotLocked(p, u);
        const po = j.po_id ? one('select * from pos where id=?', j.po_id) : null;
        const totalAmount = +j.total_amount || 0;
        const baseAmount = +j.amount || (totalAmount / 1.18);
        const gstAmount = +j.gst_amount || (totalAmount - baseAmount);

        // 3-Way Match Check
        let matchStatus = 'MATCHED';
        const grns = all('select * from grns where proc_id=?', p.id);
        if (!grns.length) {
          matchStatus = 'PENDING_GRN';
        } else if (po && Math.abs(po.total_landed - totalAmount) > 5) {
          matchStatus = 'PRICE_MISMATCH';
        }

        const invId = Number(run('insert into invoices(proc_id,po_id,invoice_no,invoice_date,amount,gst_amount,total_amount,match_status,payment_status,remarks,created_at,doc_id) values(?,?,?,?,?,?,?,?,?,?,?,?)',
          p.id, j.po_id || null, j.invoice_no, j.invoice_date || today(), baseAmount, gstAmount, totalAmount, matchStatus, 'Unpaid', j.remarks || '', now(), j.doc_id || null).lastInsertRowid);

        run("update proc set invoice_status='received', updated=? where id=?", now(), p.id);
        audit(u, p.id, `Vendor Tax Invoice recorded: ${j.invoice_no} (${money(totalAmount)}) – 3-Way Match: ${matchStatus}`);
        return send(res, 200, { ok: 1, invoice_id: invId, match_status: matchStatus });
      }
    }

    if ((m = P.match(/^\/api\/invoices\/(\d+)$/))) {
      W();
      const inv = one('select * from invoices where id=?', m[1]);
      if (!inv) throw E('Invoice not found', 404);
      const p = getP(inv.proc_id);
      checkProcNotLocked(p, u);
      if (M === 'PUT') {
        const baseAmount = j.amount !== undefined ? Number(j.amount || 0) : inv.amount;
        const gstAmount = j.gst_amount !== undefined ? Number(j.gst_amount || 0) : inv.gst_amount;
        const totalAmount = j.total_amount !== undefined ? Number(j.total_amount || 0) : (baseAmount + gstAmount);
        
        run(`update invoices set 
          invoice_no=?, invoice_date=?, amount=?, gst_amount=?, total_amount=?, 
          match_status=?, payment_status=?, payment_date=?, utr_no=?, remarks=? 
          where id=?`,
          j.invoice_no || inv.invoice_no,
          j.invoice_date || inv.invoice_date,
          baseAmount,
          gstAmount,
          totalAmount,
          j.match_status || inv.match_status || 'MATCHED',
          j.payment_status || inv.payment_status || 'Unpaid',
          j.payment_date !== undefined ? j.payment_date : inv.payment_date,
          j.utr_no !== undefined ? j.utr_no : inv.utr_no,
          j.remarks !== undefined ? j.remarks : inv.remarks,
          inv.id
        );
        audit(u, p.id, `Updated Invoice: ${j.invoice_no || inv.invoice_no} (${money(totalAmount)})`);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Vendor Invoices');
        run('delete from invoices where id=?', inv.id);
        const rem = one('select * from invoices where proc_id=? order by id desc', p.id);
        if (!rem) {
          run("update proc set invoice_status='pending', updated=? where id=?", now(), p.id);
        }
        audit(u, p.id, `SECURE DELETE: Invoice ${inv.invoice_no} removed by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/invoices\/(\d+)\/payment$/)) && M === 'POST') {
      W();
      run('update invoices set payment_status=?,payment_date=?,utr_no=? where id=?',
        j.payment_status || 'Paid', j.payment_date || today(), j.utr_no || '', m[1]);
      const inv = one('select * from invoices where id=?', m[1]);
      audit(u, inv ? inv.proc_id : null, `Invoice ${inv?.invoice_no} payment marked as ${j.payment_status} (UTR: ${j.utr_no || 'NA'})`);
      return send(res, 200, { ok: 1 });
    }

    if ((m = P.match(/^\/api\/invoices\/(\d+)\/print$/))) {
      const inv = one('select * from invoices where id=?', m[1]);
      if (!inv) throw E('Invoice not found', 404);
      const p = getP(inv.proc_id);
      const po = inv.po_id ? one('select * from pos where id=?', inv.po_id) : (p.po_no ? one('select * from pos where proc_id=?', p.id) : null);
      const vendor = (po && po.vendor_id) ? one('select * from vendors where id=?', po.vendor_id) : { name: po ? po.vendor_name : 'Vendor', gst: '—', address: '—' };
      return sendHtml(res, invoiceVoucherHtml(inv, po, p, vendor || {}, S()));
    }

    // Items CRUD
    if ((m = P.match(/^\/api\/procs\/(\d+)\/items$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      checkProcNotLocked(p, u);
      if (!adm && !['quotations', 'negotiation', 'final', 'pr'].includes(p.stage)) {
        throw E('Items are locked after the logic note stage');
      }
      let n = 0;
      for (const i of j.items || []) {
        if (!i.name || !(+i.qty > 0)) continue;
        run('insert into items(proc_id,name,descr,model,qty,unit,hsn,citpc_rate,last_date) values(?,?,?,?,?,?,?,?,?)',
          p.id, i.name, i.descr || '', i.model || '', +i.qty, i.unit || 'nos', i.hsn || '', +i.citpc_rate || null, i.last_date || null);
        n++;
      }
      audit(u, p.id, n + ' item(s) added');
      return send(res, 200, { n });
    }

    if ((m = P.match(/^\/api\/items\/(\d+)$/))) {
      W();
      const i = one('select * from items where id=?', m[1]);
      if (!i) throw E('Item not found', 404);
      const p = getP(i.proc_id);
      checkProcNotLocked(p, u);
      if (M === 'PUT') {
        const f = ['name', 'descr', 'model', 'qty', 'unit', 'hsn', 'citpc_rate', 'last_date'];
        run(`update items set ${f.map(k => k + '=?').join(',')} where id=?`, ...f.map(k => j[k] === '' ? null : (j[k] ?? i[k])), i.id);
        audit(u, p.id, 'Item edited: ' + i.name);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Requisition Line Items');
        if (!adm && !['quotations', 'negotiation', 'final'].includes(p.stage)) throw E('Locked at this stage');
        run('delete from qitems where item_id=?', i.id);
        run('delete from items where id=?', i.id);
        audit(u, p.id, `SECURE DELETE: Item removed: ${i.name} by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/items\/(\d+)\/final$/)) && M === 'POST') {
      W();
      const i = one('select * from items where id=?', m[1]);
      const p = getP(i.proc_id);
      checkProcNotLocked(p, u);
      if (!adm && !['pr', 'logic'].includes(p.stage)) throw E('Final vendor can be changed at PR / logic note stage');
      const x = one('select qi.rate,qi.gst from qitems qi join quotes q on q.id=qi.quote_id where qi.item_id=? and q.vendor_id=? and q.type=? order by q.qdate desc',
        i.id, j.vendor_id, p.type === 'capex' ? 'initial' : 'final');
      if (!x) throw E('Selected vendor has not quoted for this item');
      run('update items set final_vendor_id=?,final_rate=?,final_gst=? where id=?', j.vendor_id, x.rate, x.gst, i.id);
      audit(u, p.id, 'Final vendor changed for item: ' + i.name);
      return send(res, 200, { ok: 1 });
    }

    // Quotations CRUD
    if ((m = P.match(/^\/api\/procs\/(\d+)\/quotes$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      checkProcNotLocked(p, u);
      const t = j.type === 'final' ? 'final' : 'initial';
      if (!adm && !(p.stage === 'quotations' && t === 'initial') && !(p.stage === 'final' && t === 'final')) {
        throw E('Cannot add this quotation type at this stage');
      }
      const id = saveQuote(p, null, { ...j, type: t });
      audit(u, p.id, `${t} quotation added for vendor`);
      return send(res, 200, { id });
    }

    if ((m = P.match(/^\/api\/quotes\/(\d+)$/))) {
      W();
      const q = one('select * from quotes where id=?', m[1]);
      if (!q) throw E('Quotation not found', 404);
      const p = getP(q.proc_id);
      checkProcNotLocked(p, u);
      if (!adm && ['completed', 'cancelled'].includes(p.stage)) throw E('Requisition is completed or cancelled; quotations cannot be modified');
      if (M === 'PUT') {
        saveQuote(p, q.id, { ...j, type: q.type });
        audit(u, p.id, 'Quotation edited: ' + q.vendor);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Vendor Quotations');
        checkProcNotLocked(p, u);
        run('delete from qitems where quote_id=?', q.id);
        run('delete from quotes where id=?', q.id);
        audit(u, p.id, `SECURE DELETE: Quotation removed: ${q.vendor} by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    // Communications / Negotiation Notes
    if ((m = P.match(/^\/api\/procs\/(\d+)\/comms$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      checkProcNotLocked(p, u);
      if (!j.text) throw E('Enter message text');
      run('insert into comms(proc_id,at,by,kind,vendor,text) values(?,?,?,?,?,?)',
        p.id, j.at || now(), u.username, j.kind, j.vendor || '', j.text);
      audit(u, p.id, `Communication logged (${j.kind}) with ${j.vendor || 'Vendor'}`);
      return send(res, 200, { ok: 1 });
    }

    if ((m = P.match(/^\/api\/comms\/(\d+)$/))) {
      W();
      const comm = one('select * from comms where id=?', m[1]);
      if (!comm) throw E('Communication log not found', 404);
      const p = getP(comm.proc_id);
      checkProcNotLocked(p, u);
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Communication Logs');
        run('delete from comms where id=?', comm.id);
        audit(u, p.id, `SECURE DELETE: Deleted communication note (${comm.kind}) by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    // Documents upload / download
    if ((m = P.match(/^\/api\/procs\/(\d+)\/upload$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      checkProcNotLocked(p, u);
      const c = url.searchParams.get('category');
      const cat = CATS.includes(c) ? c : 'Other';
      const id = saveDoc(p, cat, url.searchParams.get('vendor'), decodeURIComponent(req.headers['x-filename'] || 'file'), raw, u);
      const qid = url.searchParams.get('quote_id');
      if (qid) run('update quotes set doc_id=? where id=?', id, qid);
      const mqid = url.searchParams.get('mail_quote_id');
      if (mqid) run('update quotes set mail_doc_id=? where id=?', id, mqid);
      return send(res, 200, { id });
    }

    // Awarded Vendor Selection for Logic Note
    if ((m = P.match(/^\/api\/procs\/(\d+)\/select-vendor$/)) && M === 'POST') {
      W();
      const p = getP(m[1]);
      checkProcNotLocked(p, u);
      const vendorId = j.vendor_id;
      const v = one('select * from vendors where id=?', vendorId);
      if (!v) throw E('Vendor not found', 404);

      const qtype = p.type === 'capex' ? 'initial' : 'final';
      const q = one('select * from quotes where proc_id=? and vendor_id=? and type=? order by id desc', p.id, vendorId, qtype)
             || one('select * from quotes where proc_id=? and vendor_id=? order by id desc', p.id, vendorId);

      if (!q) throw E('Selected vendor has not submitted a quotation for this requisition');

      const qitems = all('select * from qitems where quote_id=?', q.id);
      for (const qi of qitems) {
        run('update items set final_vendor_id=?, final_rate=?, final_gst=? where id=? and proc_id=?',
          v.id, qi.rate, qi.gst, qi.item_id, p.id);
      }

      const reason = j.justification || j.final_reason || p.final_reason || '';
      run('update proc set citpc_vendor=?, awarded_vendor_id=?, awarded_vendor_name=?, selection_basis=?, final_reason=?, updated=? where id=?',
        v.name, v.id, v.name, j.selection_basis || 'L1 - Lowest Commercial Bidder', reason, now(), p.id);
      audit(u, p.id, `Logic Note Awarded Vendor selected: ${v.name} (Basis: ${j.selection_basis || 'L1'})`);
      return send(res, 200, { ok: 1, vendor_name: v.name });
    }

    // All Documents Vault
    if (P === '/api/documents' && M === 'GET') {
      const qCat = url.searchParams.get('category');
      const qProc = url.searchParams.get('proc_id');
      let query = `
        SELECT d.*, p.code as proc_code, p.title as proc_title, p.dept as proc_dept, p.type as proc_type
        FROM docs d
        LEFT JOIN proc p ON p.id = d.proc_id
        WHERE 1=1
      `;
      const params = [];
      if (qCat && qCat !== 'all') {
        query += ' AND d.category = ?';
        params.push(qCat);
      }
      if (qProc && qProc !== 'all') {
        query += ' AND d.proc_id = ?';
        params.push(qProc);
      }
      query += ' ORDER BY d.id DESC';
      const rows = all(query, ...params);
      const docsWithMeta = rows.map(r => {
        let size = 0;
        let exists = false;
        try {
          const fp = path.join(DD, r.path);
          if (fs.existsSync(fp)) {
            size = fs.statSync(fp).size;
            exists = true;
          }
        } catch {}
        return {
          ...r,
          size,
          exists,
          ext: (path.extname(r.orig || r.name) || '').toLowerCase()
        };
      });
      return send(res, 200, docsWithMeta);
    }

    if ((m = P.match(/^\/api\/docs\/(\d+)(?:\/(view|download))?$/))) {
      const docId = m[1];
      const action = m[2] || 'view';
      const d = one('select * from docs where id=?', docId);
      if (!d) throw E('Document not found', 404);
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Document Vault Files');
        if (d.proc_id) {
          const p = getP(d.proc_id);
          checkProcNotLocked(p, u);
        }
        try { fs.unlinkSync(path.join(DD, d.path)); } catch {}
        run('delete from docs where id=?', d.id);
        audit(u, d.proc_id, `SECURE DELETE: Document "${d.name}" permanently deleted by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
      const fp = path.join(DD, d.path);
      if (!fs.existsSync(fp)) {
        throw E('Document file is missing from local storage', 404);
      }
      const ext = path.extname(fp).toLowerCase();
      const contentType = mime[ext] || 'application/octet-stream';
      const dispType = action === 'download' ? 'attachment' : 'inline';
      const dlName = d.orig || d.name;
      res.writeHead(200, {
        'Content-Type': contentType,
        'Content-Disposition': `${dispType}; filename="${encodeURIComponent(dlName)}"`
      });
      return res.end(fs.readFileSync(fp));
    }

    // Item Master Catalog CRUD
    if (P === '/api/catalog' && M === 'GET') {
      return send(res, 200, all('select * from item_master order by name'));
    }
    if (P === '/api/catalog' && M === 'POST') {
      W();
      if (!j.name) throw E('Item name required');
      const r = run('insert into item_master(code,name,descr,category,unit,hsn,citpc_rate,created) values(?,?,?,?,?,?,?,?)',
        j.code || ('ITM-' + Date.now().toString().slice(-6)), j.name, j.descr || '', j.category || 'General', j.unit || 'nos', j.hsn || '', +j.citpc_rate || 0, today());
      audit(u, null, 'Catalog item added: ' + j.name);
      return send(res, 200, { id: Number(r.lastInsertRowid) });
    }
    if ((m = P.match(/^\/api\/catalog\/(\d+)\/usage$/)) && M === 'GET') {
      const item = one('select * from item_master where id=?', m[1]);
      if (!item) throw E('Catalog item not found', 404);
      const prItems = all(`
        select i.id, i.proc_id, i.name, i.qty, i.unit, p.code as proc_code, p.title as proc_title, p.stage
        from items i
        left join proc p on p.id = i.proc_id
        where lower(trim(i.name)) = lower(trim(?)) or lower(trim(i.model)) = lower(trim(?))
      `, item.name, item.code);
      const poItems = all(`
        select pi.id, pi.po_id, pi.name, pi.qty, pi.unit, po.po_no, po.po_date, po.vendor_name
        from po_items pi
        left join pos po on po.id = pi.po_id
        where lower(trim(pi.name)) = lower(trim(?))
      `, item.name);
      return send(res, 200, {
        item,
        prCount: prItems.length,
        poCount: poItems.length,
        prItems,
        poItems,
        inUse: (prItems.length + poItems.length) > 0
      });
    }
    if ((m = P.match(/^\/api\/catalog\/(\d+)$/))) {
      if (M === 'PUT') {
        W();
        run('update item_master set code=?,name=?,descr=?,category=?,unit=?,hsn=?,citpc_rate=? where id=?',
          j.code, j.name, j.descr || '', j.category || 'General', j.unit || 'nos', j.hsn || '', +j.citpc_rate || 0, m[1]);
        audit(u, null, 'Catalog item updated: ' + j.name);
        return send(res, 200, { ok: 1 });
      }
      if (M === 'DELETE') {
        if (!adm) throw E('Security Authorization Failed: Only System Administrators can delete Master Catalog items.', 403);
        const item = one('select * from item_master where id=?', m[1]);
        if (!item) throw E('Catalog item not found in database.', 404);

        // Security Check 1: Mandatory confirmation token
        if (j.confirm !== 'DELETE' && j.confirm !== item.code) {
          throw E('Security Verification Failed: Type "DELETE" or the exact Item Code to confirm deletion.', 400);
        }

        // Security Check 2: Administrator password verification
        if (j.password) {
          const uRec = one('select pw from users where id=?', u.id);
          if (!uRec || !chk(String(j.password), uRec.pw)) {
            throw E('Security Verification Failed: Invalid Administrator password.', 401);
          }
        }

        // Security Check 3: Active Requisition and PO dependency protection
        const prCount = (one('select count(1) c from items where lower(trim(name)) = lower(trim(?)) or lower(trim(model)) = lower(trim(?))', item.name, item.code) || {}).c || 0;
        const poCount = (one('select count(1) c from po_items where lower(trim(name)) = lower(trim(?))', item.name) || {}).c || 0;
        if ((prCount > 0 || poCount > 0) && !j.force) {
          throw E(`Security Protection: Cannot delete "${item.name}". It is actively referenced in ${prCount} Requisition(s) and ${poCount} Purchase Order(s). Deletion would corrupt audit records. Explicit override required.`, 409);
        }

        run('delete from item_master where id=?', m[1]);
        audit(u, null, `Security: Master Catalog item permanently deleted: ${item.code} (${item.name}) by Admin [${u.username}]${(prCount || poCount) ? ' [Force Override]' : ''}`);
        return send(res, 200, { ok: 1, deleted: item.code });
      }
    }

    // Vendor Directory CRUD
    if (P === '/api/vendors' && M === 'GET') {
      return send(res, 200, all('select * from vendors order by name'));
    }
    if (P === '/api/vendors' && M === 'POST') {
      W();
      const name = String(j.name || '').trim();
      if (!name) throw E('Vendor name is required', 400);
      const gst = String(j.gst || '').toUpperCase().trim();
      const pan = (String(j.pan || '').toUpperCase().trim()) || (gst.length === 15 ? gst.slice(2, 12) : '');
      const r = run('insert into vendors(name,address,gst,contact,phone,email,pan,msme_type,msme_no,bank_name,bank_ac,ifsc,payment_terms,rating,city,state,pincode) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        name, String(j.address || '').trim(), gst, String(j.contact || '').trim(), String(j.phone || '').trim(), String(j.email || '').trim(), pan, j.msme_type || 'None', String(j.msme_no || '').trim(), String(j.bank_name || '').trim(), String(j.bank_ac || '').trim(), String(j.ifsc || '').toUpperCase().trim(), j.payment_terms || '30 days', +j.rating || 4.5, String(j.city || '').trim(), String(j.state || '').trim(), String(j.pincode || '').trim());
      const vid = Number(r.lastInsertRowid);
      audit(u, null, 'Vendor added: ' + name);
      const created = one('select * from vendors where id=?', vid);
      return send(res, 200, created || { id: vid, name });
    }
    if (P === '/api/vendors/import' && M === 'POST') {
      W();
      let a = 0, b = 0;
      for (const v of j.rows || []) {
        if (!v.name) continue;
        const g = String(v.gst || '').toUpperCase().trim();
        const pan = v.pan || (g.length === 15 ? g.slice(2, 12) : '');
        const ex = g ? one('select id from vendors where gst=?', g) : one('select id from vendors where lower(name)=lower(?)', v.name);
        if (ex) {
          run('update vendors set name=?,address=?,contact=?,phone=?,email=?,pan=?,msme_type=?,bank_name=?,bank_ac=?,ifsc=? where id=?',
            v.name, v.address || '', v.contact || '', v.phone || '', v.email || '', pan, v.msme_type || 'None', v.bank_name || '', v.bank_ac || '', v.ifsc || '', ex.id);
          b++;
        } else {
          run('insert into vendors(name,address,gst,contact,phone,email,pan,msme_type,bank_name,bank_ac,ifsc,rating) values(?,?,?,?,?,?,?,?,?,?,?,?)',
            v.name, v.address || '', g, v.contact || '', v.phone || '', v.email || '', pan, v.msme_type || 'None', v.bank_name || '', v.bank_ac || '', v.ifsc || '', 4.5);
          a++;
        }
      }
      audit(u, null, `Vendor import: ${a} new, ${b} updated`);
      return send(res, 200, { added: a, updated: b });
    }

    if ((m = P.match(/^\/api\/vendors\/(\d+)$/))) {
      if (M === 'PUT') {
        W();
        const name = String(j.name || '').trim();
        if (!name) throw E('Vendor name is required', 400);
        const gst = String(j.gst || '').toUpperCase().trim();
        const pan = (String(j.pan || '').toUpperCase().trim()) || (gst.length === 15 ? gst.slice(2, 12) : '');
        run('update vendors set name=?,address=?,gst=?,contact=?,phone=?,email=?,pan=?,msme_type=?,msme_no=?,bank_name=?,bank_ac=?,ifsc=?,payment_terms=?,rating=?,city=?,state=?,pincode=? where id=?',
          name, String(j.address || '').trim(), gst, String(j.contact || '').trim(), String(j.phone || '').trim(), String(j.email || '').trim(), pan, j.msme_type || 'None', String(j.msme_no || '').trim(), String(j.bank_name || '').trim(), String(j.bank_ac || '').trim(), String(j.ifsc || '').toUpperCase().trim(), j.payment_terms || '30 days', +j.rating || 4.5, String(j.city || '').trim(), String(j.state || '').trim(), String(j.pincode || '').trim(), m[1]);
        audit(u, null, 'Vendor updated: ' + name);
        const updated = one('select * from vendors where id=?', m[1]);
        return send(res, 200, updated || { ok: 1 });
      }
      if (M === 'DELETE') {
        verifySecurityDelete(u, j, adm, 'Vendors');
        const hasQuotes = one('select 1 from quotes where vendor_id=?', m[1]);
        if (hasQuotes) {
          run('delete from qitems where quote_id in (select id from quotes where vendor_id=?)', m[1]);
          run('delete from quotes where vendor_id=?', m[1]);
        }
        const v = one('select name from vendors where id=?', m[1]);
        run('delete from vendors where id=?', m[1]);
        audit(u, null, `SECURE DELETE: Vendor "${v ? v.name : 'ID ' + m[1]}" permanently deleted by ${u.username}`);
        return send(res, 200, { ok: 1 });
      }
    }

    if ((m = P.match(/^\/api\/vendors\/(\d+)\/history$/))) {
      return send(res, 200, all(`select distinct p.id,p.code,p.title,p.type,p.stage,q.type as qtype,q.qdate from quotes q join proc p on p.id=q.proc_id where q.vendor_id=? order by q.qdate desc`, m[1]));
    }

    // Audit Log & Reports
    if (P === '/api/audit') return send(res, 200, all('select a.*,p.code from audit a left join proc p on p.id=a.proc_id order by a.id desc limit 600'));
    if (P === '/api/audit/csv') {
      const rows = all('select a.at, a.user, p.code as requisition, a.act as action_recorded from audit a left join proc p on p.id=a.proc_id order by a.id desc');
      const headers = ['Timestamp', 'User', 'Requisition', 'Action'];
      const csv = [headers.join(','), ...rows.map(r => [
        `"${r.at || ''}"`,
        `"${r.user || ''}"`,
        `"${r.requisition || 'System'}"`,
        `"${(r.action_recorded || '').replace(/"/g, '""')}"`
      ].join(','))].join('\n');
      res.writeHead(200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="compliance-audit-trail.csv"'
      });
      return res.end('\ufeff' + csv);
    }
    if (P === '/api/report.csv') {
      const rows = all('select code,type,kind,title,dept,location,est,stage,citpc_ref,pr_no,pr_date,hod_date,comm_date,created from proc');
      const c = [Object.keys(rows[0] || { code: 1 }).join(','), ...rows.map(r => Object.values(r).map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
      res.writeHead(200, { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=procurement-register.csv' });
      return res.end('\ufeff' + c);
    }

    // Python-Powered Tally XML, Excel Workbook & Spend Analytics Endpoints
    if (P === '/api/export/tally') {
      const { execFile } = require('child_process');
      const pyScript = path.join(__dirname, 'python', 'tally_bridge.py');
      return execFile('python', [pyScript, '--stdout'], { maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
        if (err) return send(res, 500, { error: 'Failed to generate Tally XML: ' + err.message });
        res.writeHead(200, {
          'Content-Type': 'application/xml; charset=utf-8',
          'Content-Disposition': 'attachment; filename="tally_purchase_orders.xml"'
        });
        return res.end(stdout);
      });
    }

    if (P === '/api/export/excel') {
      const { execFile } = require('child_process');
      const pyScript = path.join(__dirname, 'python', 'excel_reports.py');
      return execFile('python', [pyScript, '--stdout'], { maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
        if (err) return send(res, 500, { error: 'Failed to generate Excel report: ' + err.message });
        res.writeHead(200, {
          'Content-Type': 'application/vnd.ms-excel; charset=utf-8',
          'Content-Disposition': 'attachment; filename="executive_procurement_report.xls"'
        });
        return res.end(stdout);
      });
    }

    if (P === '/api/analytics/spend') {
      const { execFile } = require('child_process');
      const pyScript = path.join(__dirname, 'python', 'spend_analytics.py');
      return execFile('python', [pyScript, '--json'], { maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
        if (err) return send(res, 500, { error: 'Failed to run spend analytics: ' + err.message });
        try {
          return send(res, 200, JSON.parse(stdout));
        } catch {
          return send(res, 500, { error: 'Invalid analytics output' });
        }
      });
    }

    // Enterprise Reports Dataset API (Powers Multi-Dimensional Reporting: Vendor, Date, PO, GRN, Invoices & Assets)
    if (P === '/api/reports/dataset' && M === 'GET') {
      const pos = all(`
        select po.*, p.code as proc_code, p.title as proc_title, p.dept, p.location as proc_location,
               p.type as proc_type, p.kind as proc_kind, p.stage as proc_stage, p.is_locked,
               v.gst as vendor_gst, v.city as vendor_city, v.rating as vendor_rating
        from pos po
        left join proc p on p.id = po.proc_id
        left join vendors v on v.id = po.vendor_id
        order by po.po_date desc, po.id desc
      `);

      const grns = all(`
        select g.*, po.po_no, po.vendor_name, po.vendor_id, p.code as proc_code, p.title as proc_title, p.dept
        from grns g
        left join pos po on po.id = g.po_id
        left join proc p on p.id = g.proc_id
        order by g.grn_date desc, g.id desc
      `);

      const invoices = all(`
        select inv.*, po.po_no, po.vendor_name, po.vendor_id, p.code as proc_code, p.title as proc_title, p.dept
        from invoices inv
        left join pos po on po.id = inv.po_id
        left join proc p on p.id = inv.proc_id
        order by inv.invoice_date desc, inv.id desc
      `);

      const assets = all(`
        select a.*, po.po_no, po.vendor_name, p.code as proc_code, p.title as proc_title, p.dept, p.type as proc_type
        from assets a
        left join pos po on po.id = a.po_id
        left join proc p on p.id = a.proc_id
        order by a.capitalization_date desc, a.id desc
      `);

      const allItems = all('select * from items');
      const procs = all('select * from proc order by id desc').map(p => {
        const pItems = allItems.filter(i => i.proc_id === p.id);
        const sanctionedVal = pItems.reduce((acc, i) => acc + (gt(i.final_rate || 0, i.final_gst) * i.qty), 0);
        return {
          ...p,
          items_count: pItems.length,
          total_sanctioned: sanctionedVal || p.est || 0
        };
      });

      const vendors = all('select id, name, gst, city, state, rating, payment_terms from vendors order by name');
      const depts = [...new Set(procs.map(p => p.dept).filter(Boolean))].sort();

      return send(res, 200, {
        pos,
        grns,
        invoices,
        assets,
        procs,
        vendors,
        depts
      });
    }

    // Admin & System Configuration
    if (!adm) throw E('Administrator privileges required for system settings.', 403);

    if (P === '/api/settings' && M === 'PUT') {
      for (const [k, v] of Object.entries(j)) {
        run('insert or replace into settings values(?,?)', k, JSON.stringify(v));
      }
      audit(u, null, 'System settings updated');
      return send(res, 200, { ok: 1 });
    }

    if (P === '/api/audit/clear' && M === 'POST') {
      if (!adm) throw E('Administrator permission required to clear the audit trail.', 403);
      run('delete from audit');
      audit(u, null, `Audit trail history archived and cleared by ${u.username}`);
      return send(res, 200, { ok: 1 });
    }

    if (P === '/api/db/export') {
      const data = fs.readFileSync(DBF);
      res.writeHead(200, {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': `attachment; filename="procure-backup-${today()}.db"`
      });
      return res.end(data);
    }

    if (P === '/api/users' && M === 'GET') return send(res, 200, all('select id,username,name,email,role,active from users'));
    if (P === '/api/users' && M === 'POST') {
      if (!ROLES[j.role] || !j.username || String(j.password || '').length < 8) {
        throw E('Valid username, system role, and 8+ character password are required.');
      }
      const username = String(j.username).trim();
      const name = (j.name || '').trim();
      const email = (j.email || '').trim();
      try {
        run('insert into users(username,name,email,role,pw) values(?,?,?,?,?)', username, name, email, j.role, hash(j.password));
      } catch (err) {
        if (err.message && err.message.includes('UNIQUE')) {
          throw E('Username already exists in the system.');
        }
        throw err;
      }
      audit(u, null, 'User created: ' + username);
      return send(res, 200, { ok: 1 });
    }

    if ((m = P.match(/^\/api\/users\/(\d+)$/)) && M === 'PUT') {
      const uTarget = one('select * from users where id=?', m[1]);
      if (!uTarget) throw E('User not found', 404);
      const role = (j.role && ROLES[j.role]) ? j.role : uTarget.role;
      const name = j.name !== undefined ? String(j.name).trim() : (uTarget.name || '');
      const email = j.email !== undefined ? String(j.email).trim() : (uTarget.email || '');
      const active = j.active !== undefined ? (j.active ? 1 : 0) : (uTarget.active ? 1 : 0);
      run('update users set role=?,name=?,email=?,active=? where id=?', role, name, email, active, m[1]);
      if (j.password) {
        if (String(j.password).length < 8) throw E('Password must be at least 8 characters long.');
        run('update users set pw=? where id=?', hash(j.password), m[1]);
      }
      for (const [t, s] of sessions) if (s.id == m[1]) sessions.delete(t);
      audit(u, null, 'User updated: #' + m[1] + ` (${uTarget.username})`);
      return send(res, 200, { ok: 1 });
    }

    if ((m = P.match(/^\/api\/users\/(\d+)$/)) && M === 'DELETE') {
      verifySecurityDelete(u, j, adm, 'User Accounts');
      if (Number(m[1]) === u.id) throw E('Cannot delete your own admin account');
      const target = one('select username from users where id=?', m[1]);
      run('delete from users where id=?', m[1]);
      for (const [t, s] of sessions) if (s.id == m[1]) sessions.delete(t);
      audit(u, null, `SECURE DELETE: User @${target?.username || m[1]} deleted by ${u.username}`);
      return send(res, 200, { ok: 1 });
    }

    if (P === '/api/backups' && M === 'GET') return send(res, 200, fs.readdirSync(BAK).filter(x => x.startsWith('backup-')).sort().reverse());
    if (P === '/api/backups' && M === 'POST') {
      const n = backup('manual');
      audit(u, null, 'Manual snapshot created: ' + n);
      return send(res, 200, { name: n });
    }
    if (P === '/api/restore' && M === 'POST') {
      restore(j.name);
      return send(res, 200, { ok: 1 });
    }

    send(res, 404, { error: 'API endpoint not found.' });
  } catch (e) {
    send(res, e.code >= 400 && e.code < 600 ? e.code : 500, { error: e.message });
  }
};

function startServer(port, maxTries = 10) {
  const srv = http.createServer(requestHandler);
  srv.once('error', err => {
    if ((err.code === 'EADDRINUSE' || err.code === 'EACCES') && maxTries > 0) {
      console.log(`Port ${port} in use, attempting port ${port + 1}...`);
      cfg.port = port + 1;
      startServer(port + 1, maxTries - 1);
    } else {
      console.error('Server listen error:', err);
    }
  });
  srv.listen(port, cfg.host, () => {
    console.log(`\n================================================================`);
    console.log(`  ProcureLocal v3 Enterprise Edition (SAP/Tally Grade)`);
    console.log(`  Server Online: http://localhost:${port}`);
    console.log(`  Data Directory: ${DD}`);
    console.log(`  Status: Active & Secure`);
    console.log(`================================================================\n`);
    try { backup('startup'); } catch (e) { console.log('Startup backup notice:', e.message); }
    setInterval(() => {
      try { backup('auto'); } catch (e) { console.log('Auto-backup notice:', e.message); }
    }, Math.max(1, S().backupHours) * 36e5);
  });
}

process.on('uncaughtException', err => {
  console.error('[ProcureLocal UncaughtException]', err);
});
process.on('unhandledRejection', reason => {
  console.error('[ProcureLocal UnhandledRejection]', reason);
});

startServer(cfg.port);


