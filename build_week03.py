"""Week 3 - Chennai data centre: psychrometry, evaporative cooling, cooling tower."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A Chennai data centre. You are asked whether a **condenser-water setpoint** can
be held by a cooling tower, and what an evaporative pre-cooler adds.

Deliverable **D-3**: the psychrometric state, the wet bulb, what a tower can
actually deliver, and the honest answer on the setpoint.

### The one idea

Every evaporative device on this campus is bounded by the **wet-bulb
temperature**. Not the dry bulb. A tower approaches it, a pre-cooler approaches
it, and neither passes it. Chennai's problem is not that it is hot; it is that
it is *humid*, so the wet bulb sits close to the dry bulb and there is little
room to work in.
"""))
C.append(md("""## 1. Psychrometrics, and one honest discrepancy

CoolProp's moist-air model applies the **real-gas enhancement factor**; the
simple equations in ASHRAE Ch. 1 do not. So humidity ratio comes out about
0.4% higher here than the textbook table. Both are defensible. Quote which you
used.
"""))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.HumidAirProp import HAPropsSI
from scipy.optimize import brentq, fsolve
am.style_plots()

P = 101325.0                       # Pa, sea level

h_sat = lambda T: HAPropsSI('H','T',T,'P',P,'R',1.0)   # J per kg DRY AIR
W_sat = lambda T: HAPropsSI('W','T',T,'P',P,'R',1.0)

def air_state(T_db, phi, p=P):
    """Every psychrometric property of one moist-air state, dry-air basis."""
    return {"T_db, C": T_db-273.15,
            "phi": phi,
            "W, kg/kg_da": HAPropsSI('W','T',T_db,'P',p,'R',phi),
            "h, kJ/kg_da": HAPropsSI('H','T',T_db,'P',p,'R',phi)/1e3,
            "T_dew, C":    HAPropsSI('D','T',T_db,'P',p,'R',phi)-273.15,
            "T_wet, C":    HAPropsSI('B','T',T_db,'P',p,'R',phi)-273.15}

design = air_state(am.K(30), 0.60)
print("  Chennai design state, 30 C / 60% RH")
for k, v in design.items(): print(f"    {k:14s} {v:10.5f}")
print(f"\\n    wet-bulb depression {design['T_db, C']-design['T_wet, C']:.3f} K")
print("\\n  against ASHRAE Handbook Fundamentals 2017 Ch.1:")
print(f"    W      {design['W, kg/kg_da']:.6f}  vs 0.016045   (+0.44%, enhancement factor)")
print(f"    h      {design['h, kJ/kg_da']:.3f}     vs 71.19")
print(f"    T_dew  {design['T_dew, C']:.3f}     vs 21.39")
print(f"    T_wet  {design['T_wet, C']:.4f}    vs 23.81      <- the number that matters")
'''))
C.append(md("""> **Check.** The wet bulb is **23.81 °C**. That agrees with ASHRAE and
> with the retired Modelica model to four decimals, which is what matters: every
> conclusion this week rests on the wet bulb, not on the humidity ratio.
"""))
C.append(md("""## 2. Why Chennai is hard

Compare the design day with a monsoon morning. The dry bulb *falls*, and the
situation gets **worse**.
"""))
C.append(code('''cases = {"design day, 30 C / 60%": air_state(am.K(30), 0.60),
         "monsoon morning, 28 C / 95%": air_state(am.K(28), 0.95),
         "dry summer afternoon, 38 C / 35%": air_state(am.K(38), 0.35)}
print(f"{'':34s}{'T_db':>8}{'T_wet':>9}{'depression':>12}")
for nme, c in cases.items():
    print(f"{nme:34s}{c['T_db, C']:8.1f}{c['T_wet, C']:9.2f}"
          f"{c['T_db, C']-c['T_wet, C']:12.2f}")
print("\\n  The monsoon morning is 10 K cooler than the dry afternoon and has"
      "\\n  almost NO evaporative capacity left. That collapse is the case.")
'''))
C.append(md("""## 3. Direct evaporative cooler

Saturation effectiveness says how far along the wet-bulb depression the air
actually gets. It cannot reach the wet bulb, and it certainly cannot pass it.
"""))
C.append(code('''def evap_cooler(T_in, W_in, eps_sat=0.85, p=P):
    T_wb = HAPropsSI('B','T',T_in,'P',p,'W',W_in)
    T_out = T_in - eps_sat*(T_in - T_wb)
    h_in  = HAPropsSI('H','T',T_in,'P',p,'W',W_in)
    # Adiabatic: the only enthalpy added is the liquid make-up at T_wb.
    # "Constant wet bulb" is then a RESULT, not an assumption.
    W_out = brentq(lambda W: HAPropsSI('H','T',T_out,'P',p,'W',W)
                             - (h_in + (W - W_in)*4186.0*(T_wb-273.15)), W_in, 0.06)
    return {"T_in, C": T_in-273.15, "T_out, C": T_out-273.15,
            "T_wb, C": T_wb-273.15, "dW, kg/kg_da": W_out-W_in,
            "T_wb_out, C": HAPropsSI('B','T',T_out,'P',p,'W',W_out)-273.15}

for nme, (T, phi) in {"design day": (am.K(30), .60),
                      "monsoon morning": (am.K(28), .95)}.items():
    W = HAPropsSI('W','T',T,'P',P,'R',phi)
    e = evap_cooler(T, W)
    print(f"  {nme:18s} {e['T_in, C']:.1f} C -> {e['T_out, C']:.2f} C "
          f"(wet bulb {e['T_wb, C']:.2f} C, drop {e['T_in, C']-e['T_out, C']:.2f} K)")
    print(f"  {'':18s} outlet wet bulb {e['T_wb_out, C']:.3f} C  <- check it barely moved")
'''))
C.append(md("""## 4. The cooling tower, by Merkel's method

Merkel's contribution is to replace the temperature driving force with an
**enthalpy** driving force. That substitution is exact only when the Lewis
number is 1, and everything else about the method follows from it.

The tower is solved as N segments: water falls from node 0, air rises to it.
"""))
C.append(code('''def merkel_tower(N=20, m_w=10.0, m_a=8.0, cp_w=4181.0, KaV=8.0,
                 T_w_in=am.K(35), T_db=am.K(30), phi=0.60, p=P):
    """N-segment counter-flow wet tower. m_a is DRY air, not moist air."""
    h_in = HAPropsSI('H','T',T_db,'P',p,'R',phi)
    T_wb = HAPropsSI('B','T',T_db,'P',p,'R',phi)

    def residual(v):
        Tw, ha = v[:N+1], v[N+1:]
        r = [Tw[0] - T_w_in, ha[N] - h_in]                 # boundaries
        for i in range(N):
            # segment energy balance (Merkel neglects the evaporated stream)
            r.append(m_w*cp_w*(Tw[i]-Tw[i+1]) - m_a*(ha[i]-ha[i+1]))
            # Merkel transfer, arithmetic-mean driving ENTHALPY
            r.append(m_a*(ha[i]-ha[i+1])
                     - (KaV/N)*0.5*((h_sat(Tw[i])-ha[i]) + (h_sat(Tw[i+1])-ha[i+1])))
        return np.array(r)

    guess = np.concatenate([np.linspace(T_w_in, T_wb+2, N+1),
                            np.linspace(h_in + m_w*cp_w*5/m_a, h_in, N+1)])
    sol = fsolve(residual, guess)
    Tw, ha = sol[:N+1], sol[N+1:]
    Q_rej, Q_air = m_w*cp_w*(Tw[0]-Tw[N]), m_a*(ha[0]-ha[N])
    return {"L/G": m_w/m_a, "KaV/L": KaV/m_w,
            "T_w_out, C": Tw[N]-273.15, "range, K": Tw[0]-Tw[N],
            "approach, K": Tw[N]-T_wb, "T_wb, C": T_wb-273.15,
            "Q_rejected, W": Q_rej,
            "energy residual, %": 100*(Q_rej-Q_air)/Q_rej,
            "_profile": (Tw, ha)}

t = merkel_tower()
for k, v in t.items():
    if not k.startswith("_"): print(f"  {k:22s} {v:14.6f}")
'''))
C.append(md("""**Two checks before you believe anything it prints.** The energy
residual must be zero to machine precision — it is the sum of the segment
balances, so a non-zero value means the solve did not converge. And raising
`KaV` by orders of magnitude must drive the approach down towards a floor.
"""))
C.append(code('''print(f"{'KaV':>10}{'KaV/L':>9}{'approach, K':>14}")
for kav in (4., 8., 20., 40., 100., 200., 1000.):
    q = merkel_tower(KaV=kav)
    print(f"{kav:10.0f}{q['KaV/L']:9.2f}{q['approach, K']:14.4f}")
print("\\n  It converges to about 0.73 K, NOT to zero. The next section is why.")
'''))
C.append(md("""## 5. What an infinitely large tower could do

The air operating line is **straight**; the saturation curve is **convex**. An
infinitely large tower runs until they first touch, and there are three places
that can happen:

- **(a) bottom touch** — the classical wet-bulb-like floor
- **(b) top touch** — exit air saturated at the entering water temperature
- **(c) internal tangency** — the one people forget

At high L/G the operating line touches the saturation curve *in the middle of
the fill*. The tower is then pinched at neither end and no amount of fill gets
past it. **The binding limit is the warmest of the three.**
"""))
C.append(code('''def tower_limits(m_w=10.0, m_a=8.0, cp_w=4181.0,
                 T_w_in=am.K(35), T_db=am.K(30), phi=0.60, p=P):
    h_in  = HAPropsSI('H','T',T_db,'P',p,'R',phi)
    T_wb  = HAPropsSI('B','T',T_db,'P',p,'R',phi)
    slope = m_w*cp_w/m_a                       # operating-line slope

    T_bottom = brentq(lambda T: h_sat(T) - h_in, 253.15, T_w_in)
    T_top    = T_w_in - m_a*(h_sat(T_w_in) - h_in)/(m_w*cp_w)

    dh_sat = lambda T: (h_sat(T+0.01) - h_sat(T-0.01))/0.02
    try:    T_tp = brentq(lambda T: dh_sat(T) - slope, 253.2, 353.0)
    except ValueError: T_tp = None
    T_tan = None if T_tp is None else T_tp - (h_sat(T_tp) - h_in)*m_a/(m_w*cp_w)

    # The tangency candidate only MEANS anything if the tangent point lies
    # inside the tower. Include it unchecked and the predicted floor gets
    # WARMER as you add air, which is nonsense - and is how the mistake
    # announces itself.
    in_range = (T_tp is not None) and (T_tan < T_tp < T_w_in)
    cands = {"bottom": T_bottom, "top": T_top}
    if in_range: cands["tangency"] = T_tan
    binding = max(cands, key=cands.get)
    return {"L/G": m_w/m_a, "T_wb, C": T_wb-273.15,
            "T_bottom, C": T_bottom-273.15, "T_top, C": T_top-273.15,
            "T_tangent, C": None if T_tan is None else T_tan-273.15,
            "tangent point, C": None if T_tp is None else T_tp-273.15,
            "tangency valid": in_range,
            "T_w_out_min, C": cands[binding]-273.15,
            "approach_min, K": cands[binding]-T_wb, "binding limit": binding}

lim = tower_limits()
for k, v in lim.items(): print(f"  {k:20s} {v}")
'''))
C.append(md("""> **Check.** At L/G = 1.25 the binding limit is the **internal
> tangency**, giving a floor about **0.71 K above the wet bulb**.
>
> The retired Modelica model gave 0.727 K. The 0.018 K difference is the
> moist-air property formulation, not the physics: CoolProp uses a real-gas
> model, MSL an ideal-gas one. Every qualitative conclusion is unchanged.
"""))
C.append(code('''print(f"{'L/G':>7}{'T_min, C':>11}{'approach, K':>13}  binding")
for mw in (2., 4., 6., 8., 10., 12., 14.):
    q = tower_limits(m_w=mw)
    print(f"{q['L/G']:7.2f}{q['T_w_out_min, C']:11.3f}{q['approach_min, K']:13.3f}"
          f"  {q['binding limit']}")
print("\\n  The floor must never get WARMER as you add air (lower L/G).")
print("  If it does, the tangency test has been left out.")
'''))
C.append(md("""Note that at low L/G the approach goes slightly **negative**.
That is not a bug. Merkel's floor is where the saturated-air enthalpy equals
the *entering air* enthalpy, and that temperature is not the thermodynamic wet
bulb. The gap is tenths of a kelvin and it is real.
"""))
C.append(md("## 6. The driving-force plot\n\nOperating line against saturation curve."))
C.append(code('''Tw, ha = t["_profile"]
Tg = np.linspace(am.K(20), am.K(40), 200)
fig, ax = plt.subplots()
ax.plot(Tg-273.15, [h_sat(T)/1e3 for T in Tg], lw=2.4, label="saturation curve  h_sat(T)")
ax.plot(Tw-273.15, ha/1e3, "o-", color=am.ORANGE, lw=2.2, ms=4,
        label=f"air operating line, L/G = {t['L/G']:.2f}")
for mw, ls in ((14., ":"),):
    q = tower_limits(m_w=mw)
    Tp = np.array([q["T_w_out_min, C"], 35.0])
    ax.plot(Tp, (HAPropsSI('H','T',am.K(30),'P',P,'R',0.6)
                 + mw*4181.0/8.0*(Tp+273.15 - (q["T_w_out_min, C"]+273.15)))/1e3,
            ls, color=am.MUTED, lw=1.8, label=f"operating line, L/G = {mw/8:.2f} (tangent)")
ax.set_xlabel("temperature  (°C)"); ax.set_ylabel("enthalpy per kg dry air  (kJ/kg)")
ax.set_title("The tower runs until the straight line touches the convex curve")
ax.legend(fontsize=9); plt.tight_layout(); plt.show()
'''))
C.append(md("## 7. The deliverable"))
C.append(code('''lg_rows  = [tower_limits(m_w=mw) for mw in np.arange(2., 16.1, 1.)]
for r_ in lg_rows: r_.pop("_profile", None)
kav_rows = []
for kav in (2., 4., 8., 16., 32., 64., 128.):
    q = merkel_tower(KaV=kav); q.pop("_profile", None); kav_rows.append(q)
psy_rows = [air_state(am.K(T), phi)
            for T in (26, 28, 30, 32, 34, 36, 38) for phi in (0.35, 0.60, 0.80, 0.95)]

path = am.to_excel("AM5061_D3_CoolingTower.xlsx",
    {"Psychrometrics": psy_rows, "Tower limits vs LG": lg_rows, "Merkel vs KaV": kav_rows},
    title="AM5061 D-3 . Chennai data centre, cooling tower and pre-cooler",
    summary=[("Design dry bulb", 30.0, "C"), ("Design RH", 0.60, "-"),
             ("Design wet bulb", design["T_wet, C"], "C"),
             ("Wet-bulb depression", design["T_db, C"]-design["T_wet, C"], "K"),
             ("Tower L/G", t["L/G"], "-"),
             ("Approach at KaV = 8", t["approach, K"], "K"),
             ("Minimum approach at this L/G", lim["approach_min, K"], "K"),
             ("Binding limit", lim["binding limit"], "")],
    sources=[("Moist air", "CoolProp HAPropsSI, ASHRAE RP-1485 real-gas model"),
             ("Wet bulb", "thermodynamic, adiabatic saturation"),
             ("Tower model", "Merkel, Lewis number = 1, N-segment counter-flow"),
             ("Design conditions", "AM5061 brief D-3, Chennai")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The design psychrometric state, with your property source stated.
2. The wet bulb on the design day **and** on a monsoon morning, and one
   sentence on which is the harder condition and why.
3. The tower approach at the design L/G, and the floor that no amount of fill
   can beat.
4. **The honest answer**: is the requested setpoint feasible? If it needs an
   approach below about 2.8 K, say so — that is not a product you can buy, and
   the right response is to quote a vendor for the floor you assume.
5. The workbook.

> **Note on weather data.** The annual hours-of-availability analysis uses TMY
> files. The ISHRAE dataset is **licensed and must not be redistributed**, so it
> is not included here and must not be posted. Use the TMYx file supplied
> separately, and cite it.
"""))
build("Week03_CoolingTower.ipynb", "Week 3 · Chennai cooling tower", C)
print("Week03 built")
