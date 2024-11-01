import urllib.parse
import re


def convalllatex(text):
    """Convert all instances of LaTeX in a string to Canvas-compatible images

    Args:
        text (str):
            Input text

    Returns:
        str:
            Output text

    """

    p = re.compile(r"\${1,2}(.*?)\${1,2}")

    return p.sub(convlatex, text)


def convlatex(texstr):
    """Convert input latex string to Canvas's img html

    Args:
        texstr (str or re.Match):
            LaTeX-formatted equation string

    Returns:
        str:
            Canvas-style image string

    """

    # handle case where input is re.Match
    if isinstance(texstr, re.Match):
        texstr = texstr.groups()[0]

    # replace problematic commands int LaTeX
    texsubdict = {
        r"\\textrm": "",
    }
    for key, val in texsubdict.items():
        texstr = re.sub(key, val, texstr)

    convstr = urllib.parse.quote(urllib.parse.quote(texstr))
    qtxt = (
        f"""<img class="equation_image" title="{texstr}" """
        f"""src="/equation_images/{convstr}?scale=1" """
        f"""alt="LaTeX: {texstr}" """
        f""" data-equation-content="{texstr}" data-ignore-a11y-check="">"""
    )

    return qtxt
