"""Week 10 - bagasse cogeneration at a 3500 TCD sugar mill."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A **3500 TCD** sugar mill. Bagasse fires a boiler at **87 bar / 515 °C**; a
**backpressure turbine** exhausts to the **3.5 bar** process header. How much
surplus power can the mill export, and what happens off-season?

Deliverable **D-10**: steam balance and export power at **100% and 60% crush
rate**, with the turbine off-design handled by the **Stodola ellipse law**.

### The thing that makes cogeneration different

In a condensing plant you choose the steam flow to suit the power demand. In a
backpressure cogeneration plant the **process decides the steam flow**, and the
power is whatever falls out. Power is a by-product. Get that backwards and every
number afterwards is wrong.
"""))
C.append(md("## 1. The mill, on a mass basis"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()

TCD          = 3500.0          # tonnes cane per day
HOURS        = 24.0
bagasse_pct  = 30.0            # % on cane
steam_pct    = 50.0            # % on cane, boiler output
process_pct  = 40.0            # % on cane, demand at 3.5 bar
mill_kWh_t   = 25.0            # kWh per tonne cane, internal electrical demand

p_hp, T_hp = 87e5, am.K(515)   # boiler outlet
p_bp       = 3.5e5             # process header
eta_s_t    = 0.80              # turbine isentropic efficiency
eta_gen    = 0.96

def mill(crush=1.0):
    cane   = TCD*crush/HOURS                    # t/h
    bag    = cane*bagasse_pct/100
    steam  = cane*steam_pct/100                 # t/h
    proc   = cane*process_pct/100
    return {"crush, %": crush*100, "cane, t/h": cane, "bagasse, t/h": bag,
            "steam raised, t/h": steam, "process demand, t/h": proc,
            "internal power, kW": cane*mill_kWh_t}

for c in (1.0, 0.6):
    m = mill(c)
    print("  " + "  ".join(f"{k} {v:.2f}" for k, v in m.items()))
'''))
C.append(md("## 2. The turbine at design point"))
C.append(code('''st_in  = am.State("Water", P=p_hp, T=T_hp)
h_in, s_in = st_in.h, st_in.s
h_out_s = PropsSI("H", "P", p_bp, "S", s_in, "Water")
h_out   = h_in - eta_s_t*(h_in - h_out_s)
st_out  = am.State("Water", P=p_bp, H=h_out)

print(f"  inlet   {p_hp/1e5:.0f} bar, {am.C(T_hp):.0f} C, h = {h_in/1e3:.1f} kJ/kg")
print(f"  ideal exhaust  h_s = {h_out_s/1e3:.1f} kJ/kg")
print(f"  real  exhaust  h   = {h_out/1e3:.1f} kJ/kg, {st_out.T_C:.1f} C, x = {st_out.x:.4f}")
print(f"  specific work  {(h_in-h_out)/1e3:.2f} kJ/kg")
if 0 <= st_out.x <= 1:
    print(f"  NOTE exhaust is wet at x = {st_out.x:.3f}. Below about 0.88 the last")
    print("  stage erodes. Check this before you accept a backpressure.")
else:
    print("  exhaust is superheated, so no erosion concern.")
'''))
C.append(md("""## 3. Steam balance and export power

The turbine passes the steam the boiler raises. Process takes what it needs. Any
**excess exhaust has nowhere to go** — it is vented, and that is pure loss.
"""))
C.append(code('''def balance(crush=1.0, steam_pct=steam_pct, process_pct=process_pct):
    m = mill(crush)
    m["steam raised, t/h"] = m["cane, t/h"]*steam_pct/100
    m["process demand, t/h"] = m["cane, t/h"]*process_pct/100
    m_s   = m["steam raised, t/h"]*1000/3600            # kg/s through the turbine
    P_gen = m_s*(h_in - h_out)*eta_gen                  # W
    vent  = max(m["steam raised, t/h"] - m["process demand, t/h"], 0.0)
    short = max(m["process demand, t/h"] - m["steam raised, t/h"], 0.0)
    export = P_gen - m["internal power, kW"]*1e3
    return {**m, "turbine flow, kg/s": m_s,
            "power generated, kW": P_gen/1e3,
            "export, kW": export/1e3,
            "exhaust vented, t/h": vent, "process shortfall, t/h": short,
            "heat-to-power ratio": (m["process demand, t/h"]*1000/3600
                                    *(h_out - PropsSI("H","P",p_bp,"Q",0,"Water")))/max(P_gen,1)}

print(f"{'':22s}{'100% crush':>14}{'60% crush':>14}")
b100, b60 = balance(1.0), balance(0.6)
for k in ("cane, t/h","steam raised, t/h","process demand, t/h","turbine flow, kg/s",
          "power generated, kW","internal power, kW","export, kW","exhaust vented, t/h"):
    print(f"{k:22s}{b100[k]:14.2f}{b60[k]:14.2f}")
print(f"\\n  export falls {100*(1-b60['export, kW']/b100['export, kW']):.1f}% "
      f"for a 40% cut in crush - roughly proportional, because everything scales"
      "\\n  with cane and the turbine still sees its design pressure ratio.")
'''))
C.append(md("""## 4. Off-design: the Stodola ellipse

At part load the turbine passes less steam, so its **inlet pressure falls**.
Stodola's law says the swallowing capacity follows an ellipse:

`ṁ / ṁ_d = √[ (p_in² − p_out²) / (p_in,d² − p_out,d²) ] · √(T_d / T_in)`

Solve it for the inlet pressure the machine will actually sit at.
"""))
C.append(code('''m_design = b100["turbine flow, kg/s"]

def stodola_inlet_pressure(m_dot, T_in=T_hp, p_out=p_bp,
                           m_d=m_design, p_in_d=p_hp, T_d=T_hp):
    """Invert the ellipse for p_in at a given flow."""
    def f(p_in):
        ratio = np.sqrt(max(p_in**2 - p_out**2, 1e-9)
                        /(p_in_d**2 - p_out**2))*np.sqrt(T_d/T_in)
        return ratio*m_d - m_dot
    return brentq(f, p_out*1.001, p_in_d*1.5)

def turbine_offdesign(crush):
    b   = balance(crush)
    m_s = b["turbine flow, kg/s"]
    p_in = stodola_inlet_pressure(m_s)
    st_i = am.State("Water", P=p_in, T=T_hp)
    h_o_s = PropsSI("H","P",p_bp,"S",st_i.s,"Water")
    h_o   = st_i.h - eta_s_t*(st_i.h - h_o_s)
    P     = m_s*(st_i.h - h_o)*eta_gen
    return {"crush, %": crush*100, "flow, kg/s": m_s, "p_in, bar": p_in/1e5,
            "specific work, kJ/kg": (st_i.h - h_o)/1e3,
            "power, kW": P/1e3,
            "export, kW": (P - b["internal power, kW"]*1e3)/1e3,
            "x_exhaust": am.State("Water", P=p_bp, H=h_o).x}

print(f"{'crush %':>9}{'flow kg/s':>11}{'p_in bar':>10}{'w kJ/kg':>10}"
      f"{'power kW':>11}{'export kW':>11}")
rows = []
for c in np.arange(0.40, 1.05, 0.05):
    r_ = turbine_offdesign(float(c)); rows.append(r_)
    print(f"{r_['crush, %']:9.0f}{r_['flow, kg/s']:11.3f}{r_['p_in, bar']:10.2f}"
          f"{r_['specific work, kJ/kg']:10.2f}{r_['power, kW']:11.1f}{r_['export, kW']:11.1f}")
'''))
C.append(md("""**Read that middle column.** The boiler cannot hold 87 bar at part
load: the turbine simply will not swallow the steam at that pressure. Inlet
pressure falls, the pressure ratio falls with it, and the **specific work drops**.
So power falls faster than flow does. That non-linearity is the whole reason
off-design analysis exists.
"""))
C.append(code('''fig, (a1,a2) = plt.subplots(1,2, figsize=(11.8,4.2))
cr = [r_["crush, %"] for r_ in rows]
a1.plot(cr, [r_["p_in, bar"] for r_ in rows], "o-", lw=2.4, color=am.NAVY)
a1.set_xlabel("crush rate  (%)"); a1.set_ylabel("turbine inlet pressure  (bar)")
a1.set_title("Stodola: the machine sets its own inlet pressure")
a2.plot(cr, [r_["power, kW"] for r_ in rows], "o-", lw=2.4, color=am.ORANGE, label="generated")
a2.plot(cr, [r_["export, kW"] for r_ in rows], "o-", lw=2.4, color=am.BLUE, label="exported")
a2.axhline(0, color=am.MUTED, lw=1)
a2.set_xlabel("crush rate  (%)"); a2.set_ylabel("power  (kW)")
a2.set_title("Both fall with crush; export falls slightly faster"); a2.legend(fontsize=9)
plt.tight_layout(); plt.show()

naive = balance(0.6)["power generated, kW"]
stod  = turbine_offdesign(0.6)["power, kW"]
print(f"\\n  At 60% crush:")
print(f"    scaling the design point linearly gives {naive:8.1f} kW")
print(f"    Stodola, with p_in falling to 52 bar,   {stod:8.1f} kW")
print(f"    the naive method overstates power by    {100*(naive-stod)/stod:8.1f}%")
print("    That is the entire reason off-design analysis exists.\\n")

zero = [r_ for r_ in rows if r_["export, kW"] <= 0]
if zero:
    print(f"  Export reaches zero at about {max(z['crush, %'] for z in zero):.0f}% crush.")
    print("  Below that the mill imports. The internal load is nearly fixed while")
    print("  generation falls with cane, so the crossover comes sooner than expected.")
else:
    print("  The mill exports across the whole range studied.")
'''))
C.append(md("## 5. The deliverable"))
C.append(code('''bal_rows = [balance(float(c)) for c in np.arange(0.4, 1.05, 0.1)]
path = am.to_excel("AM5061_D10_Cogeneration.xlsx",
    {"Steam balance": bal_rows, "Turbine off-design (Stodola)": rows},
    title="AM5061 D-10 . 3500 TCD bagasse cogeneration",
    summary=[("Cane crush", TCD, "TCD"),
             ("Boiler steam", f"{p_hp/1e5:.0f} bar / {am.C(T_hp):.0f} C", ""),
             ("Process header", p_bp/1e5, "bar"),
             ("Turbine isentropic efficiency", eta_s_t, "-"),
             ("Specific work at design", (h_in-h_out)/1e3, "kJ/kg"),
             ("Power generated, 100% crush", b100["power generated, kW"], "kW"),
             ("Export, 100% crush", b100["export, kW"], "kW"),
             ("Export, 60% crush", turbine_offdesign(0.6)["export, kW"], "kW"),
             ("Exhaust quality at design", st_out.x, "-")],
    sources=[("Water/steam", "CoolProp, IAPWS-95"),
             ("Off-design turbine", "Stodola ellipse law"),
             ("Mill ratios", "bagasse 30% on cane, steam 50%, process 40%, "
                             "25 kWh/t internal - TYPICAL VALUES, confirm for the site"),
             ("Case data", "AM5061 brief D-10")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The steam balance at 100% and 60% crush.
2. Export power at both, **using Stodola for the off-design point** — not by
   scaling the design-point number linearly.
3. The crush rate at which export reaches zero, and what the mill should do
   about it.
4. The exhaust quality, and whether it is acceptable.
5. The workbook.

**State your assumptions.** The mill ratios here (30% bagasse on cane, 50%
steam, 40% process, 25 kWh/t) are typical Indian values, not measurements. Every
number downstream scales with them, so a report that does not declare them is
not checkable.
"""))
build("Week10_Cogeneration.ipynb", "Week 10 · Bagasse cogeneration", C)
print("Week10 built")
