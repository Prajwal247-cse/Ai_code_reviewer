"""
Sample: bad_code.py
This file intentionally contains multiple issues for demo/testing purposes.
Use it to test the AI Code Reviewer.
"""

import os
import pickle

# ── ISSUE: Hardcoded credentials (SEC-010, SEC-011) ──────────────────────────
DB_PASSWORD = "admin123"
API_KEY = "sk-1234567890abcdefghijklmno"


# ── ISSUE: Mutable default argument (ARG-001) ─────────────────────────────────
def process_requests(request, history=[]):
    """Process incoming requests."""
    history.append(request)
    return history


# ── ISSUE: eval() usage (SEC-001) ─────────────────────────────────────────────
def calculate(expression):
    # FIXME: This is dangerous
    return eval(expression)


# ── ISSUE: Bare except (EXC-001), print() (LOG-001), SQL injection ────────────
def get_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    try:
        # TODO: use parameterized query
        result = execute_query(query)
        print(f"Found user: {result}")
        return result
    except:
        pass


# ── ISSUE: File not closed (BUG-006), no error handling ──────────────────────
def read_config(path):
    f = open(path, "r")
    data = f.read()
    return data


# ── ISSUE: High cyclomatic complexity (CPX-001) ───────────────────────────────
def validate_order(order, user, items, promo, region):
    if order:
        if user:
            if user.get("verified"):
                if items:
                    for item in items:
                        if item.get("in_stock"):
                            if promo:
                                if promo.get("valid"):
                                    if region in ["US", "EU"]:
                                        if order.get("total") > 0:
                                            return True
    return False


# ── ISSUE: Unsafe deserialization (SEC-003) ───────────────────────────────────
def load_session(data: bytes):
    return pickle.loads(data)


# ── ISSUE: os.system with user input (SEC-005) ────────────────────────────────
def run_command(cmd):
    os.system(cmd)


# ── ISSUE: String concatenation in "loop-like" scenario ──────────────────────
def build_csv(rows):
    result = ""
    for row in rows:
        result += ",".join(str(x) for x in row) + "\n"
    return result
