"""Week 12 - solar-driven LiBr-water absorption chiller for a 500 t cold store."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

Grid-independent cooling for **500 tonnes of potato storage in Agra**. Evacuated
tube collectors drive a **single-effect LiBr–water absorption chiller**. Size the
collector field.

Deliverable **D-12**: collector area and storage volume for an **80% solar
fraction**.

### What is different about an absorption chiller

There is no compressor. The pressure lift is done by a **liquid pump** on a
solution loop, which costs almost nothing, and the "compression" is done by
**heat** in the generator. So the machine is driven by a temperature, not by
electricity, and its COP is around **0.7 — not 3**. That is not a bad number;
it is a different quantity, because the input is low-grade heat.

> **Property note.** CoolProp supplies LiBr **solution** properties (density,
> specific heat, enthalpy). It does **not** supply the vapour–liquid
> equilibrium, so the solution concentrations here are **design inputs read off
> the Dühring chart**, which is exactly how a first-pass design is done. Reading
> them off the chart is your job, and the chart is on the Week 12 slides.
"""))
C.append(md("## 1. The cold store load"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()

MASS_T      = 500.0        # tonnes of potato
T_store     = am.K(4)      # storage temperature
respiration = 25.0         # W per tonne, potato at 4 C (typical)
transmission= 12.0e3       # W, envelope gain
infiltration= 4.0e3        # W
Q_field     = 18.0e3       # W, field heat pull-down averaged over the season

Q_cool = MASS_T*respiration + transmission + infiltration
print(f"  respiration   {MASS_T*respiration/1e3:7.2f} kW")
print(f"  transmission  {transmission/1e3:7.2f} kW")
print(f"  infiltration  {infiltration/1e3:7.2f} kW")
print(f"  steady load   {Q_cool/1e3:7.2f} kW  = {Q_cool/3516.85:.1f} TR")
'''))
C.append(md("""## 2. The single-effect cycle

Four temperatures fix the machine: evaporator, condenser, absorber and
generator. The two **concentrations** come off the Dühring chart at those
temperatures — enter them here.
"""))
C.append(code('''T_evap  = am.K(5)       # chilled water leaves ~7 C for a 4 C store
T_cond  = am.K(40)      # cooling tower water + approach
T_abs   = am.K(38)
T_gen   = am.K(88)      # driven by evacuated tubes

# ---- FROM THE DUHRING CHART -----------------------------------------
# Read these at (T_abs, T_evap) and (T_gen, T_cond). Typical single-effect
# values for the temperatures above; replace with your own chart readings.
X_weak   = 0.56        # kg LiBr / kg solution, leaving the ABSORBER
X_strong = 0.62        # leaving the GENERATOR
# ---------------------------------------------------------------------

if X_strong <= X_weak:
    raise ValueError("the strong solution must be more concentrated than the weak")
f = X_strong/(X_strong - X_weak)      # circulation ratio, pure LiBr mass balance
print(f"  weak solution   X = {X_weak:.3f}   (from the absorber)")
print(f"  strong solution X = {X_strong:.3f}   (from the generator)")
print(f"  circulation ratio f = X_s/(X_s - X_w) = {f:.3f}")
print(f"\\n  {f:.1f} kg of solution must be pumped for every 1 kg of refrigerant")
print("  vapour boiled off. Narrow the concentration gap and f explodes, which")
print("  is why the crystallisation limit matters so much.")
'''))
C.append(md("""### The crystallisation limit

Push the strong solution too concentrated, or cool it too far, and LiBr
**crystallises** and blocks the machine. That is the hard boundary on the right
of the Dühring chart, and it is why absorption chillers are fussy about cooling
water temperature.
"""))
C.append(code('''def solution_h(T, X):
    """Enthalpy of aqueous LiBr from CoolProp's incompressible solution data."""
    return PropsSI("H", "T", T, "P", 1e5, f"INCOMP::LiBr[{X:.4f}]")

def chiller(Q_cool, T_evap=T_evap, T_cond=T_cond, T_gen=T_gen, T_abs=T_abs,
            X_w=X_weak, X_s=X_strong, eta_shx=0.65):
    fcirc = X_s/(X_s - X_w)
    # refrigerant (pure water) side
    h_v_gen  = PropsSI("H","T",T_gen, "Q",1,"Water")      # vapour off the generator
    h_l_cond = PropsSI("H","T",T_cond,"Q",0,"Water")      # condensate
    h_v_evap = PropsSI("H","T",T_evap,"Q",1,"Water")
    m_ref    = Q_cool/(h_v_evap - h_l_cond)               # isenthalpic throttle
    Q_cond   = m_ref*(h_v_gen - h_l_cond)

    # solution side
    m_weak, m_strong = fcirc*m_ref, (fcirc - 1)*m_ref
    h_w_abs = solution_h(T_abs, X_w)
    h_s_gen = solution_h(T_gen, X_s)
    # solution heat exchanger preheats the weak stream using the hot strong one
    dT_max  = T_gen - T_abs
    h_w_in  = h_w_abs + eta_shx*dT_max*PropsSI("C","T",T_abs,"P",1e5,f"INCOMP::LiBr[{X_w:.4f}]")
    h_s_out = h_s_gen - (m_weak/max(m_strong,1e-9))*(h_w_in - h_w_abs)

    Q_gen = m_ref*h_v_gen + m_strong*h_s_gen - m_weak*h_w_in
    Q_abs = m_ref*h_v_evap + m_strong*h_s_out - m_weak*h_w_abs
    return {"Q_cool, kW": Q_cool/1e3, "Q_gen, kW": Q_gen/1e3,
            "Q_cond, kW": Q_cond/1e3, "Q_abs, kW": Q_abs/1e3,
            "COP_thermal": Q_cool/Q_gen, "circulation ratio": fcirc,
            "m_refrigerant, kg/s": m_ref, "m_weak, kg/s": m_weak,
            "energy balance, kW": (Q_cool + Q_gen - Q_cond - Q_abs)/1e3}

ch = chiller(Q_cool)
for k, v in ch.items(): print(f"  {k:22s} {v:10.4f}")
print("\\n  The energy balance should close: Q_evap + Q_gen = Q_cond + Q_abs.")
'''))
C.append(md("""## 3. The collector field

Hottel–Whillier–Bliss: a collector's efficiency falls linearly (near enough)
with the ratio of temperature lift to irradiance. Evacuated tubes have a much
smaller loss coefficient than flat plates, which is why they can reach the
88 °C the generator needs.
"""))
C.append(code('''eta_0, a1_, a2_ = 0.72, 1.60, 0.0080     # evacuated tube, typical certified values
T_amb_day = am.K(32)                     # Agra, mean daytime in the storage season

def collector_eff(G, T_m, T_amb=T_amb_day):
    """Hottel-Whillier-Bliss, second order. G in W/m2."""
    if G <= 0: return 0.0
    dT = T_m - T_amb
    return max(eta_0 - a1_*dT/G - a2_*dT**2/G, 0.0)

T_mean_coll = T_gen + 7.0        # collector mean fluid temperature
print(f"{'irradiance G':>14}{'efficiency':>12}{'useful W/m2':>14}")
for G in (300, 500, 700, 900):
    e = collector_eff(G, T_mean_coll)
    print(f"{G:14.0f}{e:12.4f}{e*G:14.1f}")
print(f"\\n  A flat plate (eta_0 0.78, a1 4.0) at G = 700 would manage "
      f"{max(0.78 - 4.0*(T_mean_coll-T_amb_day)/700, 0):.3f}")
print("  which is why this machine needs evacuated tubes, not flat plates.")
'''))
C.append(md("## 4. Area and storage for an 80% solar fraction"))
C.append(code('''H_day   = 5.5e3*3600/1e3       # Wh/m2/day -> J/m2/day at Agra (5.5 kWh/m2/day)
hours_sun = 8.0
G_mean  = 5.5e3/hours_sun      # W/m2 averaged over the sunlit period
SF      = 0.80                 # target solar fraction

Q_gen_W  = ch["Q_gen, kW"]*1e3
E_gen_day = Q_gen_W*24*3600                       # J/day the generator needs
E_solar_needed = SF*E_gen_day

eta_coll = collector_eff(G_mean, T_mean_coll)
E_per_m2_day = eta_coll*G_mean*hours_sun*3600     # J/m2/day
A_coll = E_solar_needed/E_per_m2_day

# storage carries the machine through the night
E_night = Q_gen_W*(24 - hours_sun)*3600
dT_store = 25.0                                   # usable swing in the tank
V_store = E_night/(1000.0*4180.0*dT_store)

print(f"  generator duty          {Q_gen_W/1e3:8.2f} kW  (continuous)")
print(f"  daily generator energy  {E_gen_day/3.6e9:8.2f} MWh/day")
print(f"  collector efficiency    {eta_coll:8.4f} at G = {G_mean:.0f} W/m2")
print(f"  useful yield            {E_per_m2_day/3.6e6:8.3f} kWh/m2/day")
print(f"\\n  collector area for {SF*100:.0f}% solar fraction: {A_coll:8.1f} m2")
print(f"  storage volume for the night:            {V_store:8.2f} m3")
print(f"  (at a {dT_store:.0f} K usable swing)")
'''))
C.append(code('''rows = []
for sf in np.arange(0.3, 1.01, 0.05):
    A = sf*E_gen_day/E_per_m2_day
    rows.append({"solar fraction": float(sf), "collector area, m2": A,
                 "area per TR, m2/TR": A/(Q_cool/3516.85),
                 "storage, m3": V_store,
                 "backup heat needed, kW": (1-sf)*Q_gen_W/1e3})
fig, ax = plt.subplots()
ax.plot([r_["solar fraction"]*100 for r_ in rows],
        [r_["collector area, m2"] for r_ in rows], "o-", lw=2.4, color=am.ORANGE)
ax.axvline(80, color=am.MUTED, ls="--")
ax.plot(80, A_coll, "o", ms=11, color=am.NAVY, zorder=5)
ax.annotate(f"  {A_coll:.0f} m²", (80, A_coll), color=am.NAVY, fontsize=11)
ax.set_xlabel("solar fraction  (%)"); ax.set_ylabel("collector area  (m²)")
ax.set_title("Area is linear in solar fraction; the last 20% costs as much as the first")
plt.tight_layout(); plt.show()
print("  Area scales linearly with solar fraction, but COST does not: the last")
print("  fraction runs only on the worst days, so its capacity factor is awful.")
print("  100% solar is almost never the economic answer. A backup burner is.")
'''))
C.append(md("""## 5. What this model can and cannot tell you

**It can** show you the effect of the concentration gap, because the circulation
ratio follows from a pure mass balance.

**It cannot** show you the effect of condenser temperature. Raising the
condenser temperature forces a higher generator temperature and *narrows* the
usable concentration gap — but that link runs through the **Dühring
equilibrium**, which is exactly the piece CoolProp does not supply and which you
entered by hand. Hold the concentrations fixed, as here, and the model reports
almost no penalty. That is an artefact of the model, not physics.

Knowing where your model stops being trustworthy is worth more than another
decimal place.
"""))
C.append(code('''# The lever the model DOES capture: the concentration gap.
print(f"{'X_strong':>10}{'gap':>8}{'f':>9}{'COP_th':>9}{'Q_gen kW':>11}{'area m2':>10}")
sens = []
for Xs in (0.58, 0.59, 0.60, 0.62, 0.64, 0.66):
    c = chiller(Q_cool, X_s=Xs)
    A = SF*c["Q_gen, kW"]*1e3*24*3600/E_per_m2_day
    sens.append({"X_strong": Xs, "gap": Xs - X_weak, **c, "collector area, m2": A})
    print(f"{Xs:10.3f}{Xs-X_weak:8.3f}{c['circulation ratio']:9.2f}"
          f"{c['COP_thermal']:9.4f}{c['Q_gen, kW']:11.2f}{A:10.1f}")
print("\\n  Narrow the gap and the circulation ratio explodes: at a 0.02 gap you")
print("  pump 29 kg of solution per kg of vapour. That is pump power, pipe size")
print("  and solution heat exchanger duty, all rising together.")
print("\\n  Now the honest part: run the same sweep on T_cond and you will see")
print("  almost NO effect, because this model holds the concentrations fixed.")
print("  The real condenser penalty travels through the Duhring equilibrium.")
for Tc in (34, 38, 42):
    c = chiller(Q_cool, T_cond=am.K(Tc), T_abs=am.K(Tc-2))
    print(f"    T_cond {Tc} C -> COP_th {c['COP_thermal']:.4f}   <- barely moves. "
          "That is the model's limit, not the machine's.")
'''))
C.append(md("## 6. The workbook"))
C.append(code('''path = am.to_excel("AM5061_D12_AbsorptionChiller.xlsx",
    {"Solar fraction study": rows, "Condenser sensitivity": sens},
    title="AM5061 D-12 . Solar LiBr-water absorption chiller, Agra",
    summary=[("Store capacity", MASS_T, "t"), ("Cooling load", Q_cool/1e3, "kW"),
             ("Cooling load", Q_cool/3516.85, "TR"),
             ("Evaporator / condenser", f"{am.C(T_evap):.0f} / {am.C(T_cond):.0f}", "C"),
             ("Generator / absorber", f"{am.C(T_gen):.0f} / {am.C(T_abs):.0f}", "C"),
             ("Weak / strong concentration", f"{X_weak} / {X_strong}", "kg/kg"),
             ("Circulation ratio", ch["circulation ratio"], "-"),
             ("COP thermal", ch["COP_thermal"], "-"),
             ("Generator duty", ch["Q_gen, kW"], "kW"),
             ("Collector area at 80% SF", A_coll, "m2"),
             ("Storage volume", V_store, "m3")],
    sources=[("Water properties", "CoolProp, IAPWS-95"),
             ("LiBr solution enthalpy", "CoolProp INCOMP::LiBr"),
             ("Concentrations", "READ FROM THE DUHRING CHART - design inputs, not computed"),
             ("Collector", "Hottel-Whillier-Bliss, evacuated tube eta0 0.72, a1 1.60, a2 0.0080"),
             ("Agra irradiance", "5.5 kWh/m2/day, 8 sunlit hours - TYPICAL, use TMY for a real design"),
             ("Potato respiration", "25 W/t at 4 C - typical")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The cycle: circulation ratio, COP_thermal, and all four duties with the
   energy balance closing.
2. Collector area and storage volume for 80% solar fraction.
3. The condenser-temperature sensitivity, and what it implies for the cooling
   tower you would specify.
4. **The concentrations you read off the Dühring chart**, and the crystallisation
   margin at your strong-solution point.
5. The workbook.

**One paragraph:** COP_thermal is about 0.7 while a vapour-compression chiller
manages 3 or more. Explain to a non-engineer why anyone would build this
machine anyway.
"""))
build("Week12_AbsorptionChiller.ipynb", "Week 12 · Solar absorption chiller", C)
print("Week12 built")
