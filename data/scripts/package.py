import sys, hashlib, os, shutil, numpy as np, pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
R, D, E, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)

files = {
 "Ignis_mu_unified_master_v1.0.csv": ("All sources, one row per run", "experiment conditions (O2, pressure, airflow, material, size, gravity)", "outcome_value / outcome_class (routed by outcome_type)", "Retrieval database (pgvector) + ML routing"),
 "FLEX_PSI-69_clean_v1.0.csv": ("FLEX droplet tests (ISS, 2009-2011)", "fuel, pressure, O2/N2/CO2/He fractions, initial droplet diameter", "test_end (Extinction/Completion/Disruption), extinction diameter, burning-rate constant, burn time", "Model 2: extinction classifier; regression on d_ext or K"),
 "SPICE_PSI-107_smoke_points_v1.0.csv": ("SPICE smoke points (ISS, 2009)", "fuel, burner diameter, coflow air velocity, fuel flow", "smoke_point_length_mm (sooting tendency)", "Model 3: smoke-point regression"),
 "SAME_PSI-101-102_smoke_particles_v1.0.csv": ("SAME + SAME-R smoke particles (ISS, 2008 + 2010)", "material, heater setting / sample temperature, air velocity, aging time", "particle count-mean diameter, mass-mean diameter, number and mass concentration", "Model 4: smoke particle size (detector design)"),
 "BASS_PSI-26_test_log_v1.0.csv": ("BASS test log (ISS, 2012-2013)", "material, geometry, O2, pressure, air settings", "burn outcome label + crew observation text", "Retrieval text (flame_behavior_notes); small classifier"),
 "SAFFIRE_I-III_PSI-98-100_v1.0.csv": ("Saffire I-III large-scale burns (Cygnus, 2016-2017)", "material, thickness, flow, flow direction, ignition power", "sustained spread (yes/no), burn time, spread rate, 1g comparison", "Retrieval evidence; 1g vs microgravity story"),
 "BASS-II_flame_spread_microgravity_v1.0.csv": ("BASS-II flame spread (ISS, 2014) - from earlier work", "O2, opposed flow, rod diameter", "flame_spread_mm_s", "Model 1 (done)"),
}
for f in files:
    src = f"{D}/{f}" if os.path.exists(f"{D}/{f}") else f"{E}/{f}"
    if os.path.abspath(src) != os.path.abspath(f"{OUT}/{f}"):
        shutil.copy(src, f"{OUT}/{f}")

M = pd.read_csv(f"{D}/Ignis_mu_unified_master_v1.0.csv")
counts = M.groupby(["source_investigation", "psi_id", "gravity_level"], dropna=False).size().reset_index(name="rows_in_master")
usable = {"FLEX": "206 usable for extinction model (Extinction 186 / Completion 27 / Disruption 61 excluded)",
          "SPICE": "55 smoke points, all usable", "SAME": "130 of 154 SAME/SAME-R runs usable for particle-size model",
          "SAME-R": "(see SAME)", "BASS": "118 with a valid outcome (3 hardware failures)", "BASS-II": "52 flame-spread + 129 log rows (119 usable gas response)",
          "WSTF 1g ground (Hirsch 2011)": "52 (1g reference only)"}
counts["note"] = counts.source_investigation.map(usable).fillna("tiny table - evidence only")
abstract = pd.DataFrame([
 ["FLEX", "274 (abstract)", "274 tests in NASA table (PSI-69); 206 usable for extinction model", "abstract number is correct for raw tests"],
 ["SPICE", "469 (abstract)", "470 flame-condition log rows; 55 smoke points (the measured outcome)", "say '55 smoke points' (469/470 are flame settings, not results)"],
 ["SAFFIRE-I", "4 (abstract)", "2 burns (Saffire-I); 13 sample burns across Saffire I-III", "say 'Saffire I-III: 13 samples'"],
 ["SAME", "8 (abstract)", "8 = test matrix rows only; 154 measured smoke runs in SAME + SAME-R results", "say '154 smoke runs (SAME + SAME-R)'"],
 ["Spec PDF total", "~1,000-1,300", "850 normalised rows from 10 sources (798 microgravity + 52 1g)", "update the spec"],
], columns=["dataset", "number we used before", "verified number (Nov 2026)", "what to write"])

def h(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
ver = pd.DataFrame([
 ["PSI-69_Experimental_table_FLEX.csv", "NASA PSI-69 experimental table", "full file", "SHA-256 identical to NASA S3 file (24,776 bytes)"],
 ["PSI-107_SmokePointReview-0g-3_SmokePointDatasheet_extract.csv", "NASA PSI-107 'Raw Data_SmokePointReview-0g-3.xlsx', sheet 'Smoke Point Datasheet'", "19 columns, 6 significant digits", "extract SHA-256 identical in browser and here"],
 ["PSI-101_SAME_SAME-R_Results_ReducedDataSheet_extract.csv", "NASA PSI-101 'Analyzed Data_SAME, SAME-R_Results.xlsx', sheet 'Reduced data sheet'", "20 columns, 6 significant digits", "extract SHA-256 identical"],
 ["PSI-26_AsRunTestMatrix_extract_raw.csv (+ _O2_extract)", "NASA PSI-26 'Science Documents_As Run_Test Matrix.xlsx', sheet 'as run matrix'", "setup columns + observations (repeated spaces collapsed)", "extract SHA-256 identical"],
 ["PSI-98/99/100 SAFFIRE, PSI-101/102 SAME tables, PSI-68 FLEX-2", "NASA PSI experimental tables", "full files", "SHA-256 identical"],
 ["PSI-25 BASS-II table (your Oct upload)", "NASA PSI-25 experimental table", "full file", "identical to NASA's current version"],
 ["All clean files vs raw", "verify_all.py", "890 field checks", "0 problems"],
], columns=["file", "NASA source", "what was taken", "verification"])
ver["local_sha256_16"] = [h(f"{R}/{n.split(' ')[0]}") if os.path.exists(f"{R}/{n.split(' ')[0]}") else "" for n in ver.file]

dictionary = pd.DataFrame([
 ["experiment_id", "unique run id (prefix = source)", "-", "ID - never a model feature"],
 ["source_investigation / psi_id", "NASA investigation and PSI number", "-", "routing / grouping"],
 ["gravity_level", "microgravity or 1g (ground)", "-", "never mix 1g rows into microgravity training"],
 ["fuel_material, material_class", "what burned; solid / liquid droplet / gas jet / heated (smoke)", "-", "feature (categorical)"],
 ["configuration", "geometry and flow arrangement", "-", "feature / filter before similarity search"],
 ["ignition_method", "only filled where the source states it", "-", "context"],
 ["oxygen_pct", "ambient O2", "% by volume", "feature"],
 ["pressure_kpa", "ambient pressure", "kPa", "feature"],
 ["airflow_cm_s / airflow_note", "forced/coflow/opposed velocity; text when only settings are logged", "cm/s", "feature"],
 ["diluent", "added inert gas", "-", "feature"],
 ["characteristic_size_mm", "droplet / rod diameter, burner diameter or sample thickness (see source)", "mm", "feature (meaning depends on source)"],
 ["temperature_c", "sample temperature (SAME heater)", "deg C", "feature"],
 ["smoke_signal_mg_m3", "smoke mass concentration (SAME DustTrak)", "mg/m3", "maps to optical smoke sensor"],
 ["outcome_type", "regression / classification / threshold", "-", "tells the backend which model or ranking to use"],
 ["outcome_variable, outcome_value, outcome_unit", "the measured result for this row", "see unit", "TARGET"],
 ["outcome_class", "categorical result (e.g. Extinction / Completion; sustained burn / no ignition)", "-", "TARGET (classification)"],
 ["flame_behavior_notes", "short text description (BASS: NASA crew notes verbatim)", "-", "embed for semantic retrieval"],
 ["value_type", "observed / derived / hand-labelled", "-", "show in UI next to every number"],
 ["source_ref, source_record_id", "exact NASA file / paper and row", "-", "evidence drawer"],
 ["quality_flags", "every issue found while cleaning", "-", "filter before training"],
], columns=["column", "meaning", "unit", "role"])

readme = pd.DataFrame({"Ignis mu / AgniShikha - NASA microgravity fire dataset v1.0 (Nov 2026)": [
 "Built from NASA Physical Sciences Informatics (PSI) files, all CC0-1.0 (public domain). Every extract was verified byte-for-byte against NASA's file.",
 "850 rows in the unified master table: 798 microgravity runs from 9 ISS/Cygnus investigations + 52 rows of 1g ground reference (WSTF).",
 "Per-investigation clean files keep all original columns that matter; the master table normalises them into one schema for retrieval.",
 "Models: BASS-II flame spread (done). Ready next: FLEX extinction classifier (206 rows), SPICE smoke point (55), SAME particle size (130).",
 "Gaps: FLEX-2 and CFI tables list conditions only (no outcomes); SAFFIRE results beyond the summary table sit in very large telemetry files; SPICE 2012 flight (methane/ethane) not included.",
 "Do not mix 1g rows into microgravity training. Do not use a model outside the tested ranges (see each README).",
 "Sheets: Data_Map, Row_counts_for_abstract, Data_dictionary, Verification, then one sheet per dataset.",
]})
data_map = pd.DataFrame([[f, *v] for f, v in files.items()], columns=["file", "what it is", "inputs (features)", "outputs (targets)", "use in project"])
data_map["rows"] = [len(pd.read_csv(f"{OUT}/{f}")) for f in files]

xl = f"{OUT}/Ignis_mu_NASA_dataset_v1.0.xlsx"
with pd.ExcelWriter(xl, engine="openpyxl") as w:
    readme.to_excel(w, sheet_name="README", index=False)
    data_map.to_excel(w, sheet_name="Data_Map", index=False)
    abstract.to_excel(w, sheet_name="Row_counts_for_abstract", index=False)
    counts.to_excel(w, sheet_name="Rows_per_source", index=False)
    dictionary.to_excel(w, sheet_name="Data_dictionary", index=False)
    ver.to_excel(w, sheet_name="Verification", index=False)
    M.to_excel(w, sheet_name="master", index=False)
    for f, name in [("FLEX_PSI-69_clean_v1.0.csv", "FLEX"), ("SPICE_PSI-107_smoke_points_v1.0.csv", "SPICE"),
                    ("SAME_PSI-101-102_smoke_particles_v1.0.csv", "SAME"), ("BASS_PSI-26_test_log_v1.0.csv", "BASS"),
                    ("SAFFIRE_I-III_PSI-98-100_v1.0.csv", "SAFFIRE")]:
        pd.read_csv(f"{OUT}/{f}").to_excel(w, sheet_name=name, index=False)
wb = load_workbook(xl)
head = PatternFill("solid", fgColor="1F3A5F")
for ws in wb.worksheets:
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = head; c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    for i, col in enumerate(ws.columns, 1):
        width = min(60, max(10, max(len(str(c.value or "")) for c in list(col)[:60]) + 2))
        ws.column_dimensions[get_column_letter(i)].width = width if ws.title not in ("README",) else 140
    if ws.title in ("Data_Map", "Row_counts_for_abstract", "Verification", "Data_dictionary", "README"):
        for row in ws.iter_rows(min_row=2):
            for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
wb.save(xl)

# raw extracts + scripts: only when building a standalone bundle in a separate folder (never duplicated inside data/processed)
if os.path.abspath(OUT) != os.path.abspath(D):
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(f"{OUT}/raw_from_NASA", exist_ok=True); os.makedirs(f"{OUT}/scripts", exist_ok=True)
    for f in os.listdir(R): shutil.copy(f"{R}/{f}", f"{OUT}/raw_from_NASA/{f}")
    for f in ["build_flex.py", "build_spice.py", "build_same.py", "build_bass_saffire.py", "build_master.py", "verify_all.py", "package.py"]:
        shutil.copy(f"{here}/{f}", f"{OUT}/scripts/{f}")
print(data_map[["file", "rows"]].to_string(index=False)); print(abstract.to_string(index=False))
