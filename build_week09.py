"""Week 9 - shell-and-tube condenser: the mechanical design problem."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

You know the **required UA** from Week 6. Now produce a **drawing**: shell
diameter, tube count, pitch, baffle cut and spacing, passes, nozzle sizes.

Deliverable **D-9**: a complete mechanical design sheet for the Case 6
condenser, plus a rating check with real R134a properties.

### Why this week feels different

Weeks 1–8 had a right answer you converged on. This one is a **fixed-point
problem**: you guess geometry, rate it, check the pressure drop, and resize.
There is no formula that goes from duty to hardware. There is only iteration
with judgement in the loop.

> **Provenance.** Kern's correlations and the tube-count formula below are
> quoted from standard usage (Kern 1950; Serth). They were **not** verified
> against a primary source in the course library. Bell–Delaware is more
> accurate and considerably more involved; Kern is what you check a vendor's
> proposal with.
"""))
C.append(md("## 1. The thermal requirement, carried over from Week 6"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()
PI = np.pi

F        = "R134a"
Q        = 10e3            # W    condenser duty
T_cond   = am.K(45)
T_w_in, T_w_out = am.K(30), am.K(40)
p_cond   = am.p_sat(F, T_cond)
dT_lm    = am.lmtd(am.C(T_cond) - am.C(T_w_out), am.C(T_cond) - am.C(T_w_in))

def duty(Q):
    """Water flow and required UA scale linearly with duty."""
    return Q/(4180.0*(T_w_out - T_w_in)), Q/dT_lm

m_w, UA_req = duty(Q)
print(f"  duty          {Q/1e3:8.2f} kW")
print(f"  water flow    {m_w:8.4f} kg/s   ({m_w*3600/1000:.3f} m3/h)")
print(f"  LMTD          {dT_lm:8.3f} K    (condensing, so one end is isothermal)")
print(f"  UA required   {UA_req:8.2f} W/K")
'''))
C.append(md("""## 2. Geometry: TEMA layout and tube count

Triangular (30°) pitch packs more tubes into a shell than square (90°), so it
gives more area per unit shell volume. Square pitch is chosen when the shell
side must be **mechanically cleanable**, which is a fouling decision, not a
thermal one.
"""))
C.append(code('''# Tube size and pass count are DESIGN VARIABLES, not constants. On a small
# duty they are the only things that can rescue the tube velocity.
TUBES = {'1/2 in': (0.01270, 0.01054), '5/8 in': (0.01588, 0.01340),
         '3/4 in': (0.01905, 0.01656)}
d_o, d_i = TUBES['3/4 in']
PR       = 1.25                  # pitch ratio, P_T/d_o
P_T      = PR*d_o
n_passes = 2

# CL: layout constant (0.87 for 30/60 deg, 1.0 for 45/90 deg)
# CTP: tube count constant (0.93 one pass, 0.90 two, 0.85 four)
CL, CTP = 0.87, {1: 0.93, 2: 0.90, 4: 0.85}[n_passes]

def tube_count(D_s, d_o=None, n_passes=None):
    """Kern/Serth tube-count approximation."""
    d_o = d_o or globals()["d_o"]
    ctp = {1: 0.93, 2: 0.90, 4: 0.85, 6: 0.82, 8: 0.80}[n_passes or globals()["n_passes"]]
    return ctp*PI*D_s**2/(4*CL*PR**2*d_o**2)

print(f"  tube {d_o*1e3:.2f} mm OD, {d_i*1e3:.2f} mm ID, {PR} pitch ratio, "
      f"{n_passes} tube passes")
print(f"\\n{'shell D, mm':>13}{'tubes':>8}{'area/m length, m2':>20}")
for D_s in (0.1, 0.15, 0.2, 0.25, 0.30):
    N = tube_count(D_s)
    print(f"{D_s*1e3:13.0f}{N:8.0f}{N*PI*d_o:20.4f}")
'''))
C.append(md("""## 3. Kern's method

Tube side gets Dittus–Boelter. Shell side gets Kern's cross-flow correlation on
an **equivalent diameter** that accounts for the pitch geometry.
"""))
C.append(code('''def shell_side(D_s, B, m_shell, fluid_state, mu_w_ratio=1.0):
    """Kern shell-side coefficient and pressure drop.
    B is baffle spacing; a common rule is 0.2*D_s <= B <= D_s."""
    Cl = P_T - d_o                                   # clearance between tubes
    A_s = D_s*Cl*B/P_T                               # cross-flow area at the shell axis
    G_s = m_shell/A_s
    # equivalent diameter, 30 deg triangular pitch
    D_e = 4*(P_T**2*np.sqrt(3)/4 - PI*d_o**2/8)/(PI*d_o/2)
    Re  = D_e*G_s/fluid_state.mu
    Pr  = fluid_state.cp*fluid_state.mu/fluid_state.k
    h_o = 0.36*Re**0.55*Pr**(1/3)*mu_w_ratio**0.14*fluid_state.k/D_e
    f   = np.exp(0.576 - 0.19*np.log(max(Re, 10.0)))
    return {"A_s, m2": A_s, "G_s, kg/m2s": G_s, "D_e, m": D_e, "Re_shell": Re,
            "h_o, W/m2K": h_o, "f": f}

def tube_side(N_t, m_tube, d_i=None, n_passes=None):
    """Water inside the tubes, Dittus-Boelter, heating so n = 0.4."""
    d_i = d_i or globals()["d_i"]; n_passes = n_passes or globals()["n_passes"]
    st = am.State("Water", P=3e5, T=0.5*(T_w_in + T_w_out))
    n_per_pass = N_t/n_passes
    m_per_tube = m_tube/n_per_pass
    Re = 4*m_per_tube/(PI*d_i*st.mu)
    Pr = st.cp*st.mu/st.k
    h_i = 0.023*max(Re,1)**0.8*Pr**0.4*st.k/d_i
    v   = m_per_tube/(st.d*PI*d_i**2/4)
    return {"Re_tube": Re, "h_i, W/m2K": h_i, "v_tube, m/s": v, "_st": st}
print("  correlations defined")
'''))
C.append(md("""## 4. The design iteration

Guess a shell diameter, compute what it delivers, and compare with what is
needed. This is a **fixed-point** loop, and watching it converge is the point.
"""))
C.append(code('''R_f_i, R_f_o = 1.76e-4, 1.76e-4     # m2K/W fouling, water and refrigerant
k_cu = 385.0

def rate(D_s, B_frac=0.4, tube="3/4 in", n_pass=2, Q=Q):
    """Rate a candidate geometry at a given duty."""
    m_w, UA_req = duty(Q)
    d_o, d_i = TUBES[tube]
    P_T = PR*d_o
    N_t = tube_count(D_s, d_o, n_pass)
    B   = B_frac*D_s
    ts  = tube_side(N_t, m_w, d_i, n_pass)
    # shell side carries condensing R134a; use the Shah value from Week 6 as
    # a representative mean rather than re-integrating here
    st_l = am.sat_liquid(F, p=p_cond)
    ss   = shell_side(D_s, B, Q/((am.sat_vapour(F,p=p_cond).h - st_l.h)), st_l)
    h_o_cond = 1800.0                # W/m2K, condensing on a horizontal bundle
    U_o = 1/(d_o/(d_i*ts["h_i, W/m2K"]) + R_f_i*d_o/d_i
             + d_o*np.log(d_o/d_i)/(2*k_cu) + R_f_o + 1/h_o_cond)
    A_req = UA_req/U_o
    L_req = A_req/(N_t*PI*d_o)
    N_b   = max(int(L_req/B) - 1, 1)
    dp_s  = ss["f"]*ss["G_s, kg/m2s"]**2*(N_b+1)*D_s/(2*st_l.d*ss["D_e, m"])
    dp_t  = (0.023*max(ts["Re_tube"],1)**-0.2)*4*(L_req*n_pass/d_i) \\
            *0.5*ts["_st"].d*ts["v_tube, m/s"]**2
    return {"Q, kW": Q/1e3, "D_s, mm": D_s*1e3, "tube": tube, "passes": n_pass, "tubes": N_t, "baffle spacing, mm": B*1e3,
            "baffles": N_b, "U_o, W/m2K": U_o, "A required, m2": A_req,
            "tube length, m": L_req, "L/D_s": L_req/D_s,
            "v_tube, m/s": ts["v_tube, m/s"], "Re_tube": ts["Re_tube"],
            "h_i, W/m2K": ts["h_i, W/m2K"],
            "dp_shell, kPa": dp_s/1e3, "dp_tube, kPa": dp_t/1e3}

print(f"{'D_s mm':>8}{'tubes':>7}{'U_o':>8}{'L, m':>8}{'L/D_s':>8}"
      f"{'v_t m/s':>9}{'dp_t kPa':>10}")
for D_s in (0.10, 0.125, 0.15, 0.20, 0.25, 0.30):
    r_ = rate(D_s, tube="3/4 in", n_pass=2)
    print(f"{r_['D_s, mm']:8.0f}{r_['tubes']:7.0f}{r_['U_o, W/m2K']:8.1f}"
          f"{r_['tube length, m']:8.2f}{r_['L/D_s']:8.2f}"
          f"{r_['v_tube, m/s']:9.3f}{r_['dp_tube, kPa']:10.2f}")
'''))
C.append(md("""### Reading that table

Three constraints fight each other:

- **L/D_s** should sit roughly between **4 and 8**. Too long and the shell
  sags and cannot be pulled for cleaning; too short and the nozzles and heads
  dominate the cost.
- **Tube velocity** should be about **1 to 2.5 m/s** for water. Below that,
  fouling accelerates. Above it, erosion does.
- **Pressure drop** must fit the pump you have.

A small shell gives high velocity and a long, thin exchanger. A large shell
gives the opposite. The design is the compromise.
"""))
C.append(code('''def feasible(r_):
    return (4 <= r_["L/D_s"] <= 8 and 1.0 <= r_["v_tube, m/s"] <= 2.5)

cands = [rate(D, tube=t, n_pass=n)
         for D in np.arange(0.06, 0.32, 0.01)
         for t in TUBES for n in (2, 4, 6, 8)]
ok = [c for c in cands if feasible(c)]
print(f"  {len(ok)} of {len(cands)} candidate shells satisfy BOTH the L/D_s and"
      f" velocity windows")
if ok:
    best = min(ok, key=lambda c: c["D_s, mm"])
    print(f"\\n  smallest feasible: {best['D_s, mm']:.0f} mm shell, "
          f"{best['tube']} tubes, {best['passes']} passes")
    for k, v in best.items(): print(f"    {k:22s} {v:10.3f}")
else:
    print("  none - the windows do not overlap. That is a REAL RESULT, not a")
    print("  failure of the method. See the next section.")
'''))
C.append(md("""### At what duty does a shell-and-tube start to make sense?

The two windows fight each other. High tube velocity wants **few** tubes; a
sensible L/D_s wants **many**. On a small duty there is no overlap, and no
choice of tube size or pass count rescues it — which is why a 10 kW condenser
is a **brazed-plate or coaxial** unit in practice.

Scale the duty and the windows separate.
"""))
C.append(code('''duty_rows = []
for Q_kW in (10, 25, 50, 100, 250, 500, 1000, 2000):
    cs = [rate(D, tube=t, n_pass=n, Q=Q_kW*1e3)
          for D in np.arange(0.06, 1.21, 0.02) for t in TUBES for n in (2,4,6,8)]
    good = [c for c in cs if feasible(c)]
    duty_rows.append({"Q, kW": Q_kW, "feasible options": len(good),
                      "smallest shell, mm": min((c["D_s, mm"] for c in good), default=None)})
    print(f"  {Q_kW:6d} kW -> {len(good):4d} feasible designs"
          + (f", smallest shell {min(c['D_s, mm'] for c in good):.0f} mm" if good else ""))
Q_ok = next((r_["Q, kW"] for r_ in duty_rows if r_["feasible options"] > 0), None)
print(f"\\n  shell-and-tube becomes viable at roughly {Q_ok} kW and above.")
print("  Below that, specify a different exchanger type. That IS the design")
print("  decision, and it is the one worth defending in a report.")
'''))
C.append(md("""## 5. The design sheet, at a duty where the geometry works"""))
C.append(code('''Q_DESIGN = (Q_ok or 500)*1e3
cands_d = [rate(D, tube=t, n_pass=n, Q=Q_DESIGN)
           for D in np.arange(0.06, 1.21, 0.01) for t in TUBES for n in (2,4,6,8)]
ok_d = [c for c in cands_d if feasible(c)]
sel = min(ok_d, key=lambda c: c["D_s, mm"]) if ok_d else cands_d[0]
m_w_d, UA_d = duty(Q_DESIGN)
print(f"  designing at {Q_DESIGN/1e3:.0f} kW: {len(ok_d)} feasible options")
for k, v in sel.items():
    print(f"    {k:22s} {v if isinstance(v,str) else round(float(v),3)}")
'''))
C.append(code('''fig, (a1,a2) = plt.subplots(1,2, figsize=(11.8,4.2))
line = [c for c in cands_d if c["tube"] == "3/4 in" and c["passes"] == 2]
D = [c["D_s, mm"] for c in line]
a1.plot(D, [c["L/D_s"] for c in line], lw=2.4, color=am.NAVY, label="3/4 in, 2 pass")
a1.axhspan(4, 8, color="#EAF7EF", zorder=0); a1.text(D[2], 8.4, "acceptable L/D_s", fontsize=9, color=am.MUTED)
a1.set_xlabel("shell diameter  (mm)"); a1.set_ylabel("L / D_s"); a1.set_ylim(0, 25)
a1.set_title("Slenderness")
for t in TUBES:
    for n in (2, 8):
        ln = [c for c in cands_d if c["tube"] == t and c["passes"] == n]
        a2.plot([c["D_s, mm"] for c in ln], [c["v_tube, m/s"] for c in ln],
                lw=2.0, label=f"{t}, {n} pass")
a2.legend(fontsize=8)
a2.axhspan(1.0, 2.5, color="#EAF7EF", zorder=0); a2.text(D[2], 2.6, "acceptable velocity", fontsize=9, color=am.MUTED)
a2.set_xlabel("shell diameter  (mm)"); a2.set_ylabel("tube velocity  (m/s)")
a2.set_title("Fouling below, erosion above")
plt.tight_layout(); plt.show()
'''))
C.append(md("## 5. Nozzles"))
C.append(code('''def nozzle(m, rho, v_target=2.0):
    d = np.sqrt(4*m/(rho*PI*v_target))
    return d, m/(rho*PI*d**2/4)

st_w = am.State("Water", P=3e5, T=T_w_in)
d_wn, v_wn = nozzle(m_w_d, st_w.d, 2.0)
m_r = Q_DESIGN/(am.State(F,P=p_cond,T=am.K(60)).h - am.sat_liquid(F,p=p_cond).h)
st_v = am.sat_vapour(F, p=p_cond)
d_vn, v_vn = nozzle(m_r, st_v.d, 15.0)      # vapour nozzles run much faster
print(f"  water nozzle     {d_wn*1e3:6.1f} mm at {v_wn:.2f} m/s")
print(f"  vapour nozzle    {d_vn*1e3:6.1f} mm at {v_vn:.2f} m/s")
print("  Round both UP to the next standard pipe size, then re-check velocity.")
'''))
C.append(md("## 6. The design sheet"))
C.append(code('''sheet = [("Duty", Q_DESIGN, "W"), ("Refrigerant", F, ""),
         ("Condensing temperature", am.C(T_cond), "C"),
         ("Water in / out", f"{am.C(T_w_in):.0f} / {am.C(T_w_out):.0f}", "C"),
         ("Water flow", m_w_d, "kg/s"), ("LMTD", dT_lm, "K"),
         ("UA required", UA_d, "W/K"),
         ("Tube size", sel["tube"], ""),
         ("TEMA layout", "30 deg triangular", ""),
         ("Tube OD / ID", f"{TUBES[sel['tube']][0]*1e3:.2f} / "
                          f"{TUBES[sel['tube']][1]*1e3:.2f}", "mm"),
         ("Pitch ratio", PR, "-"), ("Tube passes", sel["passes"], "-"),
         ("Shell diameter", sel["D_s, mm"], "mm"),
         ("Tube count", sel["tubes"], "-"),
         ("Tube length", sel["tube length, m"], "m"),
         ("Baffle spacing", sel["baffle spacing, mm"], "mm"),
         ("Baffle cut", 25.0, "%"), ("Baffles", sel["baffles"], "-"),
         ("Overall U (outside)", sel["U_o, W/m2K"], "W/m2K"),
         ("Tube velocity", sel["v_tube, m/s"], "m/s"),
         ("Tube-side dp", sel["dp_tube, kPa"], "kPa"),
         ("Water nozzle", d_wn*1e3, "mm"), ("Vapour nozzle", d_vn*1e3, "mm")]

path = am.to_excel("AM5061_D9_ShellAndTube.xlsx",
    {"Shell study at design duty": cands_d[::4], "Duty study": duty_rows},
    title="AM5061 D-9 . Shell-and-tube condenser mechanical design",
    summary=sheet,
    sources=[("R134a and water properties", "CoolProp 8.0.0"),
             ("Shell side", "Kern's method - QUOTED from standard usage, not source-verified"),
             ("Tube count", "Kern/Serth approximation, CTP/CL constants"),
             ("Fouling", "1.76e-4 m2K/W both sides, TEMA typical"),
             ("Thermal duty", "carried from AM5061 D-6, Week 6")])
print("written:", path)
for k, v, u in sheet: print(f"    {k:26s} {v if isinstance(v,str) else round(v,3)} {u}")
'''))
C.append(md("""## What to hand in

1. The complete design sheet: shell diameter, tube count, length, passes,
   pitch, baffle spacing and cut, nozzle sizes.
2. The shell-diameter study, showing **why** you chose that shell and not a
   neighbouring one — which constraint bound.
3. A rating check: does your geometry actually deliver the required UA?
4. The workbook.

**One paragraph:** Kern's method is approximate and Bell–Delaware is better.
Where would you expect Kern to be most wrong on *this* exchanger, and would
that error be conservative or not?
"""))
build("Week09_ShellAndTube.ipynb", "Week 9 · Shell-and-tube condenser", C)
print("Week09 built")
