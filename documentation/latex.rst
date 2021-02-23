.. _Latex2Canvas:

LaTeX to Canvas
==================

.. note::

    This functionality requires that the package has been installed with the optional ``[latex2html]`` dependencies, and that you have pandoc installed and in the system PATH.  See :ref:`Setup` for further details.


The :py:meth:`~.cornellGrading.latex2html` method allows you to convert LaTeX source into Canvas-native html, including rendering equations via the Canvas equation editor (this produces an equation image that contains the original equation as alt tex and (in compatible browsers) a MathJax payload that can be utilized by screen readers.  This is the single best approach (found to date) of ensuring that LaTeX-derived products are fully accessible.

This functionality uses pandoc for the initial HTML conversion, and is therefore limited by pandoc's capabilities.  For details on pandoc, see the user's guide: https://pandoc.org/MANUAL.html

In general, pandoc will be able to handle relatively simple documents based on the article or amsart class, using some additional optional packages (see: https://pandoc.org/MANUAL.html#variables-for-latex).  Macros defined in the source will typically be supported (unless they rely on unsupported packages).  User-defined style files typically will not work.  The easiest way to see whether your LaTeX document will render properly is to run pandoc on it manually and inspect the output html.

The :py:meth:`~.cornellGrading.latex2html` method will attempt to do the following:

#. Make a copy of the input LaTeX source and apply a dictionary of standard substitutions.  The dictionary variable name is ``texsubdict``. It currently only contains mappings from ``\nicefrac`` to ``\frac`` and removes all ``\ensuremath`` directives, but can be updated as needed.
#. Execute pandoc on the cleaned-up source code, using the original direcotry as the working directory, with flags ``--webtex`` and ``--default-image-extension=png``
#. Read in the resulting HTML and parse.  In parsing, every equation image link will be overwritten to point at Canvas, every image (inside a Figure) will be uploaded to Canvas (if the original image is no a PNG, a PNG will be generated first) and the image link will be updated to point at the uploaded figure, and all span css formatting will be added to each individual span directive.

Currently, images will only be properly handled if inside a Figure float.  Table support exists, but is spotty. 


Create Canvas Page from LaTeX
---------------------------------


The :py:meth:`~.cornellGrading.latex2page` method allows you to convert LaTeX source into a Canvas page.

Assuming you have instantiated a ``cornellGrading`` object as ``c``, as above, you can run:

.. code-block:: python

    res = c.latex2page(fname, title)

where `fname` is the full path to either the LaTeX source or the PDF compiled from the source (which must be in the same directory as the source), and `title` is the title for the generated page.  Other method options include:

* ``insertPDF=True`` will also include a link to the compiled PDF in the generated page (in this case `fname` must be the compiled PDF)
* ``published=True`` will automatically publish the page (the page is unpublished by default).


