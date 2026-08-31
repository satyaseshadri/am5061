"""Build AM5061 Colab notebooks.

One source of truth: am5061.py sits next to this file, and each notebook gets
it embedded in a %%writefile cell. That makes every notebook SELF-CONTAINED -
a student opens one Colab link and nothing else has to be fetched, mounted or
installed by hand. Regenerate the notebooks whenever am5061.py changes.
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code(text, collapsed=False):
    meta = {"cellView": "form"} if collapsed else {}
    return {"cell_type": "code", "execution_count": None, "metadata": meta,
            "outputs": [], "source": text.splitlines(True)}


def setup_cells(week_title):
    """The two cells every notebook opens with: install, then the library."""
    lib = (HERE / "am5061.py").read_text()
    return [
        md(f"# AM5061 · {week_title}\n\n"
           "**Design of Thermal and Fluid Systems** · Applied Mechanics, IIT Madras · Jul–Nov 2026\n\n"
           "Run the two setup cells below once, then work down the notebook. "
           "Nothing needs to be installed on your own machine.\n"),
        md("## Setup\n\nRun these two cells first. The second one writes the "
           "course helper module, so this notebook is self-contained.\n"),
        code("#@title Install the property library  { display-mode: \"form\" }\n"
             "!pip install -q CoolProp openpyxl\n"
             "print('CoolProp ready')\n", collapsed=True),
        # %%writefile MUST be the first line of its cell, so no #@title here.
        code("%%writefile am5061.py\n" + lib, collapsed=True),
    ]


def build(path, week_title, cells):
    nb = {
        "cells": setup_cells(week_title) + cells,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4, "nbformat_minor": 0,
    }
    p = pathlib.Path(path)
    p.write_text(json.dumps(nb, indent=1))
    return p
