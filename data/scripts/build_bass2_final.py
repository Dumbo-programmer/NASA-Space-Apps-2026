"""Ignis μ · BASS-II final dataset builder (v1.0)
Targets from: Link, Huang, Fernandez-Pello, Olson, Ferkul (2018) Sci Rep 8:120, Supplementary Tables S1/S2 (CC BY 4.0)
Joined to: NASA PSI-25 BASS-II Experimental Table (cleaned v0.1)"""
import pandas as pd, numpy as np
SRC = "Link et al. 2018, Sci Rep 8:120, doi:10.1038/s41598-017-18398-4"
# ---- Table S1 (microgravity, ISS). (d_cm, XO2, label, [(Vg, dt, Vf_x1e3)])
S1 = [
 (1.27,20.7,"B13a",[(1.64,184,5.23),(1.54,232,5.27),(1.43,239,4.63),(1.38,238,4.69)]),
 (1.27,20.6,"B13b",[(1.64,159,7.09),(1.54,179,4.91)]),
 (1.27,19.3,"B5",  [(1.64,192,3.76),(1.54,241,3.74)]),
 (1.27,17.6,"B9",  [(1.64,147,4.57),(1.54,76,3.34),(1.43,154,2.67),(1.38,112,2.03)]),
 (0.95,20.9,"C25", [(1.58,115,6.09),(1.52,169,5.50),(1.48,181,5.59)]),
 (0.95,20.8,"B22", [(1.58,123,6.45),(1.58,79,8.31),(1.52,120,5.89),(1.48,146,4.10)]),
 (0.95,18.5,"B4",  [(2.00,177,3.25),(1.87,131,3.10),(1.73,145,2.69)]),
 (0.95,17.5,"B12", [(1.01,121,3.08),(0.82,134,3.45),(0.60,129,3.65),(0.48,158,2.37)]),
 (0.64,18.9,"B6",  [(2.00,90,10.00),(1.87,121,9.74),(1.73,93,8.32)]),
 (0.64,18.4,"B15", [(2.14,424,7.16)]),
 (0.64,18.4,"B14", [(1.98,384,6.38)]),
 (0.64,18.2,"B16", [(7.55,72,6.78),(1.67,139,7.62),(0.83,198,6.99),(0.72,170,5.68)]),
 (0.64,17.7,"B1",  [(4.00,794,7.15),(2.15,23,5.91)]),
 (0.64,17.7,"C3a", [(2.50,33,8.37),(2.00,30,6.42)]),
 (0.64,17.5,"B19", [(7.55,67,4.69),(1.67,128,6.52),(0.83,189,6.25),(0.72,200,5.44)]),
 (0.64,17.4,"B2",  [(2.50,24,7.25),(2.00,28,7.87)]),
 (0.64,17.4,"C3b", [(1.85,109,6.00)]),
 (0.64,17.0,"B10", [(2.00,106,5.41),(1.87,104,5.15),(1.73,148,4.22)]),
 (0.64,16.8,"P17", [(1.01,123,4.12),(0.82,187,4.78),(0.41,65,2.26)]),
]
log = pd.read_csv("BASS-II_PSI-25_clean_v0.1.csv")
log = log.set_index("test_id")
rows, k = [], 0
for d, xo2, lab, steps in S1:
    test = {"B22": "P22a"}.get(lab, "P" + lab[1:])
    L = log.loc[test] if test in log.index else None
    for i, (vg, dt, vf) in enumerate(steps, 1):
        k += 1
        flags = []
        o2log = L.o2_initial_pct if L is not None else np.nan
        if L is not None and abs(o2log - xo2) > 0.3: flags.append(f"O2 differs: paper {xo2} vs PSI log {o2log}")
        if lab == "B22": flags.append("Table S1 says B22; PSI log has P22a (20.8%) and P22b (20.0%); matched to P22a by O2")
        if lab.startswith("C"): flags.append("clear PMMA (paper analysis focuses on black)")
        if lab.startswith("P"): flags.append("label printed as P17 in Table S1 (colour not given; log says black)")
        if vg < 0.6: flags.append("flow < 0.6 cm/s: below lowest-spread flow reported for B16/B19")
        rows.append(dict(
            record_id=f"BASS2-FS-UG-{k:03d}", test_id=test, s1_label=lab, psi_id="PSI-25",
            pi_group="Fernandez-Pello", gravity="microgravity", platform="ISS MSG (BASS-II)",
            material="PMMA rod (cast)", pmma_color=("clear" if lab.startswith("C") else "black"),
            diameter_cm=d, diameter_mm=round(d*10,1), inv_diameter_per_cm=round(1/d,3),
            o2_pct=xo2, o2_psi_log_pct=o2log, opposed_flow_cm_s=vg,
            flow_step=i, n_flow_steps=len(steps), tracking_dt_s=dt,
            vf_x1e3_cm_s_raw=vf, flame_spread_mm_s=round(vf*1e-3*10,4),
            test_date=(L.date if L is not None else None),
            psi_log_air_text=(L.air_display_raw if L is not None else None),
            value_type="observed (published, processed by authors)",
            source=SRC+", Table S1", quality_flags="; ".join(flags)))
ug = pd.DataFrame(rows)
ug["log_join_ok"] = ug.o2_psi_log_pct.notna()

# ---- Table S2 (normal gravity, Earth): (d, XO2, Vg, Vf_x1e3 or None, pm%) ; None = flame not sustained
S2 = [
 (1.27,20.9,25,7.81,0.2),(1.27,20.9,2,9.07,2.5),(1.27,20.0,25,5.08,0.8),(1.27,20.0,2,6.41,0.2),
 (1.27,19.0,25,2.60,2.9),(1.27,19.0,2,3.99,5.1),(1.27,18.5,25,1.35,8.0),(1.27,18.5,2,2.56,1.5),
 (1.27,18.3,25,None,None),(1.27,18.1,2,None,None),
 (0.95,20.9,25,9.06,4.3),(0.95,20.9,2,10.65,0.3),(0.95,20.0,25,6.29,0.6),(0.95,20.0,2,8.45,0.4),
 (0.95,19.0,25,3.50,1.0),(0.95,19.0,2,5.01,2.5),(0.95,18.8,2,2.97,2.0),(0.95,18.5,25,None,None),
 (0.95,18.5,2,3.33,0.6),(0.95,18.1,2,None,None),
 (0.64,20.9,25,11.17,1.3),(0.64,20.9,2,13.63,0.8),(0.64,20.0,25,8.16,0.6),(0.64,20.0,2,9.90,1.2),
 (0.64,19.0,25,5.77,2.2),(0.64,19.0,2,6.96,1.1),(0.64,18.5,25,3.20,3.0),(0.64,18.5,2,5.90,0.5),
 (0.64,18.2,25,None,None),(0.64,18.2,2,4.69,1.0),(0.64,18.0,2,3.13,2.3),(0.64,17.8,2,None,None),(0.64,17.5,2,None,None),
 (0.32,20.9,25,18.40,1.7),(0.32,20.9,2,23.57,2.2),(0.32,20.0,25,14.50,0.8),(0.32,20.0,2,19.00,1.3),
 (0.32,19.0,25,10.00,1.2),(0.32,19.0,2,14.01,0.8),(0.32,18.5,25,7.50,0.8),(0.32,18.5,2,11.02,0.3),
 (0.32,18.0,25,4.35,0.8),(0.32,18.0,2,8.00,1.1),(0.32,17.7,25,None,None),(0.32,17.5,2,3.88,0.5),(0.32,17.0,2,None,None),
]
amb = {(0.64,18.2,2),(0.64,18.0,2),(0.64,18.2,25),(0.32,18.0,25),(0.32,18.5,2)}
g1 = pd.DataFrame([dict(
    record_id=f"BASS2-FS-1G-{i:03d}", gravity="normal (1g)", platform="UC Berkeley ground duct",
    material="PMMA rod (cast, black)", diameter_cm=d, diameter_mm=round(d*10,1), inv_diameter_per_cm=round(1/d,3),
    o2_pct=x, opposed_flow_cm_s=v, flame_sustained=(vf is not None),
    vf_x1e3_cm_s_raw=vf, flame_spread_mm_s=(round(vf*1e-3*10,4) if vf is not None else np.nan),
    repeat_spread_pct=pm, n_repeats=">=3",
    value_type="observed (published, mean of >=3 repeats)", source=SRC+", Table S2",
    quality_flags=("row position ambiguous in PDF text extraction; confirm against Table S2" if (d,x,v) in amb else ""))
    for i,(d,x,v,vf,pm) in enumerate(S2,1)])

ug.to_csv("BASS-II_flame_spread_microgravity_v1.0.csv", index=False)
g1.to_csv("BASS-II_flame_spread_1g_reference_v1.0.csv", index=False)

# ---- sanity checks
print("μg rows:", len(ug), " tests:", ug.test_id.nunique(), " joined to PSI log:", int(ug.log_join_ok.sum()))
print(ug.groupby("diameter_cm").size().to_string())
print("O2 mismatches:", ug[ug.quality_flags.str.contains("O2 differs")].test_id.unique())
print("spread mm/s range:", ug.flame_spread_mm_s.min(), "-", ug.flame_spread_mm_s.max())
import numpy.linalg as la
b = ug[ug.pmma_color=="black"]
X = np.c_[np.ones(len(b)), b.o2_pct, b.opposed_flow_cm_s, b.diameter_cm]
coef = la.lstsq(X, b.flame_spread_mm_s, rcond=None)[0]
print("linear check (const, O2, Vg, d):", np.round(coef,4))
print("1g rows:", len(g1), " sustained:", int(g1.flame_sustained.sum()))
