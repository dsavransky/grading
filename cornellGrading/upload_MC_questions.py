#!python

from cornellGrading import cornellGrading
import easygui  # graphical user interface
import re  # regular expressions, for search in string
import urllib.parse
import numpy as np  # python scientific computing package


# define converter to convert standalone input latex string into html


def convlatex(texstr):
    # Convert input latex string to Canvas's img html

    if isinstance(texstr, re.Match):
        texstr = texstr.groups()[0]
    # canvas double-encodes urls, so you have to double-encode urls as well or some of your urls will drop out when it double-decodes
    qtxt = """<img class="equation_image" title="{0}" src="https://canvas.cornell.edu/equation_images/{1}" alt="LaTeX: {0}">""".format(
        texstr, urllib.parse.quote(urllib.parse.quote(texstr))
    )

    return qtxt


# define converter to parse and find strings enclosed by $, sending enclosed strings to convlatex


def convall(text):
    p = re.compile(r"\${1,2}(.*?)\${1,2}")

    return p.sub(convlatex, text)


def main():

    c = cornellGrading()

    # get canvas data from my class into cornellgrading's c

    courseNames = c.listCourses()[0]  # gets courses I have access to

    courseNumbers = [
        re.findall(r"\((.+?)\)", i)[-1] for i in courseNames
    ]  # pull out rightmost instance of a string in between parentheses

    # append  end-program options, with dummy string
    endProgram = "-1234"
    courseNames.insert(0, "end program")
    courseNumbers.insert(0, endProgram)
    courseChosen = easygui.choicebox(
        "Select canvas course (or exit)",
        "Course Selector (or exit)",
        choices=courseNames,
    )
    coursenum = int(courseNumbers[courseNames.index(courseChosen)])

    c.getCourse(coursenum)

    # load text file with BK-formatted multiple-choice questions using the numpy module
    filename = easygui.fileopenbox(
        msg="Select a txt multiple-choice question bank input file",
        title="Input File Selector",
        default="./*_MC.txt",
    )  # ,'txt multiple-choice source files'
    data = np.genfromtxt(
        filename, delimiter="\t", dtype=str
    )  # numpy function to load data from text

    # create a quiz.  at present this quiz has no properties; it is a vehicle to upload a bank of questions because Kirby is unaware of a question bank endpoint in the API.
    # i could make the quiz have properties, just haven't done so

    q = c.course.create_quiz(
        {"title": "dummy quiz"}
    )  # creates quiz in course; title is 2nd string

    # create array of questions from data from file.  uses blackboard multiple choice input format for cross-compatibility
    # format: MC <tab> question <tab> correct/incorrect <tab> response to answer <tab> repeat sets of three for additional answers

    for row in data:  # loop through rows in data
        answers = []  # create blank answers object
        for a in np.reshape(
            row[2:], (int(row[2:].size / 3), 3)
        ):  # takes cols in pairs starting with third one and puts in a
            answers.append(
                {"answer_html": convall(a[0])}
            )  # assign answer text.  put in answer_html not answer_text so that latex can be processed
            if (
                a[1] == "correct"
            ):  # parsing text file for the blackboard input standard and switching to the canvas input standard
                correctValue = 100  # canvas appears to assign the first answer with correctValue>0 to be correct, all others incorrect
            else:
                correctValue = 0  # their use of numbers make you think you an assign partial credit.  you can't.
            answers.append({"answer_weight": correctValue})  # assign corectness
            answers.append(
                {"comments_html": convall(a[2])}
            )  # comments in response to right or wrong answers
            # answers.append({'comments_html':convall(r"test latex $\pi=\cos\,\theta$")}) # comments in response to right or wrong answers
            # can have latex also.  this is true for MC quest.
            # Not generally true, canvas implementation is very inconsistent
        q.create_question(
            question={
                "question_text": convall(row[1]),
                "question_type": "multiple_choice_question",
                "answers": answers,
            }
        )  # in canvas, upload question


if __name__ == "__main__":
    main()
