# grading
Routines for semi-automated grading of MATLAB coding assignments and interaction with Canvas and Qualtrics.

By Dmitry Savransky with contributions by Guy Hoffman and Brian Kirby. Thanks also to Hadas Ritz for extensive testing and QA.

Please note: the Canvas routines have the potential to bork your gradebook and (unlikely but possibly) whole course site. **Use at your own risk**. 

[![Documentation Status](https://readthedocs.org/projects/grading/badge/?version=latest)](https://grading.readthedocs.io/en/latest/?badge=latest)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
[![PyPI version](https://badge.fury.io/py/cornellGrading.svg)](https://badge.fury.io/py/cornellGrading)
[![Requirements Status](https://requires.io/github/dsavransky/grading/requirements.svg?branch=main)](https://requires.io/github/dsavransky/grading/requirements/?branch=main)

cornellGrading Installation
==============================
To install from PyPI:

```
pip install --user cornellGrading
```

Or, with optional dependencies required to push LaTeX into Canvas HTML:

```
pip install --user cornellGrading[latex2html]
```

To install system-wide, omit the `--user` option.

---
**NOTE**

The `latex2html` option requires the pandoc executable to be installed and in the system PATH.  For detailed pandoc installation instructions see here: https://pandoc.org/installing.html

---

If cloning from github, in the cloned grading directory:

```
pip install --user .
```

or, to install in developer mode:

```
pip install --user -e .
```

In order to also install requirements needed push LaTeX into Canvas HTML, do:

```
pip install --user -e .[latex2html]
```

cornellGrading Documentation
================================
Documentation is available here: https://grading.readthedocs.io/

Docstrings: https://grading.readthedocs.io/en/latest/cornellGrading.html#module-cornellGrading.cornellGrading

Acknowledgements
=====================
cornellGrading uses [UCF/Open_'s](https://ucfopen.github.io/) [canvasapi](https://github.com/ucfopen/canvasapi) and the [black](https://github.com/psf/black) code formatter. 
