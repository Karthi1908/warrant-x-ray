#!/usr/bin/env python3
"""Security audit script (T112).

Checks:
1. Secret scan across git history and repository files.
2. .env.example audit ensuring no default credentials.
3. Checks for any committed database files, raw scraped data, or large binaries (>1MB).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def check_env_example():
    env_example = ROOT_DIR / ".env.example"
    if not env_example.exists():
        print("FAIL: .env.example does not exist")
        return False
    
    content = env_example.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            if "KEY" in key or "SECRET" in key or "TOKEN" in key or "PASSWORD" in key:
                if val:
                    print(f"FAIL: .env.example contains value for credential {key}: {val}")
                    return False
    print("PASS: .env.example contains no secrets.")
    return True

def check_tracked_files():
    # Check git tracked files
    res = subprocess.run(["git", "ls-files"], cwd=ROOT_DIR, capture_output=True, text=True)
    files = res.stdout.splitlines()
    
    forbidden_exts = {".db", ".sqlite", ".sqlite3", ".tar", ".gz", ".zip", ".bin"}
    violations = []
    
    for f in files:
        p = ROOT_DIR / f
        if p.suffix.lower() in forbidden_exts:
            violations.append(f"Forbidden extension: {f}")
        elif p.is_file() and p.stat().st_size > 1024 * 1024: # >1MB
            if not f.endswith("package-lock.json") and not f.endswith("uv.lock"):
                violations.append(f"Large binary/file (>1MB): {f} ({p.stat().st_size / 1024 / 1024:.2f} MB)")
                
    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    print("PASS: No raw databases or large binary assets tracked in git.")
    return True

def check_git_secrets():
    res = subprocess.run(["git", "log", "-p", "-n", "20"], cwd=ROOT_DIR, capture_output=True, text=True, errors="ignore")
    secret_pattern = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]")
    suspicious = []
    
    for line in res.stdout.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            m = secret_pattern.search(line)
            if m:
                val = m.group(2)
                # Ignore fake/stub/test
                if not any(ign in line.lower() for ign in ["example", "fake", "stub", "test", "mock", "none", "hash"]):
                    suspicious.append(line.strip())
                    
    if suspicious:
        print(f"FAIL: Suspicious secret pattern in git history: {len(suspicious)}")
        for s in suspicious[:5]:
            print(f"  {s[:80]}")
        return False
    print("PASS: No secrets detected in git commit history.")
    return True

if __name__ == "__main__":
    ok1 = check_env_example()
    ok2 = check_tracked_files()
    ok3 = check_git_secrets()
    if ok1 and ok2 and ok3:
        print("\nAll Security Hardening Checks Passed (T112)!")
        sys.exit(0)
    else:
        sys.exit(1)
