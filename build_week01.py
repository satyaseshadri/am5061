"""Week 1 - the 28 kW dairy heat pump. Colab notebook."""
from nbbuild import md, code, build

C = []

C.append(md("""---
## The case

A dairy needs **28 kW of heating** to pasteurise milk. You are specifying a
vapour-compression heat pump on **R134a**, condensing at **70 °C** and
evaporating at **10 °C**.

Deliverable **D-1**: the four state points, the COP, the mass flow and the
compressor power. Then answer the design question at the bottom.

### What you are actually doing

There are no components here. This is **sixteen equations in four state
points**. The cycle diagram is a drawing that tells you which enthalpy is
which, nothing more. Real components with ports arrive in Week 7.
"""))

C.append(md("""## 1. The design specification

Everything the brief gives you, in one place. Change these and the whole
notebook re-runs.
"""))
C.append(code('''import am5061 as am
from CoolProp.CoolProp import PropsSI
import numpy as np, matplotlib.pyplot as plt
am.style_plots()

FLUID  = "R134a"
Q_H    = 28e3          # W      required heating duty
T_cond = am.K(70)      # K      condensing temperature
T_evap = am.K(10)      # K      evaporating temperature
eta_s  = 1.0           # -      isentropic efficiency (1.0 = ideal, for now)
dT_sub = 0.0           # K      condenser subcooling
dT_sup = 0.0           # K      evaporator superheat

print(f"critical point of {FLUID}: "
      f"{am.C(am.critical(FLUID)['T']):.2f} C, {am.critical(FLUID)['p']/1e5:.2f} bar")
print(f"condensing at {am.C(T_cond):.0f} C - comfortably subcritical, so the "
      "cycle has a two-phase condenser.")
'''))

C.append(md("""## 2. The two pressures

The evaporator and condenser each sit at the saturation pressure of their
temperature. This is the only place the fluid choice enters the *structure* of
the problem, and it is why a fluid with a sensible pressure ratio over your
temperature lift is the first thing you look for.
"""))
C.append(code('''p_evap = am.p_sat(FLUID, T_evap)
p_cond = am.p_sat(FLUID, T_cond)

print(f"p_evap = {p_evap/1e5:7.4f} bar   at {am.C(T_evap):.0f} C")
print(f"p_cond = {p_cond/1e5:7.4f} bar   at {am.C(T_cond):.0f} C")
print(f"pressure ratio = {p_cond/p_evap:.3f}")
'''))

C.append(md("""## 3. The four state points

| | where | how it is fixed |
|---|---|---|
| 1 | compressor suction | saturated vapour at `p_evap`, plus superheat |
| 2 | compressor discharge | at `p_cond`, from the isentropic state and `eta_s` |
| 3 | condenser outlet | saturated liquid at `p_cond`, less subcooling |
| 4 | evaporator inlet | isenthalpic expansion, so `h4 = h3` |

State 2 is the only one needing care. Compression is *isentropic* to the ideal
point 2s, then the real work is scaled by the isentropic efficiency.
"""))
C.append(code('''# --- 1: compressor suction -------------------------------------------
if dT_sup > 0:
    st1 = am.State(FLUID, P=p_evap, T=am.T_sat(FLUID, p_evap) + dT_sup)
else:
    st1 = am.sat_vapour(FLUID, p=p_evap)
h1, s1 = st1.h, st1.s

# --- 2s: isentropic discharge, then 2: real discharge -----------------
h2s = PropsSI("H", "P", p_cond, "S", s1, FLUID)
h2  = h1 + (h2s - h1) / eta_s
st2 = am.State(FLUID, P=p_cond, H=h2)

# --- 3: condenser outlet ----------------------------------------------
if dT_sub > 0:
    st3 = am.State(FLUID, P=p_cond, T=am.T_sat(FLUID, p_cond) - dT_sub)
else:
    st3 = am.sat_liquid(FLUID, p=p_cond)
h3 = st3.h

# --- 4: isenthalpic expansion -----------------------------------------
h4  = h3
st4 = am.State(FLUID, P=p_evap, H=h4)

print(f"{'pt':>3} {'p, bar':>9} {'T, C':>9} {'h, kJ/kg':>10} {'x, -':>8}  phase")
for n, st in ((1, st1), (2, st2), (3, st3), (4, st4)):
    x = st.x
    xs = f"{x:8.4f}" if 0 <= x <= 1 else "       -"
    # CoolProp calls a point ON the dome "twophase". True, but it reads oddly
    # for a saturated vapour, so name the two edges explicitly.
    ph = ("sat. liquid" if x == 0 else "sat. vapour" if x == 1 else st.phase)
    print(f"{n:>3} {st.p/1e5:9.4f} {st.T_C:9.3f} {st.h/1e3:10.3f} {xs}  {ph}")
'''))

C.append(md("""## 4. Performance

Specific quantities first, then scale up to the duty the dairy asked for.
"""))
C.append(code('''w_in = h2 - h1          # J/kg   compressor work
q_H  = h2 - h3          # J/kg   heat rejected in the condenser
q_L  = h1 - h4          # J/kg   refrigeration effect

COP_actual = q_H / w_in
COP_carnot = T_cond / (T_cond - T_evap)
eta_II     = COP_actual / COP_carnot

m_flow = Q_H / q_H
W_comp = m_flow * w_in
Q_L    = m_flow * q_L

print(f"  w_in        {w_in/1e3:10.3f} kJ/kg")
print(f"  q_H         {q_H/1e3:10.3f} kJ/kg")
print(f"  q_L         {q_L/1e3:10.3f} kJ/kg")
print(f"  COP_actual  {COP_actual:10.5f}")
print(f"  COP_carnot  {COP_carnot:10.5f}")
print(f"  eta_II      {eta_II:10.5f}")
print(f"  m_flow      {m_flow:10.5f} kg/s")
print(f"  W_comp      {W_comp:10.2f} W")
print(f"  Q_L         {Q_L:10.2f} W")
print()
print("  energy balance check:  Q_L + W_comp - Q_H =",
      f"{Q_L + W_comp - Q_H:.6e} W   (must be ~0)")
'''))

C.append(md("""> **Check your answer.** The ideal cycle gives **COP = 3.98559**.
> If you get something else, you changed a parameter. That is fine, but know
> which one.
"""))

C.append(md("""## 5. The cycle on p–h axes

The plot is not decoration. The condenser is the top horizontal run, the
evaporator the bottom one, and the *width* of the bottom run is your
refrigeration effect. Widen it and the mass flow drops.
"""))
C.append(code('''fig, ax = plt.subplots(figsize=(7.4, 5.0))

# saturation dome
Tc = am.critical(FLUID)["T"]
Ts = np.linspace(am.K(-30), Tc - 0.4, 300)
ax.plot([PropsSI("H","T",t,"Q",0,FLUID)/1e3 for t in Ts],
        [PropsSI("P","T",t,"Q",0,FLUID)/1e5 for t in Ts], color=am.MUTED, lw=1.3)
ax.plot([PropsSI("H","T",t,"Q",1,FLUID)/1e3 for t in Ts],
        [PropsSI("P","T",t,"Q",1,FLUID)/1e5 for t in Ts], color=am.MUTED, lw=1.3)

# the cycle, 1 -> 2 -> 3 -> 4 -> 1
hs = [h1, h2, h3, h4, h1]
ps = [p_evap, p_cond, p_cond, p_evap, p_evap]
ax.plot(np.array(hs)/1e3, np.array(ps)/1e5, "o-", color=am.ORANGE, lw=2.4, ms=7)
for n, (h, p) in enumerate(zip(hs[:4], ps[:4]), 1):
    ax.annotate(str(n), (h/1e3, p/1e5), textcoords="offset points",
                xytext=(9, 7), fontsize=12, color=am.NAVY, fontweight="bold")

ax.set_yscale("log")
ax.set_xlabel("specific enthalpy  h  (kJ/kg)")
ax.set_ylabel("pressure  p  (bar)")
ax.set_title(f"{FLUID} cycle:  {am.C(T_evap):.0f} °C to {am.C(T_cond):.0f} °C,"
             f"  COP = {COP_actual:.3f}")
ax.grid(alpha=.25, which="both")
plt.tight_layout(); plt.show()
'''))

C.append(md("""## 6. The design question

The brief asks you to re-run with **`eta_s = 0.72`** and **`dT_sub = 5`**, and
report what happens to the COP and to the required mass flow.

Then answer this: **which of the two does a compressor salesman care about,
and why?**
"""))
C.append(code('''def cycle(eta_s=1.0, dT_sub=0.0, dT_sup=0.0, T_cond=T_cond, T_evap=T_evap):
    """The whole of sections 2-4, as one function. Returns a dict."""
    pe, pc = am.p_sat(FLUID, T_evap), am.p_sat(FLUID, T_cond)
    s1_ = (am.State(FLUID, P=pe, T=am.T_sat(FLUID, pe) + dT_sup) if dT_sup > 0
           else am.sat_vapour(FLUID, p=pe))
    h1_, s1v = s1_.h, s1_.s
    h2s_ = PropsSI("H", "P", pc, "S", s1v, FLUID)
    h2_  = h1_ + (h2s_ - h1_) / eta_s
    h3_  = (am.State(FLUID, P=pc, T=am.T_sat(FLUID, pc) - dT_sub).h if dT_sub > 0
            else am.sat_liquid(FLUID, p=pc).h)
    w, qh, ql = h2_ - h1_, h2_ - h3_, h1_ - h3_
    return {"COP": qh / w, "m_flow, kg/s": Q_H / qh, "W_comp, W": Q_H / qh * w,
            "T2, C": am.C(am.State(FLUID, P=pc, H=h2_).T),
            "q_L, kJ/kg": ql / 1e3}

base = cycle()
real = cycle(eta_s=0.72, dT_sub=5.0)

print(f"{'':16s}{'ideal':>12s}{'eta=0.72, dTsub=5':>20s}{'change':>12s}")
for k in base:
    a, b = base[k], real[k]
    print(f"{k:16s}{a:12.4f}{b:20.4f}{(b-a)/a*100:11.1f}%")
'''))

C.append(md("""## 7. The deliverable

A sweep of condensing temperature, written to a filterable workbook. This is
what you hand in: **Python is the engine, Excel is the deliverable.**
"""))
C.append(code('''T_cond_C = np.arange(50, 81, 2.5)
rows = am.sweep(lambda t: cycle(eta_s=0.72, dT_sub=5.0, T_cond=am.K(t)),
                T_cond_C, name="T_cond, C")

path = am.to_excel(
    "AM5061_D1_HeatPump.xlsx",
    {"T_cond sweep": rows},
    title="AM5061 D-1 · 28 kW dairy heat pump · R134a",
    summary=[("Heating duty", Q_H, "W"),
             ("Refrigerant", FLUID, ""),
             ("Evaporating temperature", am.C(T_evap), "C"),
             ("Isentropic efficiency", 0.72, "-"),
             ("Subcooling", 5.0, "K"),
             ("COP at 70 C condensing", real["COP"], "-"),
             ("Mass flow at 70 C", real["m_flow, kg/s"], "kg/s")],
    sources=[("R134a properties", "CoolProp 8.0.0, Tillner-Roth & Baehr (1994) EOS"),
             ("Case specification", "AM5061 brief D-1, Jul-Nov 2026"),
             ("Cycle model", "Ideal vapour-compression, isenthalpic expansion")])

print("written:", path)
for r in rows[::3]:
    print(f"  T_cond {r['T_cond, C']:5.1f} C -> COP {r['COP']:.4f}, "
          f"m_flow {r['m_flow, kg/s']:.4f} kg/s")
'''))

C.append(md("""Download the workbook from the file browser on the left (folder
icon), or run the cell below in Colab.
"""))
C.append(code('''try:
    from google.colab import files
    files.download("AM5061_D1_HeatPump.xlsx")
except ImportError:
    print("Not in Colab - the file is in this folder.")
'''))

C.append(md("""## What to hand in

1. The four state points, as a table with units.
2. COP, mass flow and compressor power, for the ideal case and for
   `eta_s = 0.72, dT_sub = 5`.
3. The p–h diagram.
4. The workbook, with your sweep.
5. **One paragraph** answering the design question in section 6.

State your property source. A number without its source is unmarkable.
"""))

build("Week01_HeatPump.ipynb", "Week 1 · The 28 kW dairy heat pump", C)
print("Week01_HeatPump.ipynb built")
