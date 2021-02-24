#!python

import argparse
import urllib.parse
import re
import os.path


def convlatex(texstr):
    """ Convert input latex string to Canvas's img html """

    if isinstance(texstr, re.Match):
        texstr = texstr.groups()[0]
    qtxt = """<img class="equation_image" title="{0}" src="https://canvas.cornell.edu/equation_images/{1}" alt="LaTeX: {0}">""".format(
        texstr, urllib.parse.quote(urllib.parse.quote(texstr))
    )

    return qtxt


def convall(text):
    p = re.compile(r"\${1,2}(.*?)\${1,2}")

    return p.sub(convlatex, text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert LaTeX input to Canvas-style html."
    )
    parser.add_argument(
        "texstr", nargs=1, type=str, help="LaTeX input or file (string)."
    )
    parser.add_argument(
        "--par",
        action="store_true",
        help="Treat input as paragraph with embedded LaTeX with $ or $$ delimiters",
    )

    args = parser.parse_args()

    texstr = args.texstr[0]
    if os.path.exists(texstr):
        with open(texstr, "r") as f:
            texstr = f.read()

    if args.par:
        qtxt = convall(texstr)
    else:
        qtxt = convlatex(texstr)

    print(qtxt)

    exit(0)
