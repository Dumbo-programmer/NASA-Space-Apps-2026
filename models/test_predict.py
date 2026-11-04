import json, time
import numpy as np
from ignis_models import predict, load
def show(name, **kw):
    t = time.time(); r = predict(name, **kw); dt = time.time() - t
    keep = {k: r[k] for k in ("prediction", "unit", "interval_90", "probability", "predicted_class", "in_domain", "warnings", "contributions") if k in r}
    print(f"\n[{name}] {kw}  ({dt:.1f}s)\n  {json.dumps(keep)}")
    return r
show("bass2_flame_spread", o2_pct=18.2, opposed_flow_cm_s=1.67, diameter_cm=0.64)
show("flex_extinction", fuel="Methanol", pressure_kpa=101.3, o2_pct=21, co2_pct=0, he_pct=0, d0_mm=2.5)
show("flex_extinction", fuel="Methanol", pressure_kpa=101.3, o2_pct=14, co2_pct=0, he_pct=0, d0_mm=3.5)
show("flex_burning_rate", fuel="Heptane", pressure_kpa=101.3, o2_pct=21, co2_pct=0, he_pct=0, d0_mm=3.0)
show("spice_smoke_point", fuel="Ethylene", burner_diameter_mm=1.6002, coflow_air_velocity_cm_s=40)
show("same_particle_size", material="Silicone", sample_temperature_c=380, air_velocity_cm_s=8.1, aging_time_s=45, campaign="SAME-R")
show("flex_extinction", fuel="Methanol", pressure_kpa=60, o2_pct=30, co2_pct=0, he_pct=0, d0_mm=6)   # out of domain

print("\nPHYSICS CHECKS (explain=False)")
p = [predict("flex_extinction", explain=False, fuel="Methanol", pressure_kpa=101.3, o2_pct=o, co2_pct=0, he_pct=0, d0_mm=3.0)["probability"] for o in (13, 15, 18, 21, 25)]
print("FLEX methanol 3 mm: P(extinction) at O2 13/15/18/21/25% ->", p)
k = [predict("flex_burning_rate", explain=False, fuel="Methanol", pressure_kpa=101.3, o2_pct=o, co2_pct=0, he_pct=0, d0_mm=3.0)["prediction"] for o in (13, 18, 21, 25)]
print("FLEX methanol K at O2 13/18/21/25% ->", k)
sp = {f: predict("spice_smoke_point", explain=False, fuel=f, burner_diameter_mm=1.6002, coflow_air_velocity_cm_s=30)["prediction"] for f in ("Ethylene", "Propane", "Propylene/N2 50%", "Propylene")}
print("SPICE smoke point at 1.6 mm, 30 cm/s ->", sp)
c = [predict("spice_smoke_point", explain=False, fuel="Propylene", burner_diameter_mm=1.6002, coflow_air_velocity_cm_s=u)["prediction"] for u in (10, 30, 50)]
print("SPICE propylene vs coflow 10/30/50 ->", c)
a = [predict("same_particle_size", explain=False, material="Kapton", sample_temperature_c=420, air_velocity_cm_s=v, aging_time_s=t, campaign="SAME-R")["prediction"] for v, t in ((8.1, 35), (8.1, 560), (0, 35))]
print("SAME Kapton CMD fresh/aged/no-flow ->", a)
