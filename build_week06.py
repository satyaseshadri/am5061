"""Week 6 - condenser of a 10 kW residential heat pump: zone-wise design."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

The condenser of a **10 kW residential heat pump** on R134a. In Week 1 you were
handed the condensing temperature. Now you must produce the **tube length**.

Deliverable **D-6**: required length by **segment integration**, against the
same length by a **single mean-h LMTD** calculation. Quantify the error of the
lazy method.

### Why a condenser is three exchangers

Refrigerant enters superheated, condenses, and leaves subcooled. The
coefficient in those three zones differs by **an order of magnitude**. Averaging
across them is the mistake this case exists to expose.
"""))
C.append(md("## 1. The duty and the three zones"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()

F = "R134a"
Q_H     = 10e3          # W    heating duty
T_cond  = am.K(45)      # K    condensing temperature
T_evap  = am.K(0)       # K
eta_s   = 0.70
dT_sub  = 5.0           # K    subcooling
T_w_in  = am.K(30)      # K    water on
dT_w    = 10.0          # K    water rise
D_i     = 0.008         # m    refrigerant tube bore
PI      = np.pi

p_cond, p_evap = am.p_sat(F, T_cond), am.p_sat(F, T_evap)
st1 = am.sat_vapour(F, p=p_evap)
h2s = PropsSI("H", "P", p_cond, "S", st1.s, F)
h2  = st1.h + (h2s - st1.h)/eta_s               # compressor discharge
st2 = am.State(F, P=p_cond, H=h2)
h_g = am.sat_vapour(F, p=p_cond).h              # start of condensation
h_f = am.sat_liquid(F, p=p_cond).h              # end of condensation
h3  = am.State(F, P=p_cond, T=T_cond - dT_sub).h

m_r = Q_H/(h2 - h3)                              # refrigerant flow
m_w = Q_H/(4180.0*dT_w)                          # water flow

zones = {"desuperheat": h2 - h_g, "condense": h_g - h_f, "subcool": h_f - h3}
print(f"  discharge {st2.T_C:.2f} C, superheat {st2.T_C - am.C(T_cond):.2f} K")
print(f"  refrigerant flow {m_r*1e3:.3f} g/s,  water flow {m_w:.4f} kg/s\\n")
print(f"{'zone':14s}{'dh, kJ/kg':>12}{'Q, W':>10}{'% of duty':>11}")
for z, dh in zones.items():
    print(f"{z:14s}{dh/1e3:12.3f}{m_r*dh:10.1f}{100*dh/(h2-h3):11.1f}")
'''))
C.append(md("""## 2. Coefficients, zone by zone

Single-phase zones get Dittus–Boelter. The condensing zone gets **Shah**, which
is a shear-driven (annular) correlation, and we check it against **Chato**,
which is the gravity-driven (stratified) alternative.

> **Provenance.** Shah's constants and Chato's 0.555 are quoted from standard
> usage. They were **not** verified against a primary source in the course
> library. Treat them as starting points.
"""))
C.append(code('''def h_dittus(m, D, fluid, p, h_bulk, cooling=True):
    """Single-phase turbulent, in-tube."""
    st = am.State(fluid, P=p, H=h_bulk)
    Re = 4*m/(PI*D*st.mu)
    Pr = st.cp*st.mu/st.k
    n  = 0.3 if cooling else 0.4
    return 0.023*max(Re,1)**0.8*Pr**n*st.k/D, Re

def h_shah(x, m, D, fluid, p):
    """Shah (1979). Annular / shear-driven in-tube condensation."""
    st_l = am.sat_liquid(fluid, p=p)
    Re_l = 4*m/(PI*D*st_l.mu)                 # all-liquid Reynolds
    Pr_l = st_l.cp*st_l.mu/st_l.k
    h_l  = 0.023*max(Re_l,1)**0.8*Pr_l**0.4*st_l.k/D
    p_r  = p/am.critical(fluid)["p"]
    return h_l*((1-x)**0.8 + 3.8*x**0.76*(1-x)**0.04/p_r**0.38)

def h_chato(dT, D, fluid, p):
    """Chato (1962). Stratified / gravity-driven, low vapour velocity."""
    st_l = am.sat_liquid(fluid, p=p); st_g = am.sat_vapour(fluid, p=p)
    hfg  = st_g.h - st_l.h
    hfg_p = hfg + 0.68*st_l.cp*max(dT, 1e-6)
    return 0.555*((st_l.d*(st_l.d-st_g.d)*9.80665*hfg_p*st_l.k**3)
                  /(st_l.mu*max(dT,1e-6)*D))**0.25

xs = np.linspace(0.02, 0.98, 60)
h_sh = [h_shah(x, m_r, D_i, F, p_cond) for x in xs]
h_ch = h_chato(5.0, D_i, F, p_cond)
print(f"  Shah ranges {min(h_sh):.0f} to {max(h_sh):.0f} W/m2K across quality")
print(f"  Chato (dT = 5 K, stratified)  {h_ch:.0f} W/m2K  - a single number,"
      "\\n  because gravity-driven condensation does not care about quality.")
'''))
C.append(md("## 3. Segment integration\n\nMarch along the condenser in enthalpy steps."))
C.append(code('''h_water_side = 3000.0        # W/m2K, annulus side, taken as given here

def segment_march(N=300, use="shah"):
    """Walk from discharge to subcooled outlet, N equal-enthalpy steps."""
    h_pts = np.linspace(h2, h3, N+1)
    T_w   = T_w_in + dT_w                      # counterflow: water leaves at the hot end
    L_tot, rows = 0.0, []
    for i in range(N):
        hi, ho = h_pts[i], h_pts[i+1]
        h_mid  = 0.5*(hi + ho)
        dQ     = m_r*(hi - ho)
        st     = am.State(F, P=p_cond, H=h_mid)
        T_r    = st.T
        # which zone are we in?
        if h_mid > h_g:   zone, h_i = "desuperheat", h_dittus(m_r, D_i, F, p_cond, h_mid, True)[0]
        elif h_mid > h_f:
            zone = "condense"
            x = (h_mid - h_f)/(h_g - h_f)
            h_i = h_shah(x, m_r, D_i, F, p_cond) if use == "shah" \\
                  else h_chato(max(T_r - (T_w - dT_w/2), 1.0), D_i, F, p_cond)
        else:             zone, h_i = "subcool", h_dittus(m_r, D_i, F, p_cond, h_mid, True)[0]
        U   = 1/(1/h_i + 1/h_water_side)        # thin copper wall neglected
        T_w_out_seg = T_w
        T_w -= dQ/(m_w*4180.0)                  # water cools as we march backwards
        dT1, dT2 = T_r - T_w_out_seg, T_r - T_w
        dTlm = am.lmtd(max(dT1,0.05), max(dT2,0.05))
        dL   = dQ/(U*PI*D_i*dTlm)
        L_tot += dL
        rows.append({"h, kJ/kg": h_mid/1e3, "zone": zone, "T_r, C": am.C(T_r),
                     "T_w, C": am.C(T_w), "h_i, W/m2K": h_i, "U, W/m2K": U,
                     "dT_lm, K": dTlm, "dL, m": dL, "L cumulative, m": L_tot})
    return L_tot, rows

L_seg, rows = segment_march()
by_zone = {}
for r_ in rows: by_zone[r_["zone"]] = by_zone.get(r_["zone"], 0.0) + r_["dL, m"]
print(f"  segment-integrated length  {L_seg:.3f} m\\n")
print(f"{'zone':14s}{'length, m':>11}{'% of length':>13}{'% of duty':>11}")
for z in ("desuperheat","condense","subcool"):
    print(f"{z:14s}{by_zone[z]:11.3f}{100*by_zone[z]/L_seg:13.1f}"
          f"{100*zones[z]/(h2-h3):11.1f}")
'''))
C.append(md("""Compare the two right-hand columns. Desuperheating takes about
10% of the duty but nearer 13% of the length, and subcooling likewise runs long
for its duty, because both are single-phase zones with poor coefficients. The
asymmetry is modest here; it grows sharply if the superheat is larger or the
water-side coefficient is worse.
"""))
C.append(md("## 4. The lazy method, and what it costs"))
C.append(code('''# One mean coefficient, one LMTD across the whole condenser.
h_mean = np.mean([r_["h_i, W/m2K"] for r_ in rows])
U_mean = 1/(1/h_mean + 1/h_water_side)
dT1 = st2.T - (T_w_in + dT_w)                       # hot end
dT2 = (T_cond - dT_sub) - T_w_in                    # cold end
L_lazy = Q_H/(U_mean*PI*D_i*am.lmtd(dT1, dT2))

print(f"  mean h              {h_mean:9.1f} W/m2K")
print(f"  single LMTD         {am.lmtd(dT1, dT2):9.3f} K")
print(f"  lazy length         {L_lazy:9.3f} m")
print(f"  segment-integrated  {L_seg:9.3f} m")
print(f"\\n  error of the lazy method: {100*(L_lazy-L_seg)/L_seg:+.1f}%")
print("  Undersizing a condenser raises the condensing pressure, which raises")
print("  the discharge temperature and cuts the COP. It is not a safe error.")
'''))
C.append(code('''fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.3))
L  = [r_["L cumulative, m"] for r_ in rows]
a1.plot(L, [r_["T_r, C"] for r_ in rows], lw=2.4, label="refrigerant")
a1.plot(L, [r_["T_w, C"] for r_ in rows], lw=2.4, label="water (counterflow)")
for z, col in (("desuperheat", "#FDEBD0"), ("condense", "#EAF2FB"), ("subcool", "#EAF7EF")):
    seg = [r_["L cumulative, m"] for r_ in rows if r_["zone"] == z]
    if seg: a1.axvspan(min(seg), max(seg), color=col, zorder=0)
a1.set_xlabel("length along condenser  (m)"); a1.set_ylabel("temperature  (°C)")
a1.set_title("Three zones, shaded"); a1.legend(fontsize=9)
a2.plot(L, [r_["h_i, W/m2K"] for r_ in rows], lw=2.4, color=am.ORANGE)
a2.axhline(h_mean, ls="--", color=am.MUTED)
a2.text(L[len(L)//2], h_mean*1.06, " the mean the lazy method uses", color=am.MUTED, fontsize=9)
a2.set_yscale("log"); a2.set_xlabel("length along condenser  (m)")
a2.set_ylabel("refrigerant-side h  (W/m²K)")
a2.set_title("An order of magnitude, averaged away")
plt.tight_layout(); plt.show()
'''))
C.append(md("## 5. Shah against Chato, and grid independence"))
C.append(code('''L_chato, _ = segment_march(use="chato")
print(f"  length with Shah  (shear-driven)   {L_seg:.3f} m")
print(f"  length with Chato (gravity-driven) {L_chato:.3f} m"
      f"   ({100*(L_chato-L_seg)/L_seg:+.1f}%)")
print("  Decide which regime you are in BEFORE opening a correlation.\\n")
print(f"{'N':>6}{'length, m':>12}")
for N in (20, 50, 100, 300, 1000):
    print(f"{N:6d}{segment_march(N=N)[0]:12.4f}")
print("  Settles to about 20.2 m, but note it WOBBLES by a few tenths of a")
print("  percent rather than converging smoothly. That is because the zone")
print("  boundaries fall at different places inside a segment as N changes.")
print("  Refining a grid across a discontinuity does not converge cleanly, and")
print("  the honest fix is to put a node ON each boundary.")
'''))
C.append(md("## 6. The deliverable"))
C.append(code('''zone_rows = [{"zone": z, "Q, W": m_r*zones[z], "% of duty": 100*zones[z]/(h2-h3),
              "length, m": by_zone[z], "% of length": 100*by_zone[z]/L_seg}
             for z in ("desuperheat","condense","subcool")]
grid_rows = [{"N segments": N, "length, m": segment_march(N=N)[0]}
             for N in (20, 50, 100, 200, 300, 600, 1000)]

path = am.to_excel("AM5061_D6_Condenser.xlsx",
    {"Zone summary": zone_rows, "Marching profile": rows[::3], "Grid study": grid_rows},
    title="AM5061 D-6 . Condenser of a 10 kW residential heat pump",
    summary=[("Heating duty", Q_H, "W"), ("Refrigerant", F, ""),
             ("Condensing temperature", am.C(T_cond), "C"),
             ("Subcooling", dT_sub, "K"),
             ("Discharge temperature", st2.T_C, "C"),
             ("Refrigerant flow", m_r, "kg/s"), ("Water flow", m_w, "kg/s"),
             ("Length, segment integration", L_seg, "m"),
             ("Length, single mean-h LMTD", L_lazy, "m"),
             ("Error of the lazy method", 100*(L_lazy-L_seg)/L_seg, "%")],
    sources=[("R134a properties", "CoolProp 8.0.0"),
             ("Condensation, annular", "Shah (1979) - QUOTED, not source-verified here"),
             ("Condensation, stratified", "Chato (1962) - QUOTED, not source-verified here"),
             ("Single phase", "Dittus-Boelter, n = 0.3 for cooling"),
             ("Water-side coefficient", "3000 W/m2K, assumed")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The zone table: duty share and length share side by side.
2. The required tube length by segment integration.
3. The same by single mean-h LMTD, and **the error**, with a sentence on
   whether that error is safe or unsafe and why.
4. Shah against Chato, with a statement of which regime you believe you are in.
5. The workbook.

The water-side coefficient here is **assumed**, not computed. Week 9 removes
that assumption and turns this duty into actual hardware.
"""))
build("Week06_Condenser.ipynb", "Week 6 · Heat pump condenser", C)
print("Week06 built")
