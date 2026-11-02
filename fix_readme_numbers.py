"""
Fixes the two number mismatches across README / PRESENTATION / INTERN_REFLECTION /
TABLEAU guide / Streamlit app.

Run from the project root:   python fix_readme_numbers.py
Safe to run twice (it only replaces the old text).
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

FILES = ["README.md", "PRESENTATION.md", "INTERN_REFLECTION.md",
         os.path.join("data", "tableau_exports", "TABLEAU_DASHBOARD_GUIDE.md"),
         os.path.join("dashboard", "app.py")]

REPLACEMENTS = [
    # --- Net revenue lift: the per-channel rows sum to $58,843, which is 11.0% of paid-attributed revenue ---
    ("$41,863", "$58,843"),
    ("(+5.5%)", "(+11.0%)"),
    ("a 5.5% efficiency lift", "an 11.0% efficiency lift"),
    # Streamlit label: compute the percentage instead of hardcoding it
    ('"+5.5% efficiency lift"', 'f"{tot_lift / tot_curr_rev * 100:+.1f}% efficiency lift"'),
    # --- Customer counts: 1,926 clusters = 1,200 known CRM customers + 726 anonymous-only visitors ---
    ("1,926 canonical customer profiles",
     "1,926 identity clusters (1,200 known CRM customers + 726 anonymous-only visitors)"),
    ("1,926 canonical entities",
     "1,926 identity clusters (1,200 known customers + 726 anonymous visitors)"),
]

for rel in FILES:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        print(f"skip (not found): {rel}")
        continue
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    new, changes = text, 0
    for old, repl in REPLACEMENTS:
        n = new.count(old)
        if n:
            new, changes = new.replace(old, repl), changes + n
    if new != text:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    print(f"{rel}: {changes} replacement(s)")
