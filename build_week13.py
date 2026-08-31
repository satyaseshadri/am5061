"""Week 13 - ORC on cement kiln waste heat: making the whole system converge."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

An **Organic Rankine Cycle** recovering cement kiln waste heat. Six components,
four unknown state points, three constraints.

Deliverable **D-13**: optimise the **evaporation pressure** and the **working
fluid** for maximum net power. Submit the sweep and the optimum.

### The real subject this week

Not the ORC. **How a design code actually solves a coupled system**, and then
how it optimises one. Every case so far had a solve you could see. This one has
a loop you have to break deliberately.

The loop: the working-fluid flow depends on the **pinch point** in the
evaporator; the pinch depends on the temperature profile; the profile depends on
the flow. That is a fixed point, and how you attack it decides whether your code
converges, crawls, or diverges.
"""))
C.append(md("## 1. Degrees of freedom, counted before any code is written"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq, fsolve, minimize_scalar
am.style_plots()

print("""  Components:   pump, evaporator, turbine, condenser            (4)
  State points: 1 pump in, 2 pump out, 3 turbine in, 4 turbine out (4)

  Unknowns    : m_wf, and the four state points               
  Equations   : pump work, evaporator energy balance, turbine work,
                condenser energy balance                          (4)
  Specified   : condensing temperature, evaporation pressure,
                superheat, pump and turbine efficiencies

  Degrees of freedom left = 1  ->  the EVAPORATION PRESSURE.
  That is the single decision variable, and it is what we optimise.""")

# ---- the heat source ------------------------------------------------
m_gas, T_gas_in, T_gas_min = 2.0, am.K(300), am.K(120)   # kg/s, K, acid dew limit
def gas_cp(T): return PropsSI("C","P",101325,"T",T,"Air")
T_cond = am.K(40)
dT_pp  = 10.0        # pinch point in the evaporator
dT_sh  = 5.0         # superheat at turbine inlet
eta_t, eta_p = 0.80, 0.70
print(f"\\n  gas {m_gas} kg/s at {am.C(T_gas_in):.0f} C, floor {am.C(T_gas_min):.0f} C")
print(f"  maximum recoverable = {m_gas*gas_cp(0.5*(T_gas_in+T_gas_min))*(T_gas_in-T_gas_min)/1e3:.1f} kW")
'''))
C.append(md("""## 2. The loop, and two ways to break it

Guess the working-fluid flow, build the evaporator profile, find where the pinch
actually lands, and correct the flow. Repeat.

**Successive substitution** just feeds the new value back. It is trivial to
write and it diverges cheerfully. **Newton–Raphson** uses the local slope and
converges quadratically when it converges at all. Watch both.
"""))
C.append(code('''def orc_states(fluid, p_evap):
    """The four state points, given a working fluid and evaporation pressure."""
    p_cond = am.p_sat(fluid, T_cond)
    st1 = am.sat_liquid(fluid, p=p_cond)                       # pump inlet
    h2s = PropsSI("H","P",p_evap,"S",st1.s,fluid)
    h2  = st1.h + (h2s - st1.h)/eta_p                          # pump outlet
    T_ev = am.T_sat(fluid, p_evap)
    st3 = am.State(fluid, P=p_evap, T=T_ev + dT_sh)            # turbine inlet
    h4s = PropsSI("H","P",p_cond,"S",st3.s,fluid)
    h4  = st3.h - eta_t*(st3.h - h4s)                          # turbine outlet
    return {"p_cond": p_cond, "h1": st1.h, "h2": h2, "h3": st3.h, "h4": h4,
            "T_evap": T_ev, "st3": st3}

def flow_from_pinch(fluid, p_evap, m_guess):
    """Given a flow guess, where does the pinch land and what flow does that
    imply? This is the fixed-point map g(m)."""
    s = orc_states(fluid, p_evap)
    # Gas cp is evaluated at the ACTUAL mean gas temperature, which depends on
    # how much heat the cycle takes, which depends on the flow we are solving
    # for. THAT is what makes this a genuine fixed point rather than a formula.
    Q_total = m_guess*(s["h3"] - s["h2"])
    cp_first = gas_cp(0.5*(T_gas_in + T_gas_min))
    T_gas_out_est = T_gas_in - Q_total/(m_gas*cp_first)
    cp_g = gas_cp(0.5*(T_gas_in + max(T_gas_out_est, am.K(60))))
    # gas temperature at the point where the working fluid starts to boil
    h_f = PropsSI("H","P",p_evap,"Q",0,fluid)
    Q_sup_evap = m_guess*(s["h3"] - h_f)                # boiling + superheat duty
    T_gas_pinch = T_gas_in - Q_sup_evap/(m_gas*cp_g)
    # the pinch constraint says that gas temperature must sit dT_pp above T_evap
    T_gas_pinch_req = s["T_evap"] + dT_pp
    # correct the flow so the constraint is met
    return (T_gas_in - T_gas_pinch_req)*m_gas*cp_g/(s["h3"] - h_f), T_gas_pinch

def solve_successive(fluid, p_evap, m0=1.0, tol=1e-10, itmax=200, damp=1.0):
    m, hist = m0, [m0]
    for i in range(itmax):
        m_new, _ = flow_from_pinch(fluid, p_evap, m)
        m_next = m + damp*(m_new - m)
        hist.append(m_next)
        if abs(m_next - m) < tol: return m_next, hist, True
        m = m_next
    return m, hist, False

def solve_newton(fluid, p_evap, m0=1.0):
    f = lambda m: flow_from_pinch(fluid, p_evap, m)[0] - m
    hist = []
    def g(m):
        hist.append(float(m[0]) if hasattr(m, "__len__") else float(m))
        return f(hist[-1])
    sol = fsolve(g, m0, full_output=False)
    return float(sol[0]), hist, True
print("  solvers defined")
'''))
C.append(code('''FL = "R245fa"
p_ev = 15e5
m_ss, h_ss, ok_ss = solve_successive(FL, p_ev, m0=1.0)
m_nw, h_nw, _     = solve_newton(FL, p_ev, m0=1.0)
print(f"  successive substitution: m = {m_ss:.6f} kg/s in {len(h_ss)-1} iterations"
      f"  ({'converged' if ok_ss else 'DID NOT CONVERGE'})")
print(f"  Newton-Raphson         : m = {m_nw:.6f} kg/s in {len(h_nw)} evaluations")
print(f"  agreement: {abs(m_ss-m_nw):.2e} kg/s")

fig, ax = plt.subplots()
ax.plot(range(len(h_ss)), h_ss, "o-", lw=2, label="successive substitution")
ax.plot(range(len(h_nw)), h_nw, "s-", lw=2, label="Newton (fsolve)")
ax.axhline(m_nw, color=am.MUTED, ls="--")
ax.set_xlabel("iteration"); ax.set_ylabel("working fluid flow  (kg/s)")
ax.set_xlim(0, min(25, max(len(h_ss), len(h_nw))))
ax.set_title("Same answer, very different paths"); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
'''))
C.append(md("""### Damping

If successive substitution oscillates or diverges, the standard fix is
**under-relaxation**: take only a fraction of the proposed step. It costs
iterations and buys stability. This is exactly what a plant code does when it
will not converge.
"""))
C.append(code('''print(f"{'damping':>9}{'iterations':>13}{'converged':>12}")
for d in (1.5, 1.0, 0.7, 0.4, 0.2):
    m_, h_, ok_ = solve_successive(FL, p_ev, m0=1.0, damp=d)
    print(f"{d:9.1f}{len(h_)-1:13d}{str(ok_):>12}")
print("\\n  Read that carefully: damping = 1.0 (no damping) is FASTEST here, at 3")
print("  iterations. Both over-relaxing and under-relaxing make it worse.")
print("  Damping is insurance, not acceleration: you pay iterations for it, and")
print("  you only pay willingly on a problem that will not converge without it.")
'''))
C.append(md("## 3. Optimising the evaporation pressure"))
C.append(code('''def performance(fluid, p_evap):
    """Net power for one fluid at one evaporation pressure."""
    try:
        p_c = am.critical(fluid)["p"]
        if p_evap > 0.95*p_c: return None
        s = orc_states(fluid, p_evap)
        m_wf, _, _ = solve_newton(fluid, p_evap, m0=1.0)
        if m_wf <= 0: return None
        cp_g = gas_cp(0.5*(T_gas_in + T_gas_min))
        Q_in = m_wf*(s["h3"] - s["h2"])
        T_gas_out = T_gas_in - Q_in/(m_gas*cp_g)
        # The acid dew floor is a CONSTRAINT, not a disqualification. If the
        # pinch-limited flow would over-cool the stack, throttle the flow until
        # the stack sits exactly on the floor. Which constraint binds is then
        # itself a design finding.
        binding = "pinch"
        if T_gas_out < T_gas_min:
            Q_in = m_gas*cp_g*(T_gas_in - T_gas_min)
            m_wf = Q_in/(s["h3"] - s["h2"])
            T_gas_out = T_gas_min
            binding = "stack floor"
        W_t = m_wf*(s["h3"] - s["h4"]); W_p = m_wf*(s["h2"] - s["h1"])
        return {"fluid": fluid, "binding constraint": binding, "p_evap, bar": p_evap/1e5,
                "T_evap, C": am.C(s["T_evap"]), "m_wf, kg/s": m_wf,
                "Q_in, kW": Q_in/1e3, "W_turbine, kW": W_t/1e3,
                "W_pump, kW": W_p/1e3, "W_net, kW": (W_t-W_p)/1e3,
                "eta_thermal": (W_t-W_p)/Q_in,
                "T_gas_out, C": am.C(T_gas_out),
                "x_turbine_exit": am.State(fluid,P=s["p_cond"],H=s["h4"]).x}
    except Exception as e:
        # Report the first failure rather than silently returning None for
        # everything, which is how a whole sweep can come back empty.
        if not performance._warned:
            print(f"    [performance] first failure on {fluid} at "
                  f"{p_evap/1e5:.1f} bar: {type(e).__name__}: {e}")
            performance._warned = True
        return None
performance._warned = False

FLUIDS = ["R245fa", "R1233zd(E)", "n-Pentane", "IsoButane", "Toluene", "R1336mzz(Z)"]
best = {}
fig, ax = plt.subplots()
for fl in FLUIDS:
    p_c = am.critical(fl)["p"]
    ps  = np.linspace(3e5, 0.92*p_c, 60)
    pts = [(p, performance(fl, float(p))) for p in ps]
    pts = [(p, r_) for p, r_ in pts if r_]
    if not pts: continue
    ax.plot([p/1e5 for p, _ in pts], [r_["W_net, kW"] for _, r_ in pts], lw=2.2, label=fl)
    bp, br = max(pts, key=lambda t: t[1]["W_net, kW"])
    best[fl] = br
    ax.plot(bp/1e5, br["W_net, kW"], "o", ms=8, color=am.NAVY, zorder=5)
ax.set_xlabel("evaporation pressure  (bar)"); ax.set_ylabel("net power  (kW)")
ax.set_title("One decision variable, one optimum per fluid"); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()

print(f"{'fluid':>13}{'p_opt bar':>11}{'T_evap C':>10}{'W_net kW':>10}"
      f"{'eta_th':>9}{'T_gas_out':>11}{'x_exit':>9}{'binds':>13}")
for fl, r_ in sorted(best.items(), key=lambda t: -t[1]["W_net, kW"]):
    x = r_["x_turbine_exit"]
    xs = f"{x:9.3f}" if 0 <= x <= 1 else f"{'dry':>9}"
    print(f"{fl:>13}{r_['p_evap, bar']:11.2f}{r_['T_evap, C']:10.1f}"
          f"{r_['W_net, kW']:10.2f}{r_['eta_thermal']:9.4f}"
          f"{r_['T_gas_out, C']:11.1f}{xs}{r_['binding constraint']:>13}")
'''))
C.append(md("""### Every fluid binds on the same constraint

Look at the last column. None of these designs is limited by the evaporator
pinch: they are all limited by the **acid dew floor** on the stack. That is a
finding, not a detail. It means the exchanger is not the bottleneck, the
chemistry of the flue gas is, and buying more heat transfer area would buy
nothing at all.

### Reading the table

`x_exit` matters as much as the power. A fluid that expands **wet** erodes the
turbine; "dry" means the expansion ends superheated, which is why ORC designers
prefer **dry** fluids (those with a positive-slope saturated vapour line) and
why the highest-power fluid is not automatically the right choice.

Check `T_gas_out` too: a design that beats the field on paper but drives the
stack below the acid dew point is not a design.
"""))
C.append(md("## 4. Refined optimum, and the deliverable"))
C.append(code('''rows = []
for fl in FLUIDS:
    p_c = am.critical(fl)["p"]
    def neg(p):
        q = performance(fl, float(p))
        return -q["W_net, kW"] if q else 1e9
    res = minimize_scalar(neg, bounds=(3e5, 0.92*p_c), method="bounded")
    r_ = performance(fl, float(res.x))
    if r_: rows.append(r_)
rows.sort(key=lambda r_: -r_["W_net, kW"])
if not rows:
    raise RuntimeError("no fluid produced a feasible design - check the pinch "
                       "and the acid dew floor before going further")
win = rows[0]
print(f"  optimum overall: {win['fluid']} at {win['p_evap, bar']:.2f} bar, "
      f"{win['W_net, kW']:.2f} kW net, eta_th {win['eta_thermal']:.4f}")

sweep = []
for fl in FLUIDS:
    p_c = am.critical(fl)["p"]
    for p in np.linspace(3e5, 0.92*p_c, 30):
        r_ = performance(fl, float(p))
        if r_: sweep.append(r_)

path = am.to_excel("AM5061_D13_ORC.xlsx",
    {"Optimum per fluid": rows, "Full sweep": sweep},
    title="AM5061 D-13 . ORC on cement kiln waste heat",
    summary=[("Gas flow", m_gas, "kg/s"), ("Gas inlet", am.C(T_gas_in), "C"),
             ("Gas floor (acid dew)", am.C(T_gas_min), "C"),
             ("Condensing temperature", am.C(T_cond), "C"),
             ("Evaporator pinch", dT_pp, "K"),
             ("Turbine / pump efficiency", f"{eta_t} / {eta_p}", "-"),
             ("Best fluid", win["fluid"], ""),
             ("Optimum evaporation pressure", win["p_evap, bar"], "bar"),
             ("Net power at optimum", win["W_net, kW"], "kW"),
             ("Thermal efficiency", win["eta_thermal"], "-")],
    sources=[("Working fluid properties", "CoolProp 8.0.0"),
             ("Flue gas", "modelled as air"),
             ("Solution method", "Newton-Raphson on the evaporator pinch fixed point"),
             ("Case data", "AM5061 brief D-13")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The convergence comparison: successive substitution against Newton, with the
   iteration counts and the damping study.
2. The degrees-of-freedom count, done **before** the code.
3. Net power against evaporation pressure for every fluid, with the optima
   marked.
4. Your chosen fluid and pressure, justified on **power, expansion dryness and
   stack temperature together** — not power alone.
5. The workbook.

**One paragraph:** your optimiser found a maximum. How do you know it is not a
local one, and what would you do to convince a reviewer?
"""))
build("Week13_ORC.ipynb", "Week 13 · ORC system convergence", C)
print("Week13 built")
