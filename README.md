# AM5061 — Design of Thermal and Fluid Systems

Case notebooks for AM5061, Applied Mechanics & Biomedical Engineering,
IIT Madras. Jul–Nov 2026.

Every case runs in **Google Colab**. Nothing needs installing.

| Week | Case | Open |
|---|---|---|
| 1 | 28 kW dairy heat pump | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week01_HeatPump.ipynb) |
| 2 | Chilled-water distribution | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week02_Hydraulics.ipynb) |
| 3 | Chennai cooling tower | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week03_CoolingTower.ipynb) |
| 4 | Steam header insulation | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week04_Insulation.ipynb) |
| 5 | Boiler waterwall tube | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week05_Waterwall.ipynb) |
| 6 | Heat pump condenser | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week06_Condenser.ipynb) |
| 7 | GPU rack heat exchanger | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week07_HeatExchanger.ipynb) |
| 8 | Cement kiln WHR boiler | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week08_WHRBoiler.ipynb) |
| 9 | Shell-and-tube condenser | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week09_ShellAndTube.ipynb) |
| 10 | Bagasse cogeneration | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week10_Cogeneration.ipynb) |
| 11 | Transcritical CO₂ booster | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week11_CO2Booster.ipynb) |
| 12 | Solar absorption chiller | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week12_AbsorptionChiller.ipynb) |
| 13 | ORC system convergence | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week13_ORC.ipynb) |
| 14 | Plant-level audit | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/satyaseshadri/am5061/blob/main/notebooks/Week14_PlantAudit.ipynb) |

**Before you change anything: File → Save a copy in Drive.**

## Guides

Read [Getting started](docs/AM5061_Guide1_GettingStarted.pdf) before Week 1.
There is also an [`am5061.py` reference](docs/AM5061_Guide2_ModuleReference.pdf)
and a [numerical methods guide](docs/AM5061_Guide3_NumericalMethods.pdf).

## How this is built

Notebooks are **generated**, not hand-edited. `build_weekNN.py` is the source;
`nbbuild.py` embeds `am5061.py` into each notebook so every one is
self-contained. Rebuild with:

```
python build_week01.py        # one week
for f in build_week*.py; do python "$f"; done   # all fourteen
```

Verify they still run:

```
for nb in notebooks/Week*.ipynb; do jupyter nbconvert --to notebook --execute "$nb"; done
```

All fourteen execute end to end. Properties come from
[CoolProp](http://coolprop.org) (IAPWS-95 for water, Span & Wagner for CO₂).

## Licence

Teaching material for AM5061. Reuse with attribution.
Third-party figures are **not** included in this repository.
