#!python

import argparse
import numpy as np
import bs4
import pynliner
import subprocess
import os


def main():
    parser = argparse.ArgumentParser(
        description="Convert LaTeX file to Canvas-style html."
    )
    parser.add_argument(
        "filepath", nargs=1, type=str, help="Full path to lattex file (string)."
    )

    args = parser.parse_args()

    filepath = args.filepath[0]
    assert os.path.exists(filepath), f"Could not locate {filepath}."
    d, f = os.path.split(filepath)
    basename, ext = f.split(os.extsep)
    assert ext.lower() == "tex", "Input file must have tex extension."

    if not (d):
        d = os.path.curdir

    _ = subprocess.run(
        ["make4ht", f],
        cwd=d,
        check=True,
        capture_output=True,
    )

    with open(os.path.join(d, f"{basename}.html"), "r") as file:
        soup = bs4.BeautifulSoup(file.read())

    stylesheets = soup.findAll("link", {"rel": "stylesheet"})

    for s in stylesheets:
        t = soup.new_tag("style")
        with open(os.path.join(d, s["href"])) as file:
            csstxt = file.read()

        csstxtsan = []
        for l in csstxt.split("\n"):
            if "~" not in l:
                csstxtsan.append(l)

        c = bs4.element.NavigableString("\n".join(csstxtsan))

        t.insert(0, c)
        t["type"] = "text/css"
        s.replaceWith(t)

    html0 = str(soup)
    out = pynliner.fromString(html0)

    with open(os.path.join(d, f"{basename}_for_Canvas.html"), "w") as file:
        file.write(out)


if __name__ == "__main__":
    main()
