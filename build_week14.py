"""Week 14 - the plant-level audit: Sankey, exergy, Rs/kWh, kg CO2."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

Take an earlier case and answer the only two questions a plant manager asks:
**what does it cost, and where is the loss?**

Deliverable **D-14**: Sankey diagram, exergy destruction table, levelised cost
and carbon intensity for one case of your choice. The worked example here uses
**Week 10's bagasse cogeneration plant**; swap in your own.

### Why energy accounting is not enough

A first-law balance says energy is conserved, so it can never tell you where the
*opportunity* went. Exergy can. A boiler that is 88% efficient on energy is
typically **under 30% efficient on exergy**, and that gap is where the design
work actually is.
"""))
C.append(md("## 1. The plant, from Week 10"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
am.style_plots()

T0, p0 = am.K(30), 101325.0          # Chennai dead state. A DESIGN CHOICE.
print(f"  dead state: {am.C(T0):.0f} C, {p0/1e3:.3f} kPa")
print("  Every exergy number below is relative to this. Report it, always.\\n")

# plant streams, from the Week 10 balance at 100% crush
m_steam = 20.255                     # kg/s through the turbine
p_hp, T_hp = 87e5, am.K(515)
p_bp       = 3.5e5
LHV_bag    = 7.5e6                   # J/kg, bagasse at 50% moisture
m_bag      = 43.75*1000/3600         # kg/s

st_hp  = am.State("Water", P=p_hp, T=T_hp)
st_bp  = am.State("Water", P=p_bp, H=2801.2e3)
st_fw  = am.State("Water", P=p_hp, T=am.K(105))
Q_fuel = m_bag*LHV_bag
W_turb = m_steam*(st_hp.h - st_bp.h)*0.96
Q_proc = m_steam*(st_bp.h - PropsSI("H","P",p_bp,"Q",0,"Water"))

print(f"  fuel input     {Q_fuel/1e6:8.2f} MW")
print(f"  shaft/electric {W_turb/1e6:8.2f} MW")
print(f"  process heat   {Q_proc/1e6:8.2f} MW")
print(f"  first-law utilisation {(W_turb+Q_proc)/Q_fuel*100:.1f}%")
'''))
C.append(md("""## 2. Exergy — the second-law picture

Flow exergy is `(h − h₀) − T₀(s − s₀)`. For the fuel we use a chemical exergy
approximated as **1.15 × LHV** for a solid biomass, which is the usual
engineering shortcut.
"""))
C.append(code('''ex_hp = am.exergy(st_hp, T0, p0)
ex_bp = am.exergy(st_bp, T0, p0)
ex_fw = am.exergy(st_fw, T0, p0)
Ex_fuel = 1.15*Q_fuel                      # chemical exergy of bagasse

Ex_steam_hp = m_steam*ex_hp
Ex_steam_bp = m_steam*ex_bp
Ex_fw_in    = m_steam*ex_fw

# component by component
Ex_d_boiler  = Ex_fuel + Ex_fw_in - Ex_steam_hp
Ex_d_turbine = Ex_steam_hp - Ex_steam_bp - W_turb
Ex_d_process = Ex_steam_bp - m_steam*am.exergy(am.State("Water",P=p_bp,Q=0), T0, p0)

comp = [
    {"component": "Boiler (combustion + heat transfer)", "exergy in, MW": Ex_fuel/1e6,
     "exergy destroyed, MW": Ex_d_boiler/1e6},
    {"component": "Turbine + generator", "exergy in, MW": Ex_steam_hp/1e6,
     "exergy destroyed, MW": Ex_d_turbine/1e6},
    {"component": "Process heat delivery", "exergy in, MW": Ex_steam_bp/1e6,
     "exergy destroyed, MW": Ex_d_process/1e6},
]
Ex_out_useful = W_turb + (Ex_steam_bp - m_steam*am.exergy(am.State("Water",P=p_bp,Q=0),T0,p0))
for c in comp:
    c["% of fuel exergy"] = 100*c["exergy destroyed, MW"]*1e6/Ex_fuel

print(f"  fuel exergy            {Ex_fuel/1e6:8.2f} MW")
print(f"  exergy in HP steam     {Ex_steam_hp/1e6:8.2f} MW")
print(f"{'component':<40}{'destroyed MW':>14}{'% of fuel':>12}")
for c in comp:
    print(f"{c['component']:<40}{c['exergy destroyed, MW']:14.3f}{c['% of fuel exergy']:12.1f}")
eta_I  = (W_turb + Q_proc)/Q_fuel
eta_II = (W_turb + (Ex_steam_bp - m_steam*am.exergy(am.State("Water",P=p_bp,Q=0),T0,p0)))/Ex_fuel
print(f"\\n  first-law  efficiency  {eta_I*100:6.1f}%")
print(f"  second-law efficiency  {eta_II*100:6.1f}%")
print("\\n  The boiler dominates. It always does: burning a fuel at 1200 C to")
print("  raise steam at 515 C throws away most of the fuel's quality before")
print("  any equipment downstream gets a chance to be inefficient.")
'''))
C.append(md("## 3. The Sankey"))
C.append(code('''fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 4.6))

# --- energy Sankey, as a stacked bar (readable, and honest about proportions)
labels_E = ["shaft power", "process heat", "stack + losses"]
vals_E   = [W_turb/1e6, Q_proc/1e6, (Q_fuel - W_turb - Q_proc)/1e6]
left = 0
for lab, v, col in zip(labels_E, vals_E, [am.ORANGE, am.BLUE, am.MUTED]):
    a1.barh(0, v, left=left, color=col, edgecolor="white", label=f"{lab}  {v:.1f} MW")
    if v/sum(vals_E) > 0.06:
        a1.text(left + v/2, 0, f"{100*v/sum(vals_E):.0f}%", ha="center",
                va="center", color="white", fontweight="bold")
    left += v
a1.set_yticks([]); a1.set_xlabel("MW"); a1.set_title(f"ENERGY: {Q_fuel/1e6:.1f} MW of fuel in")
a1.legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5,-0.18), ncol=1)

# --- exergy Sankey
labels_X = ["shaft power", "useful process exergy",
            "destroyed in boiler", "destroyed in turbine", "destroyed elsewhere"]
X_proc_useful = Ex_steam_bp - m_steam*am.exergy(am.State("Water",P=p_bp,Q=0),T0,p0)
vals_X = [W_turb/1e6, X_proc_useful/1e6, Ex_d_boiler/1e6, Ex_d_turbine/1e6,
          max((Ex_fuel - W_turb - X_proc_useful - Ex_d_boiler - Ex_d_turbine)/1e6, 0)]
left = 0
for lab, v, col in zip(labels_X, vals_X,
                       [am.ORANGE, am.BLUE, "#B03A2E", "#D98880", am.MUTED]):
    a2.barh(0, v, left=left, color=col, edgecolor="white", label=f"{lab}  {v:.1f} MW")
    if v/sum(vals_X) > 0.06:
        a2.text(left + v/2, 0, f"{100*v/sum(vals_X):.0f}%", ha="center",
                va="center", color="white", fontweight="bold")
    left += v
a2.set_yticks([]); a2.set_xlabel("MW"); a2.set_title(f"EXERGY: {Ex_fuel/1e6:.1f} MW in")
a2.legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5,-0.18), ncol=1)
plt.tight_layout(); plt.show()
print("  Same plant, two accounts. The energy picture says 'mostly useful'.")
print("  The exergy picture says 'mostly destroyed, and here is where'.")
print("  Only the second one tells you what to redesign.")
'''))
C.append(md("""## 4. The 4R sequence, driven by the exergy map

**Reduce · Reuse · Recycle · Replace** — applied in that order, and targeted by
the exergy table rather than by intuition. The largest destruction term is where
you look first, but only if something can actually be done about it.
"""))
C.append(code('''actions = [
 {"target": "Boiler combustion irreversibility", "R": "Replace",
  "action": "Raise steam pressure/temperature, or gasify rather than burn",
  "exergy at stake, MW": Ex_d_boiler/1e6,
  "realistic recovery, %": 10,
  "note": "Largest term, hardest to touch. Combustion irreversibility is set by flame temperature."},
 {"target": "Vented exhaust steam", "R": "Reduce",
  "action": "Match steam raising to process demand; trim boiler output",
  "exergy at stake, MW": 14.58*1000/3600*ex_bp/1e6,
  "realistic recovery, %": 80,
  "note": "Cheapest win on the list. Pure waste, no thermodynamic obstacle."},
 {"target": "Turbine irreversibility", "R": "Replace",
  "action": "Higher-efficiency turbine on next overhaul",
  "exergy at stake, MW": Ex_d_turbine/1e6,
  "realistic recovery, %": 15,
  "note": "Capital-intensive, incremental."},
]
print(f"{'target':<36}{'R':<9}{'at stake MW':>13}{'recoverable MW':>16}")
for a in actions:
    rec = a["exergy at stake, MW"]*a["realistic recovery, %"]/100
    a["recoverable, MW"] = rec
    print(f"{a['target']:<36}{a['R']:<9}{a['exergy at stake, MW']:13.2f}{rec:16.3f}")
print("\\n  Note the ordering. The BIGGEST destruction term is not the best")
print("  opportunity - the vented steam is. Exergy tells you where the loss is;")
print("  engineering judgement tells you which losses you can actually get back.")
'''))
C.append(md("## 5. Techno-economics"))
C.append(code('''CAPEX_per_kW = 65000.0      # Rs/kW installed, Indian bagasse cogen, order of magnitude
LIFE, DISC   = 20, 0.10     # years, discount rate
OPEX_frac    = 0.04         # of capex per year
CUF          = 0.45         # capacity utilisation: a sugar mill runs seasonally
TARIFF       = 4.50         # Rs/kWh, export tariff
GRID_CO2     = 0.71         # kg CO2/kWh, Indian grid average

P_kW   = W_turb/1e3
capex  = P_kW*CAPEX_per_kW
crf    = DISC*(1+DISC)**LIFE/((1+DISC)**LIFE - 1)
annual_kWh = P_kW*8760*CUF
lcoe   = (capex*crf + capex*OPEX_frac)/annual_kWh

print(f"  installed capacity      {P_kW:10.0f} kW")
print(f"  capex                   {capex/1e7:10.2f} crore Rs")
print(f"  capital recovery factor {crf:10.4f}")
print(f"  annual generation       {annual_kWh/1e6:10.2f} GWh   (CUF {CUF:.0%})")
print(f"\\n  levelised cost          {lcoe:10.2f} Rs/kWh")
print(f"  export tariff           {TARIFF:10.2f} Rs/kWh")
print(f"  margin                  {TARIFF-lcoe:10.2f} Rs/kWh")
print(f"  simple payback          {capex/((TARIFF-lcoe)*annual_kWh):10.2f} years"
      if TARIFF > lcoe else "  NOT VIABLE at this tariff")
'''))
C.append(code('''fig, ax = plt.subplots()
cufs = np.linspace(0.20, 0.90, 60)
for cap in (50000, 65000, 80000):
    l = [(P_kW*cap*crf + P_kW*cap*OPEX_frac)/(P_kW*8760*c) for c in cufs]
    ax.plot(cufs*100, l, lw=2.2, label=f"{cap/1000:.0f}k Rs/kW installed")
ax.axhline(TARIFF, color="#B03A2E", ls="--", lw=1.8)
ax.text(22, TARIFF+0.15, f"export tariff {TARIFF:.2f} Rs/kWh", color="#B03A2E", fontsize=9)
ax.axvline(CUF*100, color=am.MUTED, ls=":")
ax.set_xlabel("capacity utilisation factor  (%)"); ax.set_ylabel("levelised cost  (Rs/kWh)")
ax.set_title("Seasonality, not efficiency, decides whether cogeneration pays")
ax.set_ylim(0, 12); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
print("  A sugar mill crushes for perhaps 160 days a year. That CUF, not the")
print("  turbine efficiency, is what usually kills or saves the business case.")
print("  This is why off-season operation on biomass is worth so much.")
'''))
C.append(md("## 6. Carbon"))
C.append(code('''co2_avoided = annual_kWh*GRID_CO2/1000        # tonnes/yr
print(f"  displaced grid electricity  {annual_kWh/1e6:8.2f} GWh/yr")
print(f"  grid emission factor        {GRID_CO2:8.2f} kg CO2/kWh")
print(f"  CO2 avoided                 {co2_avoided:8.0f} t/yr")
print(f"  carbon intensity of output  {0.0:8.2f} kg CO2/kWh  (bagasse counted as biogenic)")
print("\\n  MARGINAL vs AVERAGE. The 0.71 figure is the grid AVERAGE. What you")
print("  actually displace at 2 a.m. is the MARGINAL plant, usually coal, with")
print("  a higher factor. Using the average understates the benefit; using coal")
print("  overstates it. State which you used and why - this is where carbon")
print("  accounting arguments are won and lost.")
'''))
C.append(md("## 7. The audit workbook"))
C.append(code('''econ = [{"CUF, %": float(c*100),
         "LCOE, Rs/kWh": (capex*crf + capex*OPEX_frac)/(P_kW*8760*c),
         "annual GWh": P_kW*8760*c/1e6,
         "margin, Rs/kWh": TARIFF - (capex*crf + capex*OPEX_frac)/(P_kW*8760*c)}
        for c in np.arange(0.20, 0.91, 0.05)]

path = am.to_excel("AM5061_D14_PlantAudit.xlsx",
    {"Exergy destruction": comp, "4R actions": actions, "Economics vs CUF": econ},
    title="AM5061 D-14 . Plant audit of the bagasse cogeneration case",
    summary=[("Dead state", f"{am.C(T0):.0f} C / {p0/1e3:.1f} kPa", ""),
             ("Fuel energy input", Q_fuel/1e6, "MW"),
             ("Fuel exergy input", Ex_fuel/1e6, "MW"),
             ("Shaft power", W_turb/1e6, "MW"),
             ("Process heat", Q_proc/1e6, "MW"),
             ("First-law efficiency", eta_I*100, "%"),
             ("Second-law efficiency", eta_II*100, "%"),
             ("Largest exergy destruction", "boiler", ""),
             ("LCOE", lcoe, "Rs/kWh"), ("Export tariff", TARIFF, "Rs/kWh"),
             ("CO2 avoided", co2_avoided, "t/yr")],
    sources=[("Steam properties", "CoolProp, IAPWS-95"),
             ("Dead state", "Chennai ambient 30 C, 101.325 kPa - a DESIGN CHOICE"),
             ("Bagasse LHV", "7.5 MJ/kg at 50% moisture - TYPICAL, confirm for the mill"),
             ("Bagasse chemical exergy", "1.15 x LHV - standard approximation for solid biomass"),
             ("Capex", "65,000 Rs/kW installed - ORDER OF MAGNITUDE, get vendor quotes"),
             ("Grid emission factor", "0.71 kg CO2/kWh, Indian grid average - AVERAGE not marginal"),
             ("Plant data", "AM5061 D-10, Week 10")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. Both Sankeys — energy and exergy — for **your** chosen case, side by side.
2. The exergy destruction table, ranked, with the dead state stated.
3. Your 4R action list, ordered by **recoverable** exergy rather than by
   destroyed exergy, with the difference explained.
4. LCOE, the tariff comparison, and the CUF sensitivity.
5. Carbon intensity, stating whether you used the average or marginal factor.
6. The workbook.

**Every cost and emission figure in this notebook is an order-of-magnitude
placeholder.** They are labelled as such on the Sources sheet. A techno-economic
claim built on unsourced numbers is worth nothing; get quotes, cite the CEA
factor you use, and state the year.
"""))
build("Week14_PlantAudit.ipynb", "Week 14 · Plant-level audit", C)
print("Week14 built")
