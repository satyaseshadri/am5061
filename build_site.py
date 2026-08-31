"""Build the static site for courses.venturekraft.in (Cloudflare Pages).

Colab opens notebooks straight from GitHub, so every badge points at the repo
rather than at Drive. That is what removes the sharing problem: nothing here
depends on a Drive permission.
"""
import pathlib, html

GH = "https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks"
RAW = "https://github.com/satyaseshadri/am5061/blob/main/notebooks"

WEEKS = [
 (1,  "The 28 kW dairy pasteurisation heat pump", "Week01_HeatPump",
      "State points, COP, mass flow. Where the whole course starts."),
 (2,  "Chilled-water distribution, 500 TR campus plant", "Week02_Hydraulics",
      "Pump curve against system curve. Throttle or slow down?"),
 (3,  "Cooling tower, Chennai data centre", "Week03_CoolingTower",
      "Wet bulb, Merkel, and whether the setpoint is buildable at all."),
 (4,  "Steam header insulation, Tiruppur mill", "Week04_Insulation",
      "Thickness, surface temperature, and the critical radius."),
 (5,  "Waterwall tube, 20 TPH bagasse boiler", "Week05_Waterwall",
      "Two-phase flow, Chen, and the deposit thickness that kills a tube."),
 (6,  "Condenser of a 10 kW heat pump", "Week06_Condenser",
      "Three zones, three coefficients. What averaging them costs you."),
 (7,  "Liquid cooling, 50 kW GPU rack", "Week07_HeatExchanger",
      "Discretised counter-flow. How many segments are enough?"),
 (8,  "Waste-heat recovery boiler, cement kiln", "Week08_WHRBoiler",
      "Effectiveness-NTU, and why phase change makes life easy."),
 (9,  "Shell-and-tube condenser", "Week09_ShellAndTube",
      "From duty to a drawing. Design as a fixed-point problem."),
 (10, "Bagasse cogeneration, 3500 TCD sugar mill", "Week10_Cogeneration",
      "Steam balance, export power, and the Stodola ellipse."),
 (11, "Transcritical CO2 booster", "Week11_CO2Booster",
      "No condenser. Find the optimum gas-cooler pressure."),
 (12, "Solar LiBr absorption chiller", "Week12_AbsorptionChiller",
      "COP 0.8, and why anyone would build it anyway."),
 (13, "ORC on cement kiln waste heat", "Week13_ORC",
      "How a design code converges. And how it lies to you."),
 (14, "Plant-level audit", "Week14_PlantAudit",
      "Sankey, exergy, rupees per kWh, kilograms of CO2."),
]

GUIDES = [
 ("Getting started with Colab and Python", "AM5061_Guide1_GettingStarted.pdf",
  "Read this before Week 1. Fifteen minutes."),
 ("am5061.py reference", "AM5061_Guide2_ModuleReference.pdf",
  "Every class and function in the shared module."),
 ("Numerical methods for thermal design", "AM5061_Guide3_NumericalMethods.pdf",
  "Which solver to reach for, and how to tell when it has lied to you."),
]

CSS = """
:root{--navy:#1F3864;--orange:#ED7D31;--muted:#59626E;--line:#e6eaf0;--bg:#fff;--panel:#F8FAFC}
@media(prefers-color-scheme:dark){:root{--navy:#8FB3E8;--muted:#9AA4B2;--line:#2a2f38;--bg:#14171c;--panel:#1b1f26}}
*{box-sizing:border-box}
body{margin:0;font-family:Calibri,Carlito,system-ui,-apple-system,sans-serif;
  color:#1a1a1a;background:var(--bg);line-height:1.55}
@media(prefers-color-scheme:dark){body{color:#e7eaee}}
.wrap{max-width:980px;margin:0 auto;padding:26px 18px 60px}
header{border-bottom:2px solid var(--navy);padding-bottom:14px;margin-bottom:22px}
.eyebrow{color:var(--orange);font-weight:700;font-size:12px;letter-spacing:.12em}
h1{color:var(--navy);font-size:30px;margin:6px 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:15px}
h2{color:var(--navy);font-size:20px;margin:34px 0 10px}
.note{background:#FDF3EC;border-left:4px solid var(--orange);padding:13px 15px;margin:18px 0;font-size:15px}
@media(prefers-color-scheme:dark){.note{background:#2a2119}}
.grid{display:grid;gap:11px}
.card{border:1px solid var(--line);border-radius:7px;padding:13px 15px;background:var(--panel);
  display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.num{font-weight:700;color:var(--navy);font-size:22px;min-width:34px}
.body{flex:1 1 320px;min-width:0}
.t{font-weight:600;color:var(--navy)}
.d{color:var(--muted);font-size:14px}
a.btn{display:inline-block;background:var(--orange);color:#fff;text-decoration:none;
  padding:8px 15px;border-radius:5px;font-size:14px;white-space:nowrap;font-weight:600}
a.btn:hover{background:#d86d24}
a.ghost{background:transparent;color:var(--navy);border:1px solid var(--line);font-weight:600}
footer{margin-top:46px;padding-top:14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px}
code{background:var(--panel);padding:2px 5px;border-radius:3px;font-size:13px}
"""

def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<header><div class="eyebrow">AM5061 &middot; DESIGN OF THERMAL AND FLUID SYSTEMS</div>
<h1>{html.escape(title)}</h1>
<div class="sub">Applied Mechanics &amp; Biomedical Engineering &middot; IIT Madras &middot; Jul&ndash;Nov 2026</div>
</header>
{body}
<footer>Prof. Satyanarayanan Seshadri &middot; Applied Mechanics, IIT Madras.
Notebooks open in Google Colab; nothing needs installing.</footer>
</div></body></html>"""

cards = "\n".join(
  f'<div class="card"><div class="num">{n}</div>'
  f'<div class="body"><div class="t">{html.escape(t)}</div>'
  f'<div class="d">{html.escape(d)}</div></div>'
  f'<a class="btn" href="{GH}/{s}.ipynb" target="_blank" rel="noopener">Open in Colab</a>'
  f'<a class="btn ghost" href="{RAW}/{s}.ipynb" target="_blank" rel="noopener">View source</a></div>'
  for n, t, s, d in WEEKS)

guides = "\n".join(
  f'<div class="card"><div class="body"><div class="t">{html.escape(t)}</div>'
  f'<div class="d">{html.escape(d)}</div></div>'
  f'<a class="btn ghost" href="docs/{f}" target="_blank" rel="noopener">Read (PDF)</a></div>'
  for t, f, d in GUIDES)

body = f"""
<div class="note"><b>New here? Read <a href="docs/AM5061_Guide1_GettingStarted.pdf">Getting started</a> first.</b><br>
Every case runs in your browser through Google Colab. Sign in with your
<code>@smail.iitm.ac.in</code> account. Nothing to install &mdash; no Python, no Anaconda.
<br><br><b>Before you change a notebook: File &rarr; Save a copy in Drive.</b>
The originals are read-only, so work on your own copy.</div>

<h2>The fourteen cases</h2>
<div class="grid">{cards}</div>

<h2>Guides</h2>
<div class="grid">{guides}</div>

<h2>Submitting</h2>
<div class="note">Each deliverable has its own upload form. Sign in with your
IIT Madras Google account so your submission is recorded against your roll number.
<br><br><i>Form links are added here once the forms are created.</i></div>
"""

out = pathlib.Path(__file__).parent / "site"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page("Course notebooks", body), encoding="utf-8")
print("site/index.html written,", len(WEEKS), "cases,", len(GUIDES), "guides")
