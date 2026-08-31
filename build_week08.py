"""Week 8 - waste-heat recovery boiler on a cement kiln: epsilon-NTU."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A **two-pass fire-tube waste-heat recovery boiler** on a cement kiln, taken
directly from the HEX Class Discussion deck, Case 2.

| | |
|---|---|
| flue gas in | 400 °C, C_h = 315 W/K |
| pass 1 | **one** tube, D₁ = 20 cm, L₁ = 4 m, U₁ = 55 W/m²K |
| pass 2 | **ten** tubes, D₂ = 6 cm, L₂ = ?, U₂ = 110 W/m²K |
| shell | boiling water, T_sat = 150 °C, constant throughout |
| gas out | 200 °C |

Deliverable **D-8**: size pass 2. Then answer **D5**: why is U₂ twice U₁?

### Why this case is easy, and why that matters

The shell side is boiling at constant temperature, so `C_max → ∞`, the capacity
ratio `C_r = 0`, and **every configuration collapses to the same relation**:

`ε = 1 − exp(−NTU)`

Counter-flow, parallel-flow, cross-flow, shell-and-tube — identical. Phase
change removes the configuration question entirely.
"""))
C.append(md("## 1. Setup, and the C_r = 0 collapse"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
am.style_plots()
PI = np.pi

C_h     = 315.0        # W/K   gas capacity rate
T_g_in  = 400.0        # C
T_sat   = 150.0        # C     boiling shell side
T_g_out = 200.0        # C     target stack temperature

D1, L1, N1, U1 = 0.20, 4.0, 1,  55.0
D2,     N2, U2 = 0.06,      10, 110.0

print("  Every configuration gives the same effectiveness when C_r = 0:")
for cfg in ("counter", "parallel", "shell1", "cross-both-unmixed"):
    print(f"    {cfg:20s} eps(NTU=1) = {am.effectiveness(cfg, 1.0, 0.0):.6f}")
print(f"    closed form 1-exp(-1)      = {1-np.exp(-1):.6f}")
'''))
C.append(md("## 2. Pass 1, as built"))
C.append(code('''A1   = PI*D1*L1*N1
NTU1 = U1*A1/C_h
eps1 = 1 - np.exp(-NTU1)
Q1   = eps1*C_h*(T_g_in - T_sat)
T_m  = T_g_in - Q1/C_h                    # gas temperature between passes

print(f"  A1    = pi*{D1}*{L1}        = {A1:.4f} m2")
print(f"  NTU1  = U1*A1/C_h            = {NTU1:.4f}")
print(f"  eps1  = 1-exp(-NTU1)         = {eps1:.4f}")
print(f"  Q1    = eps1*C_h*(400-150)   = {Q1/1e3:.2f} kW")
print(f"  T_m   = 400 - Q1/C_h         = {T_m:.1f} C")
'''))
C.append(md("## 3. Pass 2 — the deliverable"))
C.append(code('''Q_total = C_h*(T_g_in - T_g_out)
Q2      = Q_total - Q1
eps2    = Q2/(C_h*(T_m - T_sat))
NTU2    = -np.log(1 - eps2)
A2      = NTU2*C_h/U2
L2      = A2/(N2*PI*D2)

print(f"  Q_total = C_h*(400-200)      = {Q_total/1e3:.2f} kW")
print(f"  Q2      = Q_total - Q1       = {Q2/1e3:.2f} kW")
print(f"  eps2    = Q2/[C_h*(T_m-150)] = {eps2:.4f}")
print(f"  NTU2    = -ln(1-eps2)        = {NTU2:.4f}")
print(f"  A2      = NTU2*C_h/U2        = {A2:.4f} m2")
print(f"  L2      = A2/(10*pi*0.06)    = {L2:.4f} m")
print(f"\\n  gas path: 400 C -> {T_m:.0f} C (pass 1) -> {T_g_out:.0f} C (pass 2)")
'''))
C.append(md("""> **Check.** L₂ = **1.78 m**, matching the HEX deck.

### Steam production

The feedwater has to be heated to saturation *and* evaporated. The sensible
part is easy to forget and it is not small.
"""))
C.append(code('''T_fw   = 50.0                                    # C, feedwater
cp_w   = PropsSI("C","P",4.76e5,"Q",0,"Water")   # ~150 C saturation
h_fg   = (PropsSI("H","P",4.76e5,"Q",1,"Water")
          - PropsSI("H","P",4.76e5,"Q",0,"Water"))
h_per_kg = cp_w*(T_sat - T_fw) + h_fg
m_steam  = Q_total/h_per_kg
print(f"  sensible  {cp_w*(T_sat-T_fw)/1e3:8.1f} kJ/kg   ({100*cp_w*(T_sat-T_fw)/h_per_kg:.1f}% of the total)")
print(f"  latent    {h_fg/1e3:8.1f} kJ/kg")
print(f"  total     {h_per_kg/1e3:8.1f} kJ/kg")
print(f"  steam     {m_steam:8.4f} kg/s = {m_steam*3600:.1f} kg/h")
'''))
C.append(md("""## 4. D5 — why is U₂ twice U₁?

The deck's hint is that ten small tubes raise the gas velocity relative to one
large tube. **Check it quantitatively rather than accepting it**, which is what
the question actually asks.
"""))
C.append(code('''A_flow_1 = N1*PI*D1**2/4
A_flow_2 = N2*PI*D2**2/4
v_ratio  = A_flow_1/A_flow_2

# Dittus-Boelter:  h ~ Re^0.8 / D  ~  (V*D)^0.8 / D  =  V^0.8 * D^-0.2
h_ratio = v_ratio**0.8 * (D2/D1)**-0.2

print(f"  flow area, pass 1 (1 x 20 cm)   {A_flow_1:.6f} m2")
print(f"  flow area, pass 2 (10 x 6 cm)   {A_flow_2:.6f} m2")
print(f"  velocity ratio  V2/V1           {v_ratio:.4f}")
print(f"  diameter ratio  D2/D1           {D2/D1:.4f}")
print(f"\\n  h2/h1 from Dittus-Boelter      {h_ratio:.4f}")
print(f"  U2/U1 as stipulated             {U2/U1:.4f}")
print(f"\\n  *** These do not agree. ***")
'''))
C.append(md("""### The honest answer

The velocity only rises by **11%**, because ten 6 cm tubes have almost the same
total flow area as one 20 cm tube. Working the Dittus–Boelter scaling through
gives **h₂/h₁ ≈ 1.38**, not 2.0.

So the stipulated `U₂ = 110 W/m²K` is a **design value, not a derived one**.
Most of the gain comes from the velocity being higher *and* the tube being
narrower; the rest is whatever the original designer assumed about fouling,
entry effects and the shell side.

**This is the point of the question.** The instinct — more small tubes means
higher velocity means higher U — is right in direction. The factor of two is
not something the geometry alone delivers, and a designer who assumes it
without checking will undersize pass 2 by about a third.

Report the number you compute, state the assumption you are testing, and say
where the rest would have to come from. That is a better answer than
reproducing 2.0.
"""))
C.append(code('''# What if U2 really were only 1.38 x U1?
U2_derived = U1*h_ratio
A2_d = NTU2*C_h/U2_derived
L2_d = A2_d/(N2*PI*D2)
print(f"  with the stipulated U2 = {U2:.0f} W/m2K  ->  L2 = {L2:.3f} m")
print(f"  with a derived     U2 = {U2_derived:.1f} W/m2K  ->  L2 = {L2_d:.3f} m")
print(f"  {100*(L2_d-L2)/L2:+.0f}% more tube, on the same duty.")
'''))
C.append(md("## 5. The stack temperature is the real decision"))
C.append(code('''def pass2_length(T_out, U=U2):
    Q_t = C_h*(T_g_in - T_out)
    Q_2 = Q_t - Q1
    if Q_2 <= 0: return np.nan, Q_2/1e3
    e2  = Q_2/(C_h*(T_m - T_sat))
    if e2 >= 1: return np.nan, Q_2/1e3
    return (-np.log(1-e2))*C_h/U/(N2*PI*D2), Q_2/1e3

rows = []
for T_out in np.arange(170.0, 261.0, 5.0):
    L, q2 = pass2_length(float(T_out))
    rows.append({"T_stack, C": float(T_out), "Q2, kW": q2, "L2, m": L,
                 "Q_total, kW": C_h*(T_g_in-T_out)/1e3,
                 "steam, kg/h": C_h*(T_g_in-T_out)/h_per_kg*3600})

fig, ax = plt.subplots()
ax.plot([r_["T_stack, C"] for r_ in rows], [r_["L2, m"] for r_ in rows],
        "o-", lw=2.4, color=am.ORANGE)
ax.axvline(170, color="#B03A2E", ls="--")
ax.text(172, 4, "acid dew point risk\\nbelow ~170 C", color="#B03A2E", fontsize=9)
ax.plot(T_g_out, L2, "o", ms=11, color=am.NAVY, zorder=5)
ax.annotate(f"  design point\\n  {L2:.2f} m", (T_g_out, L2), color=am.NAVY, fontsize=10)
ax.set_xlabel("stack temperature  (°C)"); ax.set_ylabel("pass 2 length  (m)")
ax.set_title("The last kelvin of recovery is the expensive one")
plt.tight_layout(); plt.show()
print("  Thermodynamics caps recovery at T_sat = 150 C. Acid dew point sets a")
print("  higher practical floor. Between them sits an economic optimum, and")
print("  that is a Week 14 calculation, not a Week 8 one.")
'''))
C.append(md("## 6. The deliverable"))
C.append(code('''design = [{"pass": 1, "tubes": N1, "D, m": D1, "L, m": L1, "U, W/m2K": U1,
           "A, m2": A1, "NTU": NTU1, "eps": eps1, "Q, kW": Q1/1e3,
           "T_gas_in, C": T_g_in, "T_gas_out, C": T_m},
          {"pass": 2, "tubes": N2, "D, m": D2, "L, m": L2, "U, W/m2K": U2,
           "A, m2": A2, "NTU": NTU2, "eps": eps2, "Q, kW": Q2/1e3,
           "T_gas_in, C": T_m, "T_gas_out, C": T_g_out}]

path = am.to_excel("AM5061_D8_WHRBoiler.xlsx",
    {"Design": design, "Stack temperature sweep": rows},
    title="AM5061 D-8 . Cement kiln waste-heat recovery boiler",
    summary=[("Gas capacity rate C_h", C_h, "W/K"),
             ("Gas inlet", T_g_in, "C"), ("Steam saturation", T_sat, "C"),
             ("Capacity ratio C_r", 0.0, "-"),
             ("Gas between passes T_m", T_m, "C"),
             ("Pass 2 length", L2, "m"),
             ("Total duty", Q_total/1e3, "kW"),
             ("Steam production", m_steam*3600, "kg/h"),
             ("U2/U1 stipulated", U2/U1, "-"),
             ("U2/U1 from Dittus-Boelter scaling", h_ratio, "-")],
    sources=[("Case data", "AM5061 HEX Class Discussion deck, Case 2, slides 11-13"),
             ("Effectiveness", "C_r = 0 limit: eps = 1 - exp(-NTU), all configurations"),
             ("Water/steam", "CoolProp, IAPWS-95, saturation at 150 C"),
             ("U1, U2", "STIPULATED in the source deck; see D5 discussion")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. Pass 2 length, with the ε-NTU working shown.
2. Steam production, and the sensible fraction of the feedwater load.
3. **D5 answered honestly**: the velocity ratio, the Dittus–Boelter scaling,
   the number you get, and why it differs from the stipulated 2.0.
4. The stack-temperature curve, with your recommended value and its
   justification.
5. The workbook.

**One paragraph:** `C_r = 0` because the shell side boils. At what point in
this design would that stop being true, and what would change if it did?
"""))
build("Week08_WHRBoiler.ipynb", "Week 8 · Waste-heat recovery boiler", C)
print("Week08 rebuilt")
