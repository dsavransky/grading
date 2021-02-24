#!python

import argparse
import csv

from bullet import Bullet

import cornellGrading


def getArgs():
    parser = argparse.ArgumentParser(
        description="Set up complex due dates based on CSV file"
    )
    parser.add_argument(
        "--courseNum",
        type=int,
        help="Canvas course id (int). Skip for interactive course menu.",
    )
    parser.add_argument(
        "--assignmentNum",
        type=int,
        help="Number of assignment (int). Skip for interactive assignment menu.",
    )
    parser.add_argument(
        "csvFileName", type=str, help="CSV file with due dates (string)."
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Delete existing due dates.",
    )
    return parser.parse_args()


def chooseCourse(c):
    strs, ids = c.listCourses()
    cli = Bullet("Choose course", strs, margin=3, return_index=True)
    _, idx = cli.launch()
    return ids[idx]


def chooseAssignment(c):
    strs, ids = c.listAssignments()
    cli = Bullet("Choose assignment", strs, margin=3, return_index=True)
    _, idx = cli.launch()
    return ids[idx]


def getAssignment(c, args):

    if args.courseNum:
        coursenum = args.courseNum
    else:
        coursenum = chooseCourse(c)

    c.getCourse(coursenum)
    print(f"Processing course: {c.course}")

    if args.assignmentNum:
        assignment = args.assignmentNum
    else:
        assignment = chooseAssignment(c)

    asgn = c.course.get_assignment(assignment)
    print(f"Processing assignment: {asgn}")

    return asgn


if __name__ == "__main__":

    c = cornellGrading.cornellGrading()
    args = getArgs()
    asgn = getAssignment(c, args)

    # Delete old due dates if they exist? Use the "--force" flag.
    if args.force:
        for o in asgn.get_overrides():
            print(f"Deleting existing override {o}")
            o.delete()

    # Due dates by section
    secs = c.course.get_sections()

    with open(args.csvFileName) as csvfile:
        reader = csv.reader(csvfile)

        # Skip first row
        header = next(reader)

        # Scan CSV file
        for row in reader:
            print(f"Section {row[0]}: due at {row[1]} {row[2]}")
            sectionid = -1
            for s in secs:
                if s.name == row[0]:
                    sectionid = s.id

            assert sectionid > -1, f"Course doesn't have section {row[0]}"

            # Set override for due dates
            duedate = c.localizeTime(row[1], row[2])
            overridedef = {
                "course_section_id": sectionid,
                "due_at": duedate.strftime("%Y-%m-%dT%H:%M:%SZ"),  # must be UTC
            }
            try:
                asgn.create_override(assignment_override=overridedef)
            except:
                print(
                    "Request failed: This usually means that the section already has a due date. Consider using the --force flag."
                )
