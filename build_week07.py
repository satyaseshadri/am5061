"""Week 7 - counter-flow heat exchanger, grid convergence."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

Liquid cooling for a **50 kW GPU rack**. You are building a counter-flow heat
exchanger **from first principles**: not one lumped UA, but N segments in
series with a metal wall between the streams.

Deliverable **D-7**: run N = 2, 5, 10, 20, 40 at UA = 400, 2000 and 6000 W/K,
and tabulate the numerical effectiveness against the analytical one.

### The question worth answering

How many segments do you need for 1% error, and **why does that number grow as
NTU rises?** That is the real deliverable. The rest is arithmetic.
"""))
C.append(md("""## 1. The discretised exchanger

Each segment is a well-mixed volume, so its outlet temperature *is* its bulk
temperature. Hot and cold run in opposite directions; the wall couples them
segment by segment with conductance `2·UA/N` on each side (two in series gives
`UA/N` per segment, and N of those gives UA).
"""))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from scipy.optimize import fsolve
am.style_plots()

cp, rho = 4181.0, 995.6
T_HOT_IN, T_COLD_IN = 350.0, 290.0      # K
K_TOT, DP = 1e5, 2.0e4                  # loss coefficient and the driving dp

def hx(N=5, UA=400.0, Th_in=T_HOT_IN, Tc_in=T_COLD_IN, k_tot=K_TOT, dp=DP):
    """Steady state of an N-segment counter-flow exchanger."""
    m = np.sqrt(dp / k_tot)             # both sides, same resistance
    C_ = m * cp
    G  = 2 * UA / N                     # hot->wall, and wall->cold

    def residual(v):
        Th, Tw, Tc = v[:N], v[N:2*N], v[2*N:]
        r = []
        for i in range(N):                       # hot marches 0 -> N-1
            th_in = Th_in if i == 0 else Th[i-1]
            r.append(C_*(th_in - Th[i]) - G*(Th[i] - Tw[i]))
        for i in range(N):                       # wall: what arrives, leaves
            r.append(G*(Th[i] - Tw[i]) - G*(Tw[i] - Tc[i]))
        for i in range(N):                       # cold marches N-1 -> 0
            tc_in = Tc_in if i == N-1 else Tc[i+1]
            r.append(C_*(Tc[i] - tc_in) - G*(Tw[i] - Tc[i]))
        return np.array(r)

    guess = np.concatenate([np.full(N, 340.), np.full(N, 320.), np.full(N, 300.)])
    sol = fsolve(residual, guess)
    Th, Tw, Tc = sol[:N], sol[N:2*N], sol[2*N:]
    NTU = UA / (m * cp)
    return {"N": N, "UA, W/K": UA, "m_dot, kg/s": m, "NTU": NTU,
            "eps_numerical": (Th_in - Th[-1])/(Th_in - Tc_in),
            "eps_analytical": NTU/(1 + NTU),
            "T_hot_out, K": Th[-1], "T_cold_out, K": Tc[0],
            "_profiles": (Th, Tw, Tc)}

r = hx()
for k, v in r.items():
    if not k.startswith("_"):
        print(f"  {k:16s} {v:12.6f}" if isinstance(v, float) else f"  {k:16s} {v:12d}")
'''))
C.append(md("""> **Check.** At N = 5, UA = 400 the numerical effectiveness is
> **0.170227**, against an analytical 0.176227.
>
> Both streams have the same `m·cp`, so the capacity ratio C_r = 1 and the
> counter-flow result collapses to **ε = NTU/(1+NTU)**. That is the only case
> where the analytical answer is this simple, which is why the case is built
> on it.
"""))
C.append(md("## 2. Grid convergence\n\nThe actual deliverable."))
C.append(code('''Ns  = [2, 5, 10, 20, 40, 80, 160]
UAs = [400.0, 2000.0, 6000.0]

rows = []
for UA in UAs:
    for N in Ns:
        q = hx(N=N, UA=UA)
        rows.append({"N": N, "UA, W/K": UA, "NTU": q["NTU"],
                     "eps_numerical": q["eps_numerical"],
                     "eps_analytical": q["eps_analytical"],
                     "error, %": 100*(q["eps_numerical"]-q["eps_analytical"])/q["eps_analytical"]})

print(f"{'UA':>7}{'NTU':>8}{'N':>6}{'eps_num':>11}{'eps_an':>10}{'err %':>9}")
for row in rows:
    print(f"{row['UA, W/K']:7.0f}{row['NTU']:8.3f}{row['N']:6d}"
          f"{row['eps_numerical']:11.6f}{row['eps_analytical']:10.6f}{row['error, %']:9.2f}")
'''))
C.append(code('''fig, ax = plt.subplots()
for UA in UAs:
    sub = [r_ for r_ in rows if r_["UA, W/K"] == UA]
    ax.plot([s["N"] for s in sub], [abs(s["error, %"]) for s in sub], "o-",
            label=f"UA = {UA:.0f} W/K   (NTU = {sub[0]['NTU']:.2f})")
ax.axhline(1.0, color=am.MUTED, ls="--", lw=1.4)
ax.text(2.2, 1.15, "1% error", color=am.MUTED, fontsize=9)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("segments  N"); ax.set_ylabel("|error| vs analytical  (%)")
ax.set_title("More NTU needs more segments for the same accuracy")
ax.legend(fontsize=9)
plt.tight_layout(); plt.show()

print("Segments needed for under 1% error:")
for UA in UAs:
    sub = [r_ for r_ in rows if r_["UA, W/K"] == UA]
    ok = [s["N"] for s in sub if abs(s["error, %"]) < 1.0]
    print(f"  UA {UA:6.0f} (NTU {sub[0]['NTU']:5.2f}) -> "
          f"{ok[0] if ok else '>160'} segments")
'''))
C.append(md("""**Why the number grows with NTU.** Each well-mixed segment is
isothermal, so a chain of N of them approximates a smooth exponential
temperature profile by a staircase of N steps. At low NTU the true profile is
nearly straight and a coarse staircase fits it well. At high NTU the profile
curves hard near the inlet, and you need more steps to follow the curvature.
Resolution has to track the gradient, not the length.
"""))
C.append(md("## 3. The temperature profile\n\nSee the staircase for yourself."))
C.append(code('''fig, ax = plt.subplots()
for N, style in ((5, "o-"), (40, "-")):
    Th, Tw, Tc = hx(N=N, UA=2000.)["_profiles"]
    xpos = (np.arange(N) + 0.5) / N
    ax.plot(xpos, Th, style, color=am.ORANGE, lw=2, ms=6,
            label=f"hot, N={N}", alpha=1.0 if N == 5 else 0.55)
    ax.plot(xpos, Tc, style, color=am.BLUE, lw=2, ms=6,
            label=f"cold, N={N}", alpha=1.0 if N == 5 else 0.55)
ax.set_xlabel("position along the exchanger, hot inlet at 0")
ax.set_ylabel("temperature  (K)")
ax.set_title("Counter-flow profiles at UA = 2000 W/K")
ax.legend(fontsize=9, ncol=2)
plt.tight_layout(); plt.show()
'''))
C.append(md("## 4. The deliverable"))
C.append(code('''path = am.to_excel("AM5061_D7_HeatExchanger.xlsx",
    {"Grid convergence": rows},
    title="AM5061 D-7 . Counter-flow HX, grid convergence",
    summary=[("Hot inlet", T_HOT_IN, "K"), ("Cold inlet", T_COLD_IN, "K"),
             ("Mass flow each side", r["m_dot, kg/s"], "kg/s"),
             ("Capacity ratio C_r", 1.0, "-"),
             ("eps at N=5, UA=400", r["eps_numerical"], "-"),
             ("eps analytical at UA=400", r["eps_analytical"], "-")],
    sources=[("Water properties", "rho 995.6 kg/m3, cp 4181 J/kgK"),
             ("Analytical effectiveness", "counter-flow, C_r = 1: eps = NTU/(1+NTU)"),
             ("Discretisation", "N well-mixed segments per side, wall capacity between")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The convergence table, all three UA values.
2. The error plot.
3. The number of segments for 1% error at each NTU, **and one paragraph on why
   it grows**.
4. The workbook.

A note on cost: this is a nonlinear solve in 3N unknowns. At N = 160 that is
480 equations, and it still runs in under a second. Discretisation is cheap.
Not knowing how much you need is what is expensive.
"""))
build("Week07_HeatExchanger.ipynb", "Week 7 · Counter-flow heat exchanger", C)
print("Week07 built")
