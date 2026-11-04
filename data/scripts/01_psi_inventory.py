"""
Ignis μ — Step A1: NASA PSI data inventory
Team AgniShikha · Data Science Lead: Prachya Biswas

What it does
  Scans a folder of downloaded NASA PSI files (CSV / XLSX / XLS / JSON / TXT),
  and writes ONE Excel report describing every table: rows, columns, data types,
  missing %, numeric ranges, example values, and likely units/roles.
  It does NOT change, guess, or fill any data.

How to run (Colab or laptop)
  1. Put all PSI files in one folder, one sub-folder per investigation, e.g.
       psi_raw/FLEX_PSI-69/...   psi_raw/BASS-II_PSI-25/...   psi_raw/SAFFIRE-I_PSI-98/...
  2. pip install pandas openpyxl
  3. python 01_psi_inventory.py psi_raw
  4. Output: psi_inventory.xlsx  (send this file to the team / Claude)
"""
import sys, re, json
from pathlib import Path
import pandas as pd

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "psi_raw")
OUT = Path("psi_inventory.xlsx")

UNIT_HINTS = {
    r"(o2|oxygen|xo2)": "oxygen (check: % vs mole fraction)",
    r"(press|kpa|atm|psi|bar)": "pressure (check unit)",
    r"(flow|velocity|vel|cm/s|mm/s|m/s)": "airflow / velocity",
    r"(temp|kelvin|\bk\b|degc|°c)": "temperature",
    r"(diam|d0|d_0|dext|ext.*diam)": "droplet diameter",
    r"(burn.*rate|\bk\b|evap)": "burning rate (check)",
    r"(time|\bt\b|duration|sec)": "time",
    r"(spread|vf|front)": "flame spread",
    r"(length|height|lf)": "length",
    r"(fuel|material|sample)": "fuel / material (categorical)",
    r"(diluent|n2|he|co2|xe|inert)": "diluent gas",
    r"(run|test|id|drop|point)": "identifier (use for grouping, not as feature)",
    r"(extinct|quench|outcome|result)": "outcome / extinction",
    r"(soot|smoke|particle|pm)": "smoke / soot",
}

def hint(col):
    c = str(col).lower()
    found = [v for k, v in UNIT_HINTS.items() if re.search(k, c)]
    return "; ".join(dict.fromkeys(found))

def read_any(p):
    s = p.suffix.lower()
    if s == ".csv":
        return {"": pd.read_csv(p, low_memory=False)}
    if s in (".xlsx", ".xls"):
        return pd.read_excel(p, sheet_name=None)
    if s == ".json":
        with open(p) as f: data = json.load(f)
        return {"": pd.json_normalize(data if isinstance(data, list) else [data])}
    if s in (".txt", ".dat", ".tsv"):
        return {"": pd.read_csv(p, sep=None, engine="python")}
    return {}

files_rows, cols_rows, problems = [], [], []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file():
        continue
    investigation = p.relative_to(ROOT).parts[0] if len(p.relative_to(ROOT).parts) > 1 else "(root)"
    try:
        tables = read_any(p)
    except Exception as e:
        problems.append({"file": str(p), "investigation": investigation, "error": repr(e)[:300]})
        continue
    if not tables:
        problems.append({"file": str(p), "investigation": investigation, "error": "unsupported type (skipped)"})
        continue
    for sheet, df in tables.items():
        tid = f"{p.name}{'::' + sheet if sheet else ''}"
        files_rows.append({"investigation": investigation, "table_id": tid, "path": str(p),
                           "rows": len(df), "columns": df.shape[1],
                           "duplicate_rows": int(df.duplicated().sum()),
                           "fully_empty_columns": int(df.isna().all().sum())})
        for col in df.columns:
            s = df[col]
            num = pd.to_numeric(s, errors="coerce")
            is_num = num.notna().sum() >= max(1, 0.8 * s.notna().sum())
            cols_rows.append({
                "investigation": investigation, "table_id": tid, "column": str(col),
                "dtype": "numeric" if is_num else "text/categorical",
                "non_missing": int(s.notna().sum()),
                "missing_pct": round(100 * s.isna().mean(), 1),
                "unique": int(s.nunique(dropna=True)),
                "min": num.min() if is_num else None,
                "max": num.max() if is_num else None,
                "example_values": ", ".join(map(str, s.dropna().astype(str).unique()[:5])),
                "likely_role_or_unit": hint(col),
                # filled by the team after reading NASA metadata:
                "confirmed_unit": "", "role (feature/target/id/meta)": "", "notes": "",
            })

with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
    pd.DataFrame(files_rows).to_excel(xw, sheet_name="Tables", index=False)
    pd.DataFrame(cols_rows).to_excel(xw, sheet_name="Columns", index=False)
    pd.DataFrame(problems or [{"file": "", "investigation": "", "error": "none"}]).to_excel(xw, sheet_name="Problems", index=False)

print(f"Scanned {len(files_rows)} tables, {len(cols_rows)} columns, {len(problems)} problems -> {OUT}")
