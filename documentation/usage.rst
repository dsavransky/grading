Course Workflows
=================

Conventions
-----------------------
Assignments will be named as ``[Premable ]HW?`` where ``Preamble`` is an optional string (a space is automatically added between the preamble and ``HW`` if the preamble is not an empty string.  The ``?`` is an integer value. So, assignment number one, but default will be called ``HW1``.


Initial Course Setup
------------------------

In Canvas:

#. Navigate to Settings>Course Details and change course name to something unique (suggestion: Name: Semester).  Be sure to click 'Update Course Details' at the bottom.
#. Navigate to Settings>Course Details, scroll to the very bottom, click 'more options', and check 'Hide totals in student grades summary'. Click 'Updated Course Details'
#. Navigate to Settings>Navigation and ensure that 'Grades' and 'Assignments' are both in the active items (top part of page).  If you want students to be able to directly access files (rather than only via links), then add 'Files' to the active navigation items as well. Don't forget to click 'Save' at the bottom of the page.
#. Go to Student View (button on right-hand side of home page), exit student view, and then ensure that the 'test student' appears in People when you are back in Instructor view (only necessary if you want the test student to be part of the qualtrics mailing list for debugging purposes).
#. Navigate to Grades.  Click the settings icon (right of the search box) and go to the 'Grade Posting Policy tab'. Ensure that 'Automatically Post Grades' is clicked (this allows for students to see comments on HWs before grades are entered, which is necessary for link injection to the self-grading surveys). Be sure to click 'Update' if any changes are made.

Now, in python (this assumes that you have completed all steps in :ref:`Setup`):

.. code-block:: python
    
    from cornellGrading import cornellGrading
    c = cornellGrading()

    #get your coursenumber (the part in parentheses):
    print("\n".join(c.listCourses()[0]))

    coursenum = ... #change to your actual number from list printed above

    c.getCourse(coursenum)

    #consistency check
    print(c.coursename) #should be the course name you set in Canvas
    print(c.names) #should be all your students

If you are going to be using Qualtrics for your course, also run:

.. code-block:: python
   
    #connect to qualtrics and generate course mailing list
    c.setupQualtrics()
    c.genCourseMailingList()

The Qualtrics setup should be skipped in you are not planning to do Qualtrics-based student polling or Qualtrics-based self-assessments. 

Upload a Homework and Create a New Assignment
-----------------------------------------------

This procedure automates the creation of new assignments, assuming that your homework statement is in a single PDF document.  This assumes that there already exists an 'Assignments' assignment group (Canvas default), and will create a 'Homeworks' folder under Files that is not directly accessible to students (assuming it does not already exist).

The assignment will be titled 'HW?' where ? is the assignment number (i.e., 'HW1', 'HW2', etc.).

In python:

.. code-block:: python

    from cornellGrading import cornellGrading
    c = cornellGrading()
    coursenum =   #insert your course number here
    c.getCourse(coursenum)

    assignmentNum =   #enter assignment number (must be integer)
    duedate =         #enter assignment duedate in 'YYYY-MM-DD' format. The due time will be 5pm by default.
    hwfile =          #string - full path on your local disk to the HW pdf file
    res = c.uploadHW(assignmentNum,duedate,hwfile)

By default, the created assignment will be worth 10 points.  To change this, instead of the last line, run:

.. code-block:: python

    res = c.uploadHW(assignmentNum,duedate,hwfile,totscore=N) #N must be an integer

By default, the created assignment will be immediately visible. To change this, instead of the last line run:
.. code-block:: python

    res = c.uploadHW(assignmentNum,duedate,hwfile,unlockDelta=M)

where ``M`` is a positive float and represents the number of days prior to the due date to unlock the assignment.


Injecting Homework Text into the Canvas Assignment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the homework file is a PDF compiled from LaTeX source code, and resides in the same directory as the original ``tex`` file, then you can inject its contents directly into the homework assignment as HTML, along with the link to the PDF, by running:

.. code-block:: python

    res = c.uploadHW(assignmentNum, duedate, hwfile, injectText=True)

See :ref:`Latex2Canvas` for further details.

.. note::
    
    ``hwfile`` must point at the PDF in the directory where it was compiled, and all other required files (figures, etc.) must reside in this same path.


Homework Self-Assessments
---------------------------

``cornellGrading`` provides two methods for implementing student self-assessment.  This section describes how to use Canvas New Quizzes to implement this workflow.  Alternatively, you can create :ref:`qualtricsselfassessments`, described below. 

New Quiz-based self-assessments are implemented by method :py:meth:`~cornellGrading.cornellGrading.cornellGrading.setupNewQuizSelfAssessment`.  This method:

#. Generates a Canvas New Quiz with multiple choice questions corresponding to each question on your homework assignment that are worth 0 to N points (where you specify N, default 3).  Each answer earns the equivalent number of points. 
#. Generates a Canvas page with your reference solutions (employing :ref:`Latex2Canvas`) from a LaTeX source file). 

Assuming you set up the assignment with the name ``HW?`` (where ? is the assignment number), the self-assessment for the assignment can be set up by running:

.. code-block:: python
    
    assignmentNum = 1 # integer value, update to actual assignment number
    nprobs = 5 # integer, update to actual number of problems 
    solfile = "/Full/Path/To/Solution/File"

    c.setupNewQuizSelfAssessment(
        assignmentNum,
        nprobs,
        solfile,
        npoints=3,  # possible points per problem
        selfGradeDueDelta=6,  # number of days after release that self-assessment is due
        selfGradeReleasedDelta=3,  # number of days after hw due dat that solutions are released
    )


The ``solfile`` input must be a string with the full path on disk to the solution file, which must be a PDF or tex source file, and must be in the same folder as the full document source and all figures/inputs. 


Including Additional Self-Assessment Questions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can include additional questions in New Quiz-based self-assessments.  For example, say you wanted students to write a short essay assessing their overall performance.  This question could be defined as:

.. code-block:: python

    item_body = (
        "<p><span>Please write a brief self-assessment of your performance on "
        "this assignment.&nbsp; Focus in particular on skills/concepts that you "
        "want to work on in subsequent assignments.</span></p>"
    )
    selfassq = {
        "position": 0,
        "points_possible": 0.0,
        "properties": {},
        "entry_type": "Item",
        "entry_editable": True,
        "stimulus_quiz_entry_id": "",
        "status": "mutable",
        "entry": {
            "title": "Self-Assessment",
            "item_body": item_body,
            "calculator_type": "none",
            "interaction_data": {
                "rce": True,
                "essay": None,
                "word_count": False,
                "file_upload": False,
                "spell_check": False,
                "word_limit_max": None,
                "word_limit_min": None,
                "word_limit_enabled": False,
            },
            "properties": {
                "word_limit": False,
                "spell_check": False,
                "word_limit_max": 0,
                "word_limit_min": 0,
                "show_word_count": False,
                "rich_content_editor": False,
            },
            "scoring_data": {"value": ""},
            "answer_feedback": {},
            "scoring_algorithm": "None",
            "interaction_type_slug": "essay",
            "feedback": {"neutral": "", "correct": "", "incorrect": ""},
        },
    }

Alternatively, you can ask students binary (Yes/No) questions.  For example, if you want students to verify whether they formatted plots properly:

.. code-block:: python

    figureq = c.genBinaryNewQuizItem(
        2,
        "Were all of your plots appropriately formatted and labeled?",
        "Plot Formatting",
    )

To include additional questions in the self-assessment quiz, use the ``extraQuestions`` keyword input to :py:meth:`~cornellGrading.cornellGrading.cornellGrading.setupNewQuizSelfAssessment`. This input takes a list of question definition dictionaries.  So, if you wished to only include the essay question defined above, you would set ``extraQuestions = [selfassq]`` and if you wanted to include both questions, you would set ``extraQuestions = [selfassq, figureq]``. 


.. _qualtricsselfassessments:

Qualtrics-Based Self-Assessments
------------------------------------
As an alternative to new quiz-based self-assessments, you can implement self-assessments via Qualtrics surveys.

Create a HW Survey
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This assumes that you have set up your assignment with the name 'HW?' where ? is the assignment number (i.e., 'HW1', 'HW2', etc.).

.. code-block:: python

    from cornellGrading import cornellGrading
    c = cornellGrading()
    coursenum =   #insert your course number here
    c.getCourse(coursenum)
    c.setupQualtrics()
    assignmentNum = 1 #change to actual assignment number
    nprobs = 3 #number of problems in assignment
    c.setupPrivateHW(assignmentNum,nprobs)


Or, let's say you're a weirdo who only wants a single grade for the whole assignment, and wants the students to grade themselves out of 10,9,7,5,3, exclusively.  Then the last line becomes:

.. code-block:: python

    c.setupPrivateHW(assignmentNum,0,scoreOptions=[10,9,7,5,3])

After executing (assuming no errors), you should see a new survey in Qualtrics with the name "Coursename HW? Self-Grade", and a personalized link should be injected into the comments for each student in the original assignment. 

If your course roster has changed, be sure to run ``c.updateCourseMailingList()`` prior to ``setupPrivateHW``.

You can also share the created survey with another qualtrics user (say, your TA).  To do so, you will need them to give you their Qualtrics id, which they can find in the Qualtrics IDs page ([see Qualtrics API Token ](#qualtrics-api-token)). Make sure you get their ID, and not their API token.  To enable sharing, add ``sharewith=qualtricsid`` to the ``setupPrivateHW`` call, where ``qualtricsid`` is id string to share with.

Upload Solutions and Create Self-Grading Assignment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to creating the HW survey in qualtrics and injecting links into the assignment comments, ``setupPrivateHW`` can also create a self-grading assignment on Canvas with the homework solutions and a due date that is different from the due date of the original assignment.  This functionality is toggled by passing ``createAss=True`` to the ``setupPrivateHW`` call.  The other relevant keyword arguments are:

* ``solutions``: String, full path to solutions PDF file on your local disk
* ``selfGradeDueDelta``: Float, number of days after original assignment due date for self-grading to be due (defaults to 7) 
* ``selfGradeReleasedDelta``: Float, number of days after original assignment due date when the self-grading assignment is released to students (defaults to 3).

So, a full call would look something like:

.. code-block:: python

    from cornellGrading import cornellGrading
    c = cornellGrading()
    coursenum =   #insert your course number here
    c.getCourse(coursenum)
    c.setupQualtrics()
    assignmentNum = 1 #change to actual assignment number
    nprobs = 3 #number of problems in assignment
    solutionsFile =   #insert path to solutions file
    c.setupPrivateHW(assignmentNum,nprobs,createAss=True,solutions=solutionsFile)

This will create a  'Homework Self-Grading' assignment group (if it does not already exist), and will create a 'Homeworks' folder under Files that is not directly accessible to students (also assuming it does not already exist).


Grab Self-Grading Results and Upload to Canvas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finally, once students have completed their self-assessment via Qualtrics, we need to move their scores into the Canvas gradebook.  This is done via the :py:meth:`~.cornellGrading.selfGradingImport` method.  Again, this assumes that you have set up your assignment with the name 'HW?' where ? is the assignment number, and also that you have assigned a point value to the assignment in Canvas (if you're using the single-question survey variant, and not checking for late submissions, the latter is not required).

In python:

.. code-block:: python

    from cornellGrading import cornellGrading
    c = cornellGrading()
    coursenum =   #insert your course number here
    c.getCourse(coursenum)
    c.setupQualtrics()
    assignmentNum = 1 #change to actual assignment number
    c.selfGradingImport(assignmentNum)

By default, this will take the sum of all of the survey question responses, scale by the ratio of the total assignment points (grabbed from Canvas) to the total number of possible points in the survey. If you are using the single-question survey variant (i.e., set ``nprobs`` to 0 in the ``setupPrivateHW`` call), then the assignment total value in Canvas is ignored, and just the exact value from Qualtrics is used. 

Default behavior is to check for late submissions, and then subtract 1/4th the total number of points if the assignment is late. Lateness is defined by the ``maxDaysLate`` keyword (defaults to 3), past which the assignment is marked zero, and the penalty itself is set by ``latePenalty``.  In order to toggle off late checking alltogether, set ``checkLate=False``, so that the last line above becomes ``c.selfGradingImport(assignmentNum,checkLate=False)``.

If your assignment has extra credit problems, you can identify these in your survey by adding the words 'Extra Credit' to any of the question names.  In this case, a maximum of ``ecscore`` points (default is 3) will be added to the HW score for all extra credit problems being self-marked perfect (and scaling down consistently with self-grading).


