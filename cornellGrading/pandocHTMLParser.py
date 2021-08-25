from html.parser import HTMLParser
import re
import os
import pdf2image
import tempfile


class pandocHTMLParser(HTMLParser):
    """Parser for pandoc produced html from LaTeX source"""

    def __init__(self, hwd, upfolder):
        """Create parser for pandoc html output to reformat for Canvas elements

        Args:
            hwd (str):
                Full path to location of original LaTeX content
            upfolder (canvasapi.folder.Folder):
                Folder object for uploads

        Returns:
            None

        """

        HTMLParser.__init__(self)

        self.inBody = False  # toggle for inside body block
        self.inFigcaption = False  # toggle for inside figure caption
        self.inSpan = False  # toggle for inside span
        self.imagesUploaded = []  # storage for images uploaded
        self.figcaptions = []  # storage for uploaded image captions
        self.figCounter = 1   # increment on figure captions
        self.figLabels = {}    # storage for figure label replacement
        self.inStyle = False  # toggle for inisde style
        self.inOL = False  # toggle for inside ordered list
        self.inNestedOL = False  # toggle for inside nested ordered list

        # define regex and dict for storing all span definitions
        self.spanp = re.compile(r"span.(.*?)\s*{(.*?)}")
        self.spanDefs = {}

        # define regex and dict for handling equations
        self.labelp = re.compile(r"\\label{([^}]+)}")
        self.eqp = re.compile(r"https://latex.codecogs.com/png.latex\?(.*)")
        self.eqlabels = {}  # key is label, value is tuple of eq num and orig full label
        self.eqcounter = 1

        # internal defs
        self.hwd = hwd
        self.tmpdir = tempfile.gettempdir()
        self.upfolder = upfolder

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.inBody = True

        if tag == "ol":
            if self.inOL is True:
                self.inNestedOL = True
            else:
                self.inOL = True

        if tag == "img":
            imsrc = dict(attrs)["src"]

            # anyting that's not a link must be an actual image
            if not (imsrc.startswith("http")):
                # if you don't see it in the source directory, it's probably a
                # PDF and needs to be converted to PNG
                if not (os.path.exists(os.path.join(self.hwd, imsrc))):
                    # look for the pdf of this image
                    imf = os.path.join(
                        self.hwd, imsrc.split(os.extsep)[0] + os.extsep + "pdf"
                    )
                    if not os.path.exists(imf):
                        imf = os.path.join(
                            self.hwd,
                            imsrc.split(os.extsep)[0]
                            + "-eps-converted-to"
                            + os.extsep
                            + "pdf",
                        )
                    assert os.path.exists(imf), (
                        "Original image file not found for %s" % imsrc
                    )

                    pilim = pdf2image.convert_from_path(
                        imf,
                        dpi=150,
                        output_folder=None,
                        fmt="png",
                        use_cropbox=False,
                        strict=False,
                    )
                    pngf = os.path.join(self.tmpdir, imsrc)
                    pilim[0].save(pngf)
                    assert os.path.exists(pngf), "Cannot locate png output %s" % pngf
                else:
                    pngf = os.path.join(self.hwd, imsrc)

                # push PNG up into the HW folder
                res = self.upfolder.upload(pngf)
                assert res[0], "Imag upload failed: %s" % pngf
                self.imagesUploaded.append(
                    {
                        "orig": imsrc,
                        "url": res[1]["preview_url"].split("/file_preview")[0],
                    }
                )
            else:
                # if we're here, we're probably in an equation
                # let's look for label directives in equations
                tmp = self.eqp.match(imsrc)
                if tmp:
                    tmp2 = self.labelp.search(dict(attrs)["alt"])
                    if tmp2:
                        self.eqlabels[tmp2.groups()[0]] = (self.eqcounter, tmp2.group())
                        self.eqcounter += 1
        # end if/else tag == "img"

        if tag == "figcaption":
            self.inFigcaption = True

        if tag == "span":
            self.inSpan = True

        if tag == "style":
            self.inStyle = True

    def handle_endtag(self, tag):
        if tag == "body":
            self.inBody = False

        if tag == "ol":
            if self.inNestedOL is True:
                self.inNestedOL = False
            else:
                self.inOL = False

        if tag == "figcaption":
            self.inFigcaption = False

        if tag == "span":
            self.inSpan = False

        if tag == "style":
            self.inStyle = False

    def handle_data(self, data):
        if self.inFigcaption:
            if not(self.inSpan):
                self.figcaptions.append(data)
            else:
                self.figLabels[data] = "[Figure {}]".format(self.figCounter)
                self.figCounter += 1

        if self.inStyle:
            tmp = self.spanp.findall(data)
            if tmp:
                for t in tmp:
                    self.spanDefs['class="{}"'.format(t[0])] = t[1]

    # end MyHTMLParser
