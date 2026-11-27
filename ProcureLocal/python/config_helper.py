#!/usr/bin/env python3
"""
ProcureLocal - Python Configuration & Database Path Resolver
-----------------------------------------------------------
Reads config.json from project root, resolves local or remote network share
database paths (UNC/mapped drives), and extracts server ports dynamically.
"""
import os
import json
from pathlib import Path

def get_app_config():
    """Locates and parses config.json from project directories."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "config.json",
        script_dir.parent.parent / "config.json",
        Path.cwd() / "config.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cfg["_config_path"] = str(c)
                    return cfg
            except Exception:
                pass
    return {"port": 3002, "dataDir": "./DB"}

def resolve_db_path(custom_db_path=None):
    """Resolves the active SQLite database path from CLI arg, config.json or default ./DB/procure.db."""
    if custom_db_path and os.path.exists(custom_db_path):
        return Path(custom_db_path).resolve()
    
    cfg = get_app_config()
    data_dir = cfg.get("dataDir")
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent
    
    if data_dir:
        p_str = str(data_dir).strip()
        if p_str.startswith(r"\\"):
            p = Path(p_str)
        elif os.path.isabs(p_str):
            p = Path(p_str)
        else:
            p = (root_dir / p_str).resolve()
        
        db_candidate = p / "procure.db" if (p.exists() and p.is_dir()) or not p_str.endswith(".db") else p
        if db_candidate.exists():
            return db_candidate

    default_db = (root_dir / "DB" / "procure.db").resolve()
    return default_db

def get_server_port():
    """Returns configured server port from config.json (default 3002)."""
    cfg = get_app_config()
    try:
        return int(cfg.get("port", 3002))
    except Exception:
        return 3002
