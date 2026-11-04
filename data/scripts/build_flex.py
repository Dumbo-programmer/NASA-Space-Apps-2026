"""
AgniShikha / Ignis mu - FLEX (PSI-69) clean dataset builder
Input : PSI-69_Experimental_table_FLEX.csv  (NASA PSI, CC0-1.0, 274 ISS droplet tests, Mar 2009 - Dec 2011)
Output: FLEX_PSI-69_clean_v1.0.csv
Run   : python build_flex.py <raw_csv> <out_dir>
"""
import sys, re
import numpy as np, pandas as pd

raw_path, out_dir = sys.argv[1], sys.argv[2]
raw = pd.read_csv(raw_path, dtype=str, encoding="utf-8")
raw.columns = ["test_no", "flex_id", "test_date_raw", "test_gmt", "fuel", "p_mmHg", "x_O2", "x_N2",
               "x_CO2", "x_He", "d0_mm", "d_ext_mm", "K_raw", "burn_time_raw", "test_end"]

flags = {i: [] for i in raw.index}
def flag(i, msg): flags[i].append(msg)

def num(col, label):
    out = []
    for i, v in raw[col].items():
        if v is None or (isinstance(v, float) and np.isnan(v)) or v == "":
            out.append(np.nan)
        elif "�" in v:
            out.append(np.nan); flag(i, f"{label}: unreadable character in NASA file -> missing")
        elif v.startswith("~"):
            out.append(float(v[1:])); flag(i, f"{label}: approximate value '{v}' in NASA file")
        else:
            out.append(float(v))
    return pd.Series(out, index=raw.index)

c = pd.DataFrame(index=raw.index)
c["record_id"] = [f"FLEX-{int(n):03d}" for n in raw.test_no]
c["psi_id"] = "PSI-69"
c["test_no"] = raw.test_no.astype(int)
c["flex_id"] = raw.flex_id
c["test_date"] = pd.to_datetime(raw.test_date_raw, format="mixed", dayfirst=False).dt.date.astype(str)
c["test_gmt"] = raw.test_gmt
c["gravity"] = "microgravity"
c["platform"] = "ISS CIR / MDCA"
c["fuel"] = raw.fuel.str.strip()

p = num("p_mmHg", "pressure")
for i in raw.index:
    if p[i] == 0:
        p[i] = np.nan; flag(i, "pressure recorded as 0 mmHg in NASA file -> missing (sister tests C11M ~535 mmHg)")
c["pressure_mmHg"] = p
c["pressure_kpa"] = (p * 0.133322).round(1)
c["pressure_atm"] = (p / 760).round(3)

for g in ["O2", "N2", "CO2", "He"]:
    c[f"x_{g}"] = num(f"x_{g}", g)
c["x_sum"] = c[["x_O2", "x_N2", "x_CO2", "x_He"]].sum(axis=1).round(3)
for i in raw.index:
    if abs(c.x_sum[i] - 1) > 0.015:
        flag(i, f"mole fractions sum to {c.x_sum[i]} (not 1.0, as printed by NASA)")
c["o2_pct"] = (c.x_O2 * 100).round(1)
c["o2_partial_pressure_kpa"] = (c.x_O2 * c.pressure_kpa).round(2)
c["diluent_added"] = np.select([c.x_CO2 > 0, c.x_He > 0], ["CO2", "He"], default="none (O2/N2 only)")
c["diluent_pct"] = ((c.x_CO2 + c.x_He) * 100).round(1)

c["d0_mm"] = num("d0_mm", "initial diameter")
c["d_ext_mm"] = num("d_ext_mm", "extinction diameter")
c["burning_rate_K_mm2_s"] = num("K_raw", "burning rate")
c["burn_time_s"] = num("burn_time_raw", "burn time")
c["test_end"] = raw.test_end.str.strip()

# ---- targets for modelling ----
c["extinguished"] = c.test_end.map({"Extinction": 1, "Completion": 0})       # Disruption -> NaN
c["use_for_extinction_model"] = c.extinguished.notna() & c.d0_mm.notna() & c.pressure_kpa.notna()
c["d_ext_over_d0"] = np.where((c.test_end == "Extinction") & c.d0_mm.gt(0) & c.d_ext_mm.notna(),
                              (c.d_ext_mm / c.d0_mm).round(3), np.nan)
c["extinction_regime_hint"] = np.select(
    [c.d_ext_over_d0 >= 0.9, c.d_ext_over_d0.between(0, 0.9, inclusive="left")],
    ["early extinction (d_ext/d0 >= 0.9, near-limit / radiative-type)", "extinction during burning"], default="")

dup = c.flex_id[c.flex_id.duplicated(keep=False)]
for i in dup.index:
    flag(i, "FLEX identifier appears twice in NASA file (193F001: tests 70 and 73, same time stamp, slightly different values)")
for i in raw.index:
    if raw.test_end[i] == "Disruption":
        flag(i, "Disruption: droplet broke up / was disturbed, so no clean extinction-or-completion outcome")

c["quality_flags"] = [" | ".join(flags[i]) for i in raw.index]
c["value_type"] = "observed (NASA PSI experimental table)"
c["source"] = "NASA PSI-69 FLEX Experimental Table (CC0-1.0), DOI 10.60555/mbq8-0451; see Dietrich et al., NASA/TP-2015-216046"

c.to_csv(f"{out_dir}/FLEX_PSI-69_clean_v1.0.csv", index=False)
print(c.shape)
print(c.test_end.value_counts().to_dict(), "| usable for extinction model:", int(c.use_for_extinction_model.sum()))
print(c.groupby("fuel").use_for_extinction_model.sum().to_dict())
print("flagged rows:", int((c.quality_flags != "").sum()))
