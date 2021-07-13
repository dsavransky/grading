import csv

from sys import platform

if platform.startswith("linux") or platform == "darwin":
    from bullet import Bullet
elif platform == "win32":
    from consolemenu import SelectionMenu
else:
    raise EnvironmentError("Unsupported Platform")


def usingWindows():
    """Helper function for determining if user is on Windows platform.

    Returns:
        bool:
            True if using Windows platform, False otherwise.
    """
    return platform == "win32"


def menuChoice(title, options):
    """Helper function for displaying choices to user and getting their selection

    Args:
        title (str):
            The title of the selection menu display
        options (list):
            List of strings to be displayed as options for user to select

    Returns:
        int:
            Chosen option index
    """
    if usingWindows():
        idx = SelectionMenu.get_selection(options, title=title)
    else:
        cli = Bullet(title, options, margin=3, return_index=True)
        _, idx = cli.launch()
    return idx


def chooseCourse(c):
    """Returns course number of chosen course from a list of all courses

    Args:
        c (cornellGrading):
            Instance of cornellGrading

    Returns:
        int:
            Chosen course number
    """
    strs, ids = c.listCourses()
    idx = menuChoice("Choose course", strs)
    return ids[idx]


def chooseAssignment(c):
    """Returns assignment number of chosen assignment from a list of all assignments

    Args:
        c (cornellGrading):
            Instance of cornellGrading

    Returns:
        int:
            Chosen assignment number
    """
    strs, ids = c.listAssignments()
    idx = menuChoice("Choose assignment", strs)
    return ids[idx]


def getAssignment(c, courseNum=None, assignmentNum=None):
    """Locate assignment by course number and assignmner number
    or by finding using a menu.

        Args:
            c (cornellGrading)
                Instance of cornellGrading
            courseNum (int):
                Number of course the assignment is in. Defaults to None.
            assignmentNum (int)
                Number of the assignment. Defaults to None.

        Returns:
            canvasapi.assignment.Assignment:
                The Assignment object

    """
    if not courseNum:
        courseNum = chooseCourse(c)

    c.getCourse(courseNum)
    print(f"Processing course: {c.course}")

    if not assignmentNum:
        assignment = chooseAssignment(c)

    asgn = c.course.get_assignment(assignment)
    print(f"Processing assignment: {asgn}")

    return asgn
