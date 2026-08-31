"""Week 4 - steam header insulation and the critical radius."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A **DN 150 steam header** at a Tiruppur textile mill, carrying saturated steam
at **8 bar(a)**. The energy manager wants the heat loss per metre at several
insulation thicknesses, and then asks a second question that sounds naive and
is not: *if insulation reduces loss, does more insulation always reduce it
further?*

Deliverable **D-4**: loss per metre at t = 25, 50, 75, 100, 150 mm, plus the
surface temperature and the conductivity the insulation actually ended up at.

### Three mechanisms, and one of them is a loop

Conduction through steel and wool, natural convection off the cladding, and
radiation from it. The wool's conductivity **rises with temperature**, so its
resistance depends on the answer. That is a loop, and you close it by iterating.
"""))
C.append(md("""## 1. The resistance network

Four resistances in series. The cylindrical conduction term is the one people
get wrong: because area grows with radius, the integral of `dr/(2πrkL)` gives a
**logarithm**, not `thickness/(k·A)`. On thick insulation that error is worth
tens of percent.
"""))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()

SIGMA, G_N, PI = 5.670374419e-8, 9.80665, np.pi

# geometry and boundary conditions, from the brief
r1, r2   = 0.077025, 0.08415      # m   DN 150 Sch 40 inside / outside radius
T_steam  = 443.564                # K   saturated steam at 8 bar(a)
T_amb    = 308.15                 # K   35 C shop floor
h_steam  = 8000.0                 # W/m2K  condensing/flowing steam film
eps_clad = 0.15                   # -   bright aluminium cladding
k_steel  = 50.0                   # W/mK
k0_ins, b_ins = 0.033, 1.5e-4     # k_ins = k0 + b*(T_mean_C)

def h_churchill_chu(T_s, T_amb, D):
    """Natural convection, horizontal cylinder. Valid to Ra ~ 1e12."""
    T_f = min(max(0.5*(T_s + T_amb), 250), 800)     # film temperature
    rho = PropsSI('D','P',101325,'T',T_f,'Air'); mu = PropsSI('V','P',101325,'T',T_f,'Air')
    k   = PropsSI('L','P',101325,'T',T_f,'Air'); cp = PropsSI('C','P',101325,'T',T_f,'Air')
    Pr, nu, alpha, beta = cp*mu/k, mu/rho, k/(rho*cp), 1/T_f
    Ra = max(G_N*beta*(T_s - T_amb)*D**3/(nu*alpha), 1e-8)
    Nu = (0.60 + 0.387*Ra**(1/6)/(1 + (0.559/Pr)**(9/16))**(8/27))**2
    return Nu*k/D

def h_radiation(T_s, T_sur, eps=eps_clad):
    """Linearised, and this is EXACT, not an approximation: Ts^4 - Tsur^4
    factorises into (Ts^2+Tsur^2)(Ts+Tsur)(Ts-Tsur)."""
    return eps*SIGMA*(T_s**2 + T_sur**2)*(T_s + T_sur)
'''))
C.append(md("""## 2. Solving the loop

Two unknowns are tangled: the surface temperature sets the outside coefficient,
and the mean insulation temperature sets its conductivity. Guess the heat flow,
work out both, check the network closes, iterate.
"""))
C.append(code('''def header(t_ins=0.050, L=1.0):
    r3 = r2 + t_ins
    A  = 2*PI*r3*L
    R_steam = 1/(h_steam*2*PI*r1*L)
    R_steel = np.log(r2/r1)/(2*PI*k_steel*L)

    h_tot = lambda Ts: h_churchill_chu(Ts, T_amb, 2*r3) + h_radiation(Ts, T_amb)
    def surface_T(q):
        f = lambda Ts: h_tot(Ts)*A*(Ts - T_amb) - q
        hi = T_steam
        while f(hi) < 0 and hi < 2000.0:   # cannot shed q even at steam temp
            hi += 200.0
        return brentq(f, T_amb + 1e-9, hi)

    def residual(q):
        T2 = T_steam - q*(R_steam + R_steel)        # insulation inner face
        Ts = surface_T(q)
        k_eff = max(k0_ins + b_ins*(0.5*(T2+Ts) - 273.15), 0.005)
        R_ins = np.log(r3/r2)/(2*PI*k_eff*L)
        return q*(R_steam + R_steel + R_ins) - (T_steam - Ts)

    # The heat flow varies by an order of magnitude across the thickness
    # sweep, so a fixed bracket does not hold. Expand until the sign changes.
    lo, hi = 0.1, 200.0
    while residual(lo)*residual(hi) > 0 and hi < 1e5:
        hi *= 2.0
    q  = brentq(residual, lo, hi)
    Ts = surface_T(q)
    T2 = T_steam - q*(R_steam + R_steel)
    k_eff = max(k0_ins + b_ins*(0.5*(T2+Ts) - 273.15), 0.005)
    R_ins = np.log(r3/r2)/(2*PI*k_eff*L)
    R_out = 1/(h_tot(Ts)*A)
    return {"t_ins, mm": t_ins*1e3, "q, W/m": q, "T_surface, C": Ts - 273.15,
            "k_ins used, W/mK": k_eff, "h_out, W/m2K": h_tot(Ts),
            "R_steam": R_steam, "R_steel": R_steel, "R_ins": R_ins, "R_out": R_out,
            "r_critical, mm": k_eff/h_tot(Ts)*1e3, "r3, mm": r3*1e3}

base = header(0.050)
for k, v in base.items():
    print(f"  {k:20s} {v:12.5f}")
'''))
C.append(md("""> **Check.** At 50 mm the loss is **78.24 W/m** with a surface at
> about 53.7 °C.
>
> Note where the resistance sits: the insulation carries almost all of it. The
> steam film and the steel wall are together worth well under a percent, which
> is why nobody specifies a steam-side coefficient carefully on a job like this.
"""))
C.append(md("## 3. The deliverable table"))
C.append(code('''rows = [header(t) for t in (0.025, 0.050, 0.075, 0.100, 0.150)]
print(f"{'t, mm':>7}{'q, W/m':>10}{'T_surf, C':>11}{'k_ins':>9}{'h_out':>8}{'R_ins %':>9}")
for r_ in rows:
    frac = 100*r_["R_ins"]/(r_["R_steam"]+r_["R_steel"]+r_["R_ins"]+r_["R_out"])
    print(f"{r_['t_ins, mm']:7.0f}{r_['q, W/m']:10.3f}{r_['T_surface, C']:11.2f}"
          f"{r_['k_ins used, W/mK']:9.5f}{r_['h_out, W/m2K']:8.3f}{frac:9.1f}")
print("\\n  Note the diminishing return: doubling 25 -> 50 mm saves far more"
      "\\n  than doubling 75 -> 150 mm. The log is why.")
'''))
C.append(md("""## 4. The second question: the critical radius

Add insulation and two things happen at once. The conduction path gets
**longer**, which helps. The outside surface gets **bigger**, which hurts.
Differentiate the total resistance and set it to zero:

`R_tot = ln(r/r_b)/(2πk) + 1/(2πrh)`  →  `dR/dr = 1/(2πkr) − 1/(2πhr²) = 0`  →  **r_cr = k/h**

Below that radius, adding insulation **raises** the loss.
"""))
C.append(code('''def bare_cylinder(t, r_bare, k_ins, h_out, T_core, T_amb=T_amb):
    r = r_bare + t
    R = np.log(r/r_bare)/(2*PI*k_ins) + 1/(2*PI*r*h_out)
    return (T_core - T_amb)/R

t = np.linspace(1e-6, 0.040, 2000)

# a 3 mm PVC-insulated cable in still air
q_cable = np.array([bare_cylinder(x, 0.0015, 0.17, 10.0, 353.15) for x in t])
r_cr_cable = 0.17/10.0

# the mill header, using the coefficients it actually settled at
q_pipe = np.array([bare_cylinder(x, r2, base["k_ins used, W/mK"],
                                 base["h_out, W/m2K"], T_steam) for x in t])
r_cr_pipe = base["k_ins used, W/mK"]/base["h_out, W/m2K"]

i = int(np.argmax(q_cable))
print(f"  cable: peak {q_cable[i]:.3f} W/m at r = {(0.0015+t[i])*1e3:.2f} mm"
      f"   (r_cr = k/h = {r_cr_cable*1e3:.1f} mm)")
print(f"  pipe : r_cr = {r_cr_pipe*1e3:.2f} mm, but the bare radius is already "
      f"{r2*1e3:.1f} mm")
print(f"  ratio r_cr/r_bare -> cable {r_cr_cable/0.0015:.1f}, pipe {r_cr_pipe/r2:.3f}")
print("\\n  Above 1, insulation can make things worse. Below 1, it never can.")
'''))
C.append(code('''fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.3))
a1.plot((0.0015+t)*1e3, q_cable, color=am.ORANGE, lw=2.4)
a1.axvline(r_cr_cable*1e3, color=am.MUTED, ls="--")
a1.plot((0.0015+t[i])*1e3, q_cable[i], "o", ms=9, color=am.NAVY, zorder=5)
a1.text(r_cr_cable*1e3, q_cable.min(), "  r_cr = k/h", color=am.MUTED, fontsize=9)
a1.set_xlabel("outer radius  (mm)"); a1.set_ylabel("loss  (W/m)")
a1.set_title("3 mm cable: loss RISES to a peak at 17 mm")

a2.plot((r2+t)*1e3, q_pipe, color=am.NAVY, lw=2.4)
a2.set_xlabel("outer radius  (mm)"); a2.set_ylabel("loss  (W/m)")
a2.set_title("DN 150 header: falls from the first millimetre")
plt.tight_layout(); plt.show()
'''))
C.append(md("""Same equation, opposite conclusion. The only difference is the
bare radius. This is why "always insulate more" is wrong as a rule and right as
a habit for pipes.
"""))
C.append(md("## 5. The workbook"))
C.append(code('''ts = np.arange(0.020, 0.201, 0.010)
sweep_rows = [header(float(x)) for x in ts]
crit_rows = [{"outer radius, mm": (0.0015+x)*1e3, "cable q, W/m": bare_cylinder(x,0.0015,0.17,10.,353.15)}
             for x in np.linspace(1e-6, 0.040, 81)]

path = am.to_excel("AM5061_D4_Insulation.xlsx",
    {"Thickness sweep": sweep_rows, "Critical radius (cable)": crit_rows},
    title="AM5061 D-4 . Tiruppur steam header insulation",
    summary=[("Steam temperature", T_steam-273.15, "C"),
             ("Ambient", T_amb-273.15, "C"),
             ("Pipe outside radius", r2*1e3, "mm"),
             ("Cladding emissivity", eps_clad, "-"),
             ("Loss at 50 mm", base["q, W/m"], "W/m"),
             ("Surface temperature at 50 mm", base["T_surface, C"], "C"),
             ("Critical radius, pipe", base["r_critical, mm"], "mm"),
             ("Critical radius, 3 mm cable", r_cr_cable*1e3, "mm")],
    sources=[("Air properties", "CoolProp 'Air' at film temperature, 101325 Pa"),
             ("Natural convection", "Churchill & Chu, horizontal cylinder"),
             ("Radiation", "grey body, linearised exactly"),
             ("Insulation k(T)", "k = 0.033 + 1.5e-4*T_mean_C, mineral wool"),
             ("Geometry", "DN 150 Sch 40, AM5061 brief D-4")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The thickness table: loss, surface temperature, and the conductivity the
   wool actually reached.
2. A recommended thickness **with a stated reason** — surface-temperature
   safety limit, payback, or both. Say which.
3. The critical-radius answer to the energy manager's second question, with the
   cable and the pipe on the same argument.
4. The workbook.

Note the surface temperatures. Anything above about 60 °C is a contact-burn
risk, and that may bind before economics does.
"""))
build("Week04_Insulation.ipynb", "Week 4 · Steam header insulation", C)
print("Week04 built")
