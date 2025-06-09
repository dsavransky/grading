import urllib.parse
import re
import pandas
import os
import numpy as np


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


def email2netid(emails):
    """Transform emails to netids

    Args:
        emails (iterable):
            List or array of strings containing email addresses

    Returns:
        list:
            List of netids (part of email before @)

    """

    return [e.split("@")[0] for e in emails]


def netid2email(netids, domain="cornell.edu"):
    """Transform emails to netids

    Args:
        netids (iterable):
            List or array of strings containing netids (usernames)
        domain (str):
            Email domain.  Defaults to "cornell.edu"

    Returns:
        list:
            List of emails

    """

    return [f"{n}@{domain}" for n in netids]


def readGradescopeFile(datafile):
    """Read in gradescope grade csv and return dataframe

    Args:
        datafile (str):
            Full path to gradescope CSV output file

    Returns:
        pandas.DataFrame:
            The data, along with a NetID column

    """

    assert os.path.exists(datafile), f"{datafile} not found."

    data = pandas.read_csv(datafile)
    data = data.loc[data["Status"] != "Missing"].reset_index(drop=True)
    data["NetID"] = email2netid(data["Email"].values)

    data["Lateness"] = pandas.to_timedelta(data["Lateness (H:M:S)"]) / np.timedelta64(
        1, "h"
    )

    return data
