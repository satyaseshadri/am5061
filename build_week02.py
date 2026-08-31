"""Week 2 - chilled-water distribution, the operating point."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A 500 TR campus chilled-water plant. The design intent was **69.9 kg/s** through
the DN 200 header. The installed pump is delivering considerably more, and the
energy manager wants to know why, and what it is costing.

Deliverable **D-2**: find the operating point, then compare **throttling**
against **speed control** at the same flow.

### What you are actually doing

The operating point is where the **pump curve** meets the **system curve**.
That is one nonlinear equation in one unknown. In Modelica the solver found it
for you; here you find it yourself, which means you can also draw it.
"""))
C.append(md("## 1. The two curves"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from scipy.optimize import brentq
am.style_plots()

rho, cp = 995.6, 4181.0        # chilled water, 7 C

dp_0 = 5.05e5    # Pa      pump shut-off head at full speed
m_0  = 140.0     # kg/s    pump runout flow at full speed
k_sys = 59.7     # Pa.s2/kg2   system resistance, as installed

def pump_head(m, N=1.0):
    """Quadratic pump curve, scaled by the affinity laws.
    head ~ N^2 and flow ~ N, so the whole curve slides down-left with speed."""
    return dp_0 * N**2 * (1 - (m / (m_0 * N))**2)

def system_loss(m, k=k_sys):
    """Fully turbulent: loss goes as the square of flow. The sign of m is kept
    so the curve is still correct if you ever reverse the flow."""
    return k * m * abs(m)
'''))
C.append(md("""## 2. The operating point

Where the two curves cross. `brentq` needs a bracket, and the physics gives you
one: flow is between zero and the pump's runout.
"""))
C.append(code('''def operating_point(k=k_sys, N=1.0):
    m = brentq(lambda m: pump_head(m, N) - system_loss(m, k), 1e-6, m_0*N*0.999)
    dp = pump_head(m, N)
    return {"m_dot, kg/s": m, "head, Pa": dp,
            "P_hyd, W": dp*m/rho, "N_rel": N, "k_system": k}

op = operating_point()
for key, val in op.items():
    print(f"  {key:14s} {val:12.4f}")
print(f"\\n  design intent was 69.9 kg/s -> running "
      f"{(op['m_dot, kg/s']/69.9 - 1)*100:.1f}% over")
'''))
C.append(md("""> **Check.** The installed plant settles at **76.8689 kg/s**. That
> overconsumption is what the brief asks you to explain.
"""))
C.append(md("## 3. Draw it\n\nIf you cannot draw this, you do not understand it."))
C.append(code('''m = np.linspace(0, m_0*0.999, 400)
fig, ax = plt.subplots()
ax.plot(m, pump_head(m)/1e5, lw=2.4, label="pump curve, N = 1.0")
ax.plot(m, system_loss(m)/1e5, lw=2.4, label=f"system curve, k = {k_sys}")
ax.plot(m, system_loss(m, k=90)/1e5, lw=1.6, ls="--",
        color=am.MUTED, label="system curve, throttled to k = 90")
ax.plot(m, pump_head(m, N=0.85)/1e5, lw=1.6, ls=":",
        color=am.MUTED, label="pump curve, N = 0.85")
ax.plot(op["m_dot, kg/s"], op["head, Pa"]/1e5, "o", ms=10, color=am.ORANGE, zorder=5)
ax.annotate(f"  {op['m_dot, kg/s']:.2f} kg/s", (op["m_dot, kg/s"], op["head, Pa"]/1e5),
            color=am.ORANGE, fontsize=11, va="center")
ax.axvline(69.9, color=am.MUTED, lw=1, ls="-.")
ax.text(69.9, 5.3, " design intent", color=am.MUTED, fontsize=9)
ax.set_xlabel("mass flow  (kg/s)"); ax.set_ylabel("head  (bar)")
ax.set_title("The operating point is an intersection, not a specification")
ax.set_ylim(0, 5.6); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
'''))
C.append(md("""## 4. The design question

Get back to the design flow of **69.9 kg/s** two ways, and compare the power.

- **Throttle**: close a valve, which raises `k_system`.
- **Slow down**: turn the VFD down, which lowers `N_rel`.

Both reach the same flow. They do not cost the same.
"""))
C.append(code('''TARGET = 69.9

k_throttled = brentq(lambda k: operating_point(k=k)["m_dot, kg/s"] - TARGET, 30., 400.)
N_slowed    = brentq(lambda N: operating_point(N=N)["m_dot, kg/s"] - TARGET, 0.3, 1.2)

cases = {"as installed": operating_point(),
         f"throttled (k={k_throttled:.1f})": operating_point(k=k_throttled),
         f"VFD (N={N_slowed:.4f})":          operating_point(N=N_slowed)}

print(f"{'':28s}{'flow kg/s':>12s}{'head bar':>11s}{'P_hyd kW':>11s}")
for nme, c in cases.items():
    print(f"{nme:28s}{c['m_dot, kg/s']:12.3f}{c['head, Pa']/1e5:11.3f}{c['P_hyd, W']/1e3:11.3f}")

p_t = cases[f"throttled (k={k_throttled:.1f})"]["P_hyd, W"]
p_v = cases[f"VFD (N={N_slowed:.4f})"]["P_hyd, W"]
print(f"\\n  speed control saves {(p_t-p_v)/p_t*100:.1f}% of hydraulic power "
      f"at the SAME flow ({(p_t-p_v)/1e3:.2f} kW)")
print("  Throttling does not remove the energy. It moves it into the valve.")
'''))
C.append(md("## 5. The deliverable"))
C.append(code('''ks = np.arange(40., 161., 5.)
rows_k = am.sweep(lambda k: operating_point(k=k), ks, name="k_system")
Ns = np.arange(0.60, 1.05, 0.025)
rows_N = am.sweep(lambda N: operating_point(N=N), Ns, name="N_rel_swept")

path = am.to_excel("AM5061_D2_Hydraulics.xlsx",
    {"Throttling": rows_k, "Speed control": rows_N},
    title="AM5061 D-2 . 500 TR campus chilled-water distribution",
    summary=[("Design intent flow", 69.9, "kg/s"),
             ("As-installed flow", op["m_dot, kg/s"], "kg/s"),
             ("Pump shut-off head", dp_0, "Pa"),
             ("Pump runout flow", m_0, "kg/s"),
             ("System resistance as installed", k_sys, "Pa.s2/kg2"),
             ("Hydraulic power saved by VFD at design flow", (p_t-p_v), "W")],
    sources=[("Water properties", "rho 995.6 kg/m3, cp 4181 J/kgK at 7 C"),
             ("Pump curve", "Quadratic fit to the installed pump, AM5061 brief D-2"),
             ("System curve", "Fully turbulent, dp = k m|m|")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The operating point, with the intersection plot.
2. Why the plant runs over its design flow.
3. Throttling versus speed control at 69.9 kg/s: flow, head and hydraulic power
   for each, and the annual cost difference at your own tariff assumption.
4. The workbook.

**One paragraph:** where does the energy go when you throttle?
"""))
build("Week02_Hydraulics.ipynb", "Week 2 · Chilled-water distribution", C)
print("Week02 built")
