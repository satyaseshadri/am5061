"""Week 11 - transcritical CO2 booster for a supermarket cold chain."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A **transcritical CO₂ booster** for a supermarket cold chain in **Chennai**.
Two evaporating levels: **−30 °C frozen** and **−8 °C chilled**. CO₂ throughout.

Deliverable **D-11**: the **optimum gas-cooler pressure** as a function of
ambient temperature over 25–42 °C. Plot COP against P_gc and mark the optimum
locus.

### Why CO₂ has no condenser

CO₂'s critical point is **31.0 °C at 73.8 bar**. In Chennai the ambient is above
that for much of the year, so on the high side the CO₂ **never condenses**. It
is cooled, as a single dense phase, in a **gas cooler**.

That changes the design completely. With no condensation there is no saturation
line tying pressure to temperature, so **the high-side pressure becomes a free
variable** — and there is an optimum. Finding it is this week's work.

> This case was **impossible** on the previous toolchain: MSL carries CO₂ only
> as an ideal gas, which cannot represent transcritical behaviour at all.
"""))
C.append(md("## 1. Why an optimum exists"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq, minimize_scalar
am.style_plots()

F = "CO2"
crit = am.critical(F)
print(f"  CO2 critical point: {am.C(crit['T']):.2f} C, {crit['p']/1e5:.2f} bar")
print(f"  Chennai design ambient 35 C is ABOVE that, so the high side is")
print(f"  transcritical and there is no condenser.\\n")

T_gc_out = am.K(38)          # gas cooler exit, 35 C ambient + 3 K approach
print(f"{'P_gc, bar':>10}{'h at exit, kJ/kg':>19}{'rho, kg/m3':>13}")
for P in (75, 80, 85, 90, 95, 100, 110, 120):
    h = PropsSI("H","P",P*1e5,"T",T_gc_out,F)/1e3
    d = PropsSI("D","P",P*1e5,"T",T_gc_out,F)
    print(f"{P:10.0f}{h:19.2f}{d:13.2f}")
print("\\n  Raising the pressure costs compressor work, but it also drops the")
print("  gas-cooler exit enthalpy STEEPLY near the pseudo-critical region,")
print("  which buys refrigeration effect. Those two fight, so there is a peak.")
'''))
C.append(md("""## 2. The booster architecture

```
   LT evaporator (-30 C) -> LT compressor -+
                                            |--> MT suction -> MT compressor -> gas cooler
   MT evaporator (-8 C)  ------------------+                                        |
                                            flash gas from receiver <--- expansion <-+
```

The LT compressor discharges into the MT suction rather than to the gas cooler.
The receiver flash gas joins there too. One high-stage machine handles the lot.
"""))
C.append(code('''T_LT, T_MT = am.K(-30), am.K(-8)
Q_LT, Q_MT = 30e3, 90e3          # W, frozen and chilled cabinet loads
p_rec      = 38e5                # receiver pressure, typical
eta_LT, eta_MT = 0.65, 0.70      # isentropic efficiencies
dT_sup     = 5.0                 # useful superheat at both evaporators

p_LT, p_MT = am.p_sat(F, T_LT), am.p_sat(F, T_MT)
print(f"  LT evaporating  {am.C(T_LT):6.1f} C -> {p_LT/1e5:6.2f} bar")
print(f"  MT evaporating  {am.C(T_MT):6.1f} C -> {p_MT/1e5:6.2f} bar")
print(f"  receiver                        {p_rec/1e5:6.2f} bar")

def compress(p_in, h_in, p_out, eta):
    s_in = PropsSI("S","P",p_in,"H",h_in,F)
    h_s  = PropsSI("H","P",p_out,"S",s_in,F)
    return h_in + (h_s - h_in)/eta

def booster(P_gc, T_amb=am.K(35), approach=3.0):
    """Steady-state booster cycle. Returns duties, work and COP."""
    T_gc = T_amb + approach
    h_gc = PropsSI("H","P",P_gc,"T",T_gc,F)          # gas cooler exit

    # expansion to the receiver: flash separates liquid and vapour
    h_rec  = h_gc                                     # isenthalpic
    h_f    = PropsSI("H","P",p_rec,"Q",0,F)
    h_g    = PropsSI("H","P",p_rec,"Q",1,F)
    x_flash = min(max((h_rec - h_f)/(h_g - h_f), 0.0), 1.0)

    # LT circuit
    h_LT_in  = h_f                                    # liquid from receiver
    h_LT_out = PropsSI("H","P",p_LT,"T",T_LT+dT_sup,F)
    m_LT     = Q_LT/(h_LT_out - h_LT_in)
    h_LT_dis = compress(p_LT, h_LT_out, p_MT, eta_LT)
    W_LT     = m_LT*(h_LT_dis - h_LT_out)

    # MT circuit
    h_MT_in  = h_f
    h_MT_out = PropsSI("H","P",p_MT,"T",T_MT+dT_sup,F)
    m_MT     = Q_MT/(h_MT_out - h_MT_in)

    # MT suction mixes: MT evaporator + LT discharge + receiver flash gas
    m_liq   = m_LT + m_MT
    m_total = m_liq/max(1 - x_flash, 1e-6)            # total through the gas cooler
    m_flash = m_total - m_liq
    h_mix   = (m_MT*h_MT_out + m_LT*h_LT_dis + m_flash*h_g)/m_total
    h_MT_dis = compress(p_MT, h_mix, P_gc, eta_MT)
    W_MT     = m_total*(h_MT_dis - h_mix)

    return {"P_gc, bar": P_gc/1e5, "T_amb, C": am.C(T_amb), "T_gc_out, C": am.C(T_gc),
            "h_gc, kJ/kg": h_gc/1e3, "flash fraction": x_flash,
            "m_LT, kg/s": m_LT, "m_MT, kg/s": m_MT, "m_total, kg/s": m_total,
            "W_LT, kW": W_LT/1e3, "W_MT, kW": W_MT/1e3,
            "W_total, kW": (W_LT+W_MT)/1e3,
            "COP": (Q_LT+Q_MT)/(W_LT+W_MT),
            "discharge, C": am.C(PropsSI("T","P",P_gc,"H",h_MT_dis,F))}

r = booster(90e5)
for k, v in r.items(): print(f"  {k:16s} {v:10.4f}")
'''))
C.append(md("## 3. The optimum, at design ambient"))
C.append(code('''Ps = np.arange(75e5, 131e5, 0.5e5)
cop = [booster(P)["COP"] for P in Ps]
i = int(np.argmax(cop))
# A three-point bracket is fragile here because the peak moves with ambient.
# A bounded search over the physically sensible range always works.
res = minimize_scalar(lambda P: -booster(P)["COP"],
                      bounds=(75e5, 130e5), method="bounded")
P_opt = res.x

print(f"  grid maximum      P_gc = {Ps[i]/1e5:.1f} bar, COP = {cop[i]:.4f}")
print(f"  refined optimum   P_gc = {P_opt/1e5:.2f} bar, COP = {booster(P_opt)['COP']:.4f}")
print(f"\\n  COP at 80 bar  {booster(80e5)['COP']:.4f}")
print(f"  COP at optimum {booster(P_opt)['COP']:.4f}")
print(f"  COP at 120 bar {booster(120e5)['COP']:.4f}")
print("\\n  Running 10 bar off the optimum costs real energy. On a supermarket")
print("  that runs 8760 h a year, this single set-point is worth optimising.")
'''))
C.append(code('''fig, ax = plt.subplots()
for T_amb_C in (25, 30, 35, 40, 42):
    cs = [booster(P, T_amb=am.K(T_amb_C))["COP"] for P in Ps]
    ax.plot(Ps/1e5, cs, lw=2.2, label=f"{T_amb_C} °C ambient")
    j = int(np.argmax(cs))
    ax.plot(Ps[j]/1e5, cs[j], "o", ms=8, color=am.NAVY, zorder=5)
ax.set_xlabel("gas cooler pressure  (bar)"); ax.set_ylabel("system COP")
ax.set_title("Each ambient has its own optimum. The peaks trace a locus.")
ax.legend(fontsize=9)
plt.tight_layout(); plt.show()
'''))
C.append(md("## 4. The optimum locus — the deliverable"))
C.append(code('''rows = []
for T_amb_C in np.arange(25, 43, 1.0):
    res = minimize_scalar(lambda P: -booster(P, T_amb=am.K(T_amb_C))["COP"],
                          bounds=(75e5, 130e5), method="bounded")
    b = booster(res.x, T_amb=am.K(T_amb_C))
    rows.append({"T_ambient, C": float(T_amb_C), "P_gc optimum, bar": b["P_gc, bar"],
                 "COP at optimum": b["COP"], "W_total, kW": b["W_total, kW"],
                 "discharge, C": b["discharge, C"],
                 "flash fraction": b["flash fraction"]})

print(f"{'T_amb C':>9}{'P_opt bar':>11}{'COP':>9}{'W kW':>9}{'discharge C':>13}")
for r_ in rows[::3]:
    print(f"{r_['T_ambient, C']:9.0f}{r_['P_gc optimum, bar']:11.2f}"
          f"{r_['COP at optimum']:9.4f}{r_['W_total, kW']:9.2f}{r_['discharge, C']:13.1f}")

# a linear rule of thumb, fitted to the locus
T = np.array([r_["T_ambient, C"] for r_ in rows])
P = np.array([r_["P_gc optimum, bar"] for r_ in rows])
a, b_ = np.polyfit(T, P, 1)
print(f"\\n  fitted rule of thumb:  P_gc,opt = {a:.3f}*T_amb + {b_:.2f}  bar")
print(f"  max deviation from the true optimum over 25-42 C: "
      f"{np.max(np.abs(P - (a*T + b_))):.2f} bar")
# Below the critical temperature the high side can condense, so there is no
# transcritical optimum and the search returns the lower bound. Fitting through
# those points flatters nothing - refit on the transcritical range only.
mask = T >= 32
a2_, b2_ = np.polyfit(T[mask], P[mask], 1)
print(f"\\n  BUT below 31 C the cycle is SUBCRITICAL and the search just returns")
print(f"  the lower bound, so those points are not real optima. Refitting on")
print(f"  the transcritical range only (T >= 32 C):")
print(f"    P_gc,opt = {a2_:.3f}*T_amb + {b2_:.2f} bar,  max deviation "
      f"{np.max(np.abs(P[mask] - (a2_*T[mask] + b2_))):.2f} bar")
print("  Use the subcritical branch below 31 C: float the high side on the")
print("  condensing temperature, exactly as you would for any other refrigerant.")
'''))
C.append(code('''fig, (a1,a2) = plt.subplots(1,2, figsize=(11.8,4.2))
a1.plot(T, P, "o-", lw=2.4, color=am.ORANGE, label="true optimum")
a1.plot(T, a*T + b_, "--", lw=1.8, color=am.MUTED, label=f"{a:.2f}·T + {b_:.1f}")
a1.set_xlabel("ambient temperature  (°C)"); a1.set_ylabel("optimum P_gc  (bar)")
a1.set_title("The optimum locus is very nearly linear"); a1.legend(fontsize=9)
a2.plot(T, [r_["COP at optimum"] for r_ in rows], "o-", lw=2.4, color=am.NAVY)
a2.axvline(am.C(crit["T"]), color="#B03A2E", ls="--")
a2.text(am.C(crit["T"])+0.3, min(r_["COP at optimum"] for r_ in rows)+0.05,
        " critical\\n temperature", color="#B03A2E", fontsize=9)
a2.set_xlabel("ambient temperature  (°C)"); a2.set_ylabel("COP at the optimum")
a2.set_title("Chennai punishes CO2 in a way Europe does not")
plt.tight_layout(); plt.show()
print("  Below 31 C the high side can still condense and CO2 does well.")
print("  Above it, the cycle is transcritical and the COP falls away. That is")
print("  why parallel compression and ejectors exist, and why 'CO2 is the")
print("  natural refrigerant' needs a climate qualifier.")
'''))
C.append(md("## 5. The workbook"))
C.append(code('''sweep_rows = [booster(float(P), T_amb=am.K(35)) for P in Ps]
path = am.to_excel("AM5061_D11_CO2Booster.xlsx",
    {"Optimum locus": rows, "P_gc sweep at 35 C": sweep_rows},
    title="AM5061 D-11 . Transcritical CO2 booster, Chennai",
    summary=[("Refrigerant", F, ""),
             ("CO2 critical point", f"{am.C(crit['T']):.2f} C / {crit['p']/1e5:.2f} bar", ""),
             ("LT evaporating", am.C(T_LT), "C"), ("MT evaporating", am.C(T_MT), "C"),
             ("LT load", Q_LT/1e3, "kW"), ("MT load", Q_MT/1e3, "kW"),
             ("Receiver pressure", p_rec/1e5, "bar"),
             ("Gas cooler approach", 3.0, "K"),
             ("Optimum P_gc at 35 C", booster(P_opt)["P_gc, bar"], "bar"),
             ("COP at that optimum", booster(P_opt)["COP"], "-"),
             ("Rule of thumb slope", a, "bar/K"),
             ("Rule of thumb intercept", b_, "bar")],
    sources=[("CO2 properties", "CoolProp 8.0.0, Span & Wagner (1996) EOS"),
             ("Compressor efficiencies", "LT 0.65, MT 0.70 isentropic - ASSUMED"),
             ("Cabinet loads", "30 kW frozen, 90 kW chilled - AM5061 brief D-11"),
             ("Architecture", "booster with flash-gas bypass to MT suction")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. COP against P_gc at design ambient, with the optimum marked.
2. The **optimum locus** over 25–42 °C, and your fitted control rule.
3. The discharge temperature at the optimum — check it against the compressor's
   limit, typically about 140 °C. An optimum you cannot run is not an optimum.
4. One paragraph on what happens to this system as ambient crosses **31 °C**,
   and what hardware you would add to fix it.
5. The workbook.

**A note on the control rule.** A linear fit is what actually goes into a
supermarket controller. Report the maximum COP you give up by using it instead
of solving the optimisation live — if that penalty is small, the simple rule
wins, and saying so is the engineering judgement being assessed.
"""))
build("Week11_CO2Booster.ipynb", "Week 11 · Transcritical CO₂ booster", C)
print("Week11 built")
