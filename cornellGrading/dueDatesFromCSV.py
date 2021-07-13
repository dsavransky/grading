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
        "-cn",
        "--courseNum",
        type=int,
        help="Canvas course id (int). Skip for interactive course menu.",
    )
    parser.add_argument(
        "-an",
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
    """Interactively choose courses from Canvas

    Args:
        c (cornellGrading): The cornellGrading object initialized by the user

    Returns:
        int: Course ID
    """
    strs, ids = c.listCourses()
    cli = Bullet("Choose course", strs, margin=3, return_index=True)
    _, idx = cli.launch()
    return ids[idx]


def chooseAssignment(c):
    """Interactively choose assignment from course

    Args:
        c (cornellGrading): The cornellGrading object initialized after selecting a course

    Returns:
        int: Assignment ID
    """
    strs, ids = c.listAssignments()
    cli = Bullet("Choose assignment", strs, margin=3, return_index=True)
    _, idx = cli.launch()
    return ids[idx]


def getAssignment(c, args):
    """General assignment chooser, taking into account command line arguments and complementing with interactive menus

    Args:
        c (cornellGrading): The cornellGrading object initialized by the user
        args (argparser args): Argument list parsed by argparse

    Returns:
        canvasapi.Assignment: The assignment object selected
    """

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


def main():

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
        reader = csv.DictReader(csvfile)

        # Scan CSV file
        for row in reader:
            print(f"Section {row['section']}:")
            print(f"|  Due at {row['due_date']} {row['due_time']}")
            if "from_date" in reader.fieldnames:
                print(f"|  Available from {row['from_date']} {row['from_time']}")
            if "until_date" in reader.fieldnames:
                print(f"|  Available until {row['until_date']} {row['until_time']}")

            sectionid = -1
            for s in secs:
                if s.name == row["section"]:
                    sectionid = s.id

            assert sectionid > -1, f"Course doesn't have section {row['section']}"

            # Set override for due dates
            due_date = c.localizeTime(row["due_date"], row["due_time"])
            overridedef = {
                "course_section_id": sectionid,
                "due_at": due_date.strftime("%Y-%m-%dT%H:%M:%SZ"),  # must be UTC
            }

            # Add optional override for "available from" dates
            if "from_date" in reader.fieldnames:
                from_date = c.localizeTime(row["from_date"], row["from_time"])
                overridedef["unlock_at"] = from_date.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )  # UTC

            # Add optional override for "available until" dates
            if "until_date" in reader.fieldnames:
                until_date = c.localizeTime(row["until_date"], row["until_time"])
                overridedef["lock_at"] = until_date.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )  # UTC

            try:
                asgn.create_override(assignment_override=overridedef)
            except:
                print(
                    "Request failed: This usually means that the section already has a due date. Consider using the --force flag."
                )


if __name__ == "__main__":
    main()
