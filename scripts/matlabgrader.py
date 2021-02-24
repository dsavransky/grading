#!python

"""
Parse MATLAB Grader output and upload to Canvas

In Grader:
- In assignment main page: Actions>Report
   - Best solution as of today
   - Output:csv
   - Save file
"""

import cornellGrading
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse MATLAB Grader output and upload to Canvas"
    )
    parser.add_argument("courseNum", nargs=1, type=int, help="Canvas course id (int).")
    parser.add_argument(
        "assignmentNum", nargs=1, type=int, help="Number of assignment (int)."
    )
    parser.add_argument(
        "gradercsv", nargs=1, type=str, help="Full path to grader export (string)."
    )
    parser.add_argument(
        "duedate", nargs=1, type=str, help="Assignment due date (string: YYYY-MM-DD)."
    )

    args = parser.parse_args()

    coursenum = args.courseNum[0]
    gradercsv = args.gradercsv[0]
    assignmentNum = args.assignmentNum[0]
    duedate = args.duedate[0]

    c = cornellGrading.cornellGrading()
    c.getCourse(coursenum)

    c.matlabImport(assignmentNum, gradercsv, duedate)
