#!python

"""
Create a qualtrics survey and a Canvas self-grading assignment
"""

import cornellGrading
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a qualtrics survey and a Canvas self-grading assignment"
    )
    parser.add_argument("courseNum", nargs=1, type=int, help="Canvas course id (int).")
    parser.add_argument(
        "assignmentNum", nargs=1, type=int, help="Number of assignment (int)."
    )
    parser.add_argument(
        "duedate", nargs=1, type=str, help="Assignment due date (string: YYYY-MM-DD)."
    )
    parser.add_argument("nprobs", nargs=1, type=int, help="Number of problems (int).")

    args = parser.parse_args()

    coursenum = args.courseNum[0]
    nprobs = args.nprobs[0]
    assignmentNum = args.assignmentNum[0]
    duedate = args.duedate[0]

    c = cornellGrading.cornellGrading()
    c.getCourse(coursenum)
    c.setupQualtrics()

    c.setupHW(assignmentNum, duedate, nprobs)
