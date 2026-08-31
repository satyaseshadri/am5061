"""Week 5 - bagasse boiler waterwall, two-phase flow and boiling."""
from nbbuild import md, code, build
C = []
C.append(md("""---
## The case

A waterwall tube in a **20 TPH bagasse-fired boiler**. Radiant heat arrives
from **one side only**, so the crown of the tube runs hotter than the mean. The
tube is SA210 carbon steel and it fails above about **450 °C**.

Deliverable **D-5**: find the peak crown metal temperature and its elevation.
Then raise the internal deposit thickness until the crown passes 450 °C, and
report the thickness that does it.

### The design knob

`t_scale` — internal magnetite deposit. Everything else is fixed by the boiler.
This is a **water-chemistry** question dressed as a heat transfer one, and that
is the point of the case.

> Read the boiling and condensation module before this. Chen, Forster–Zuber,
> Rouhani–Axelsson and Müller-Steinhagen & Heck all appear here without
> re-derivation.
"""))
C.append(md("## 1. Saturation properties, and the correlations"))
C.append(code('''import am5061 as am
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq
am.style_plots()

G_N, PI = 9.80665, np.pi

def sat_props(p):
    """Everything the two-phase correlations need, at one pressure."""
    T = PropsSI('T','P',p,'Q',0,'Water')
    return {"p": p, "T_sat": T,
            "rho_l": PropsSI('D','P',p,'Q',0,'Water'),
            "rho_g": PropsSI('D','P',p,'Q',1,'Water'),
            "h_fg":  PropsSI('H','P',p,'Q',1,'Water') - PropsSI('H','P',p,'Q',0,'Water'),
            "mu_l":  PropsSI('V','P',p,'Q',0,'Water'),
            "mu_g":  PropsSI('V','P',p,'Q',1,'Water'),
            "k_l":   PropsSI('L','P',p,'Q',0,'Water'),
            "cp_l":  PropsSI('C','P',p,'Q',0,'Water'),
            "sigma": PropsSI('I','P',p,'Q',0,'Water'),
            # slope of the saturation line, needed by Forster-Zuber
            "dpdT":  PropsSI('P','T',T+0.5,'Q',0,'Water')
                     - PropsSI('P','T',T-0.5,'Q',0,'Water')}

s45 = sat_props(45e5)
print("  Saturated water at 45 bar (drum pressure):")
for k, v in s45.items(): print(f"    {k:8s} {v:14.6g}")
print(f"\\n    density ratio rho_l/rho_g = {s45['rho_l']/s45['rho_g']:.2f}")
'''))
C.append(code('''# ---- the correlation set, exactly as in the module -------------------
def f_fanning(Re):                      # Blasius, Fanning
    return 16/max(Re,1) if Re < 2000 else 0.079*Re**-0.25

def martinelli(x, s):                   # X_tt, both phases turbulent
    if x <= 0: return 1e10
    return ((1-x)/x)**0.9*(s["rho_g"]/s["rho_l"])**0.5*(s["mu_l"]/s["mu_g"])**0.1

def chen_F(x, s):                       # convective enhancement
    inv = 1/martinelli(x, s)
    return 1.0 if inv <= 0.1 else 2.35*(inv + 0.213)**0.736

def h_liquid(x, s, G, D):               # Dittus-Boelter on the liquid fraction
    Re = G*(1-x)*D/s["mu_l"]; Pr = s["cp_l"]*s["mu_l"]/s["k_l"]
    return 0.023*max(Re,1)**0.8*Pr**0.4*s["k_l"]/D

def chen_S(x, s, G, D, F):              # nucleate suppression
    Re_tp = G*(1-x)*D/s["mu_l"]*F**1.25
    return 1/(1 + 2.53e-6*max(Re_tp,0)**1.17)

def h_forster_zuber(dT_sat, s):         # pool nucleate boiling
    dT = max(dT_sat, 1e-6); dP = s["dpdT"]*dT
    Cc = 0.00122*(s["k_l"]**0.79*s["cp_l"]**0.45*s["rho_l"]**0.49) \\
         /(s["sigma"]**0.5*s["mu_l"]**0.29*s["h_fg"]**0.24*s["rho_g"]**0.24)
    return Cc*dT**0.24*dP**0.75

def void_homogeneous(x, s):
    return 0.0 if x <= 0 else 1/(1 + (1-x)/x*(s["rho_g"]/s["rho_l"]))
def void_zivi(x, s):
    return 0.0 if x <= 0 else 1/(1 + (1-x)/x*(s["rho_g"]/s["rho_l"])**(2/3))
def void_rouhani(x, s, G):
    if x <= 0: return 0.0
    t1 = (1 + 0.12*(1-x))*(x/s["rho_g"] + (1-x)/s["rho_l"])
    t2 = 1.18*(1-x)*(G_N*s["sigma"]*(s["rho_l"]-s["rho_g"]))**0.25/(G*s["rho_l"]**0.5)
    return (x/s["rho_g"])/(t1 + t2)

def dpdz_frictional(x, s, G, D):
    """Mueller-Steinhagen & Heck. VALIDITY: fitted on HORIZONTAL tubes with
    REFRIGERANTS. Using it on a vertical steam waterwall is an extrapolation.
    It is the best simple method available and it is still an extrapolation."""
    a = f_fanning(G*D/s["mu_l"])*2*G**2/(D*s["rho_l"])
    b = f_fanning(G*D/s["mu_g"])*2*G**2/(D*s["rho_g"])
    return (a + 2*(b-a)*x)*(1-x)**(1/3) + b*x**3
print("  correlations defined")
'''))
C.append(md("""## 2. The tube

Quality marches up on the energy balance. At each station Chen's superposition
gives the two-phase coefficient — and it is **implicit**, because the nucleate
term needs the wall superheat, which needs the coefficient. One root-find per
station closes it.
"""))
C.append(code('''def waterwall(N=60, p_drum=45e5, D_o=0.0635, t_wall=0.005, L=12.0, G=400.0,
              k_steel=45.0, q_peak=300e3, z_peak=4.0, z_width=3.5,
              peak_factor=2.0, t_scale=0.0, k_scale=1.0):
    s = sat_props(p_drum)
    D_i = D_o - 2*t_wall
    A_flow = PI*D_i**2/4
    m_flow = G*A_flow
    dz = L/N
    z = (np.arange(N) + 0.5)*dz

    q_o = q_peak*np.exp(-((z - z_peak)/z_width)**2)      # incident, projected width
    # Radiant flux lands on the projected width D_o. Spread over the inside
    # perimeter that is a mean; the crown carries peak_factor times it.
    q_i = q_o*D_o/(PI*D_i)*peak_factor

    x   = np.zeros(N); T_wo = np.zeros(N); h_tp = np.zeros(N)
    dpf = np.zeros(N); dpg  = np.zeros(N); a_r = np.zeros(N)

    for i in range(N):
        x[i] = (q_o[0]*D_o*(dz/2)/(m_flow*s["h_fg"]) if i == 0 else
                x[i-1] + (q_o[i-1]+q_o[i])/2*D_o*dz/(m_flow*s["h_fg"]))
        F  = chen_F(x[i], s)
        S  = chen_S(x[i], s, G, D_i, F)
        hl = h_liquid(x[i], s, G, D_i)
        # implicit: h_tp = F*h_l + S*h_pool(q_i/h_tp)
        h_tp[i] = brentq(lambda h: F*hl + S*h_forster_zuber(q_i[i]/h, s) - h, 1e2, 5e6)
        dT_film = q_i[i]/h_tp[i]
        T_wi = s["T_sat"] + dT_film
        T_wo[i] = T_wi + q_i[i]*t_scale/k_scale + q_o[i]*t_wall/k_steel
        a_r[i]  = void_rouhani(x[i], s, G)
        dpf[i]  = dpdz_frictional(x[i], s, G, D_i)
        dpg[i]  = (a_r[i]*s["rho_g"] + (1-a_r[i])*s["rho_l"])*G_N

    x_out = x[-1] + q_o[-1]*D_o*dz/2/(m_flow*s["h_fg"])
    return {"t_scale, mm": t_scale*1e3,
            "circulation ratio": 1/max(x_out, 1e-9), "x_out": x_out,
            "T_sat, C": s["T_sat"]-273.15,
            "T_metal_max, C": T_wo.max()-273.15,
            "z of peak, m": float(z[int(np.argmax(T_wo))]),
            "dp_friction, Pa": dpf.sum()*dz, "dp_gravity, Pa": dpg.sum()*dz,
            "_z": z, "_x": x, "_T_wo": T_wo, "_h_tp": h_tp, "_q_i": q_i,
            "_alpha": a_r, "_s": s, "_D_i": D_i, "_G": G}

r = waterwall()
for k, v in r.items():
    if not k.startswith("_"): print(f"  {k:20s} {v:12.4f}")
'''))
C.append(md("""> **Check three things before you believe any of it.**
>
> 1. The circulation ratio must land between about **8 and 20**. It is 13.47.
> 2. The **gravitational** term must dominate the pressure drop. It does, by
>    about fifty to one — the friction term is noise on a vertical riser.
> 3. The three void-fraction correlations must order themselves
>    **homogeneous > Rouhani > Zivi** at low quality.
"""))
C.append(code('''s, G, D_i = r["_s"], r["_G"], r["_D_i"]
print(f"  dp_gravity / dp_friction = {r['dp_gravity, Pa']/r['dp_friction, Pa']:.1f}")
print(f"\\n{'x':>7}{'homogeneous':>14}{'Rouhani':>10}{'Zivi':>9}   ordering")
for x in (0.01, 0.02, 0.05, 0.10, 0.30):
    ah, ar, az = void_homogeneous(x,s), void_rouhani(x,s,G), void_zivi(x,s)
    ok = "OK" if ah > ar > az else "*** WRONG ***"
    print(f"{x:7.2f}{ah:14.4f}{ar:10.4f}{az:9.4f}   {ok}")
print("\\n  At 5% quality the flow is already about 99% vapour BY AREA.")
'''))
C.append(md("## 3. Up the tube"))
C.append(code('''fig, axs = plt.subplots(1, 3, figsize=(13.2, 4.2))
axs[0].plot(r["_q_i"]/1e3, r["_z"], color=am.ORANGE, lw=2.4)
axs[0].set_xlabel("crown inside flux  (kW/m²)"); axs[0].set_ylabel("elevation  (m)")
axs[0].set_title("Radiant flux profile")
axs[1].plot(r["_x"], r["_z"], color=am.NAVY, lw=2.4, label="quality x")
axs[1].plot(r["_alpha"], r["_z"], color=am.BLUE, lw=2.0, ls="--",
            label="void fraction α (Rouhani)")
axs[1].set_xlabel("–"); axs[1].set_title("Quality and void"); axs[1].legend(fontsize=9)
axs[2].plot(r["_T_wo"]-273.15, r["_z"], color=am.ORANGE, lw=2.4, label="crown metal")
axs[2].axvline(r["_s"]["T_sat"]-273.15, color=am.MUTED, ls=":", label="T_sat")
axs[2].axvline(450, color="#B03A2E", lw=1.8, ls="--", label="450 °C limit")
axs[2].plot(r["T_metal_max, C"], r["z of peak, m"], "o", ms=9, color=am.NAVY, zorder=5)
axs[2].set_xlabel("temperature  (°C)"); axs[2].set_title("Crown metal temperature")
axs[2].legend(fontsize=8.5)
plt.tight_layout(); plt.show()
print(f"  peak crown metal {r['T_metal_max, C']:.1f} C at z = {r['z of peak, m']:.2f} m")
print(f"  the flux peaks at 4.0 m - the metal peak sits slightly ABOVE it,")
print(f"  because quality keeps rising and the coefficient keeps changing.")
'''))
C.append(md("""## 4. The design question: how much deposit is fatal?

Deposit adds a resistance **inside** the tube, right where the flux is highest.
It does not change the flow or the quality at all. It simply lifts the whole
metal-temperature curve.
"""))
C.append(code('''rows = []
for ts in np.arange(0.0, 1.01e-3, 0.05e-3):
    q = waterwall(t_scale=float(ts))
    rows.append({k: v for k, v in q.items() if not k.startswith("_")})

print(f"{'t_scale, mm':>12}{'T_metal_max, C':>16}{'margin to 450':>15}")
for row in rows[::2]:
    print(f"{row['t_scale, mm']:12.2f}{row['T_metal_max, C']:16.1f}"
          f"{450-row['T_metal_max, C']:15.1f}")

t_fail = brentq(lambda ts: waterwall(t_scale=ts)["T_metal_max, C"] - 450.0, 0.0, 2e-3)
print(f"\\n  The crown reaches 450 C at a deposit thickness of "
      f"{t_fail*1e3:.3f} mm.")
print("  That is thinner than a sheet of paper.")
'''))
C.append(code('''fig, ax = plt.subplots()
ax.plot([r_["t_scale, mm"] for r_ in rows], [r_["T_metal_max, C"] for r_ in rows],
        "o-", color=am.ORANGE, lw=2.4, ms=5)
ax.axhline(450, color="#B03A2E", ls="--", lw=1.8)
ax.axvline(t_fail*1e3, color=am.MUTED, ls=":", lw=1.6)
ax.text(t_fail*1e3, 300, f"  {t_fail*1e3:.2f} mm", color=am.MUTED, fontsize=10)
ax.text(0.02, 455, "SA210 limit, 450 °C", color="#B03A2E", fontsize=9)
ax.set_xlabel("internal deposit thickness  (mm)")
ax.set_ylabel("peak crown metal temperature  (°C)")
ax.set_title("Water chemistry is a heat transfer design variable")
plt.tight_layout(); plt.show()
'''))
C.append(md("## 5. The deliverable"))
C.append(code('''prof = [{"z, m": float(z), "x": float(x), "alpha_rouhani": float(a),
         "q_i, kW/m2": float(q/1e3), "T_crown, C": float(T-273.15)}
        for z, x, a, q, T in zip(r["_z"], r["_x"], r["_alpha"], r["_q_i"], r["_T_wo"])]

path = am.to_excel("AM5061_D5_Waterwall.xlsx",
    {"Deposit sweep": rows, "Tube profile (clean)": prof},
    title="AM5061 D-5 . 20 TPH bagasse boiler waterwall",
    summary=[("Drum pressure", 45e5, "Pa"),
             ("Saturation temperature", r["T_sat, C"], "C"),
             ("Mass flux", 400.0, "kg/m2.s"),
             ("Peak incident flux", 300e3, "W/m2"),
             ("Circulation ratio", r["circulation ratio"], "-"),
             ("Peak crown metal, clean", r["T_metal_max, C"], "C"),
             ("Elevation of peak", r["z of peak, m"], "m"),
             ("Deposit thickness reaching 450 C", t_fail*1e3, "mm"),
             ("dp gravity", r["dp_gravity, Pa"], "Pa"),
             ("dp friction", r["dp_friction, Pa"], "Pa")],
    sources=[("Water properties", "CoolProp, IAPWS-95"),
             ("Flow boiling", "Chen superposition; Forster-Zuber pool term"),
             ("Void fraction", "Rouhani & Axelsson drift flux"),
             ("Pressure drop", "Mueller-Steinhagen & Heck, via Ould Didi et al. 2002 "
                               "- fitted on HORIZONTAL refrigerant flow, extrapolated here"),
             ("Tube and flux data", "AM5061 brief D-5")])
print("written:", path)
'''))
C.append(md("""## What to hand in

1. The peak crown metal temperature and its elevation, clean.
2. Why the metal peak does **not** sit exactly at the flux peak.
3. The deposit thickness that reaches 450 °C, and what that implies for boiler
   water chemistry and blowdown policy.
4. The three checks in section 2, with your numbers.
5. The workbook.

**State the extrapolation.** Müller-Steinhagen & Heck was fitted on horizontal
tubes carrying refrigerants. You are applying it to a vertical steam riser.
That is defensible and it must be declared. Marks are lost for quoting a
pressure drop as though it were measured.
"""))
build("Week05_Waterwall.ipynb", "Week 5 · Boiler waterwall tube", C)
print("Week05 built")
