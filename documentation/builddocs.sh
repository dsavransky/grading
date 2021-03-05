#!/bin/bash
# Script to fully regenerate, compile and update html docs
# must be run directly from documentation directory

if [ ! -d "../cornellGrading" ] || [ `basename $PWD` != "documentation" ] ; then
    echo "This script must be run from the documentation directory in the grading parent directory."
    exit 1
fi


sphinx-apidoc -f -o . ../cornellGrading/ 

rm modules.rst

make html
make html

exit 0

