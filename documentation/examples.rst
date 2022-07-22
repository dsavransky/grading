Extended Examples
====================

Individualized Quizzes
------------------------

I decided (for reasons that defy explanation), to give a personalized, self-administered, self-timed, written exam (hello to the other 3 people in the universe with this use case). Canvas, in their infinite wisdom, provide the exact framework for this kind of thing (in the form of graded Quizzes), but then do not allow a file upload to the quiz.  So, we go the convoluted route:  use a Quiz to deliver the exam to students and record a start time, and then use an assignment to collect the responses.  Compare quiz start times to assignment submit times to check whether the students exceeded their allowed time window, and then grade the submissions as usual.  All that remains is setting up a separate quiz for each student and assigning each one to *only* the intended student.  Here we go:

#. First we set up a single assignment to collect the results.  This can be done manually via the web interface or through the API, but in either case, note the assignment id and url so you can link directly to it from the quizzes (not strictly necessary, but makes things easier for the students).

#. Write your bank of exam questions. I decided that I wanted groups of similar questions, wanted to give each student 3 questions to solve, and had ~45 students, so I ended up with 3 groups of questions of 4, 4, and 3 questions in each (48 unique combinations).  Each question lives in its own file named ``prob1.tex``, ``prob2.tex``, etc., and there's a ``header.tex`` in the same directory with all the front matter of the exam (including a ``\begin{enumerate}`` directive). We're going to generate and compile a unique pdf tagged with each student's netid - here I'll just show one instance, but you wrap everything in a loop to cover all students.

    .. code-block:: python

        from cornellGrading import cornellGrading
        from datetime import datetime, timedelta
        import numpy as np
        import subprocess

        c = cornellGrading()
        coursenum = ... # your course number here
        c.getCourse(coursenum)

        prelimpath = ... # path to prelim dir with all the tex files

        # question groups
        block1 = [1,2,3,4]
        block2 = [5,6,7,8]
        block3 = [9,10,11]

        # generate unique combinations and randomize order
        combos = []
        for i in range(len(block1)):
            for j in range(len(block2)):
                for k in range(len(block3)):
                    combos.append([block1[i],block2[j],block3[k]])

        combos = np.array(combos)
        rng = np.random.default_rng()
        arr = np.arange(len(combos))
        rng.shuffle(arr)
        combos = combos[arr]

        # create/get destination folder on Canvas for uploads
        prelimfolder = c.createFolder("Homeworks/Prelim", hidden=True)

        #going to do just the first student, but this is where you'd start the loop
        nid = c.netids[0] # netid
        comb = combos[0]  # problem set

        # write exam tex file
        fname = os.path.join(prelimpath, 'prelim_2020_{}.tex'.format(nid))
        with open(fname, "w") as f:
            f.write("\\input{header.tex}\n")
            for p in comb:
                f.write("\\input{prob%d.tex}\n"%(p))
            f.write("\\end{enumerate}\n")
            f.write("\\bigskip\\bigskip This exam is for %s"%(nid))
            f.write("\\end{document}\n")

        # compile exam
        _ = subprocess.run(["latexmk","-pdf",fname],cwd=prelimpath,check=True,capture_output=True)
        pdfname = os.path.join(prelimpath, 'prelim_2020_{}.pdf'.format(nid))
        assert os.path.exists(pdfname)

        prelimupload = prelimfolder.upload(pdfname)
        assert prelimupload[0], "Prelim Upload failed."

    Note that I've used ``latexmk`` (which of course has to be in my path already) to take care of multiple compilation steps, etc.  If all your questions are simple (no cross-references or anything else requiring multiple compilations, then regular ``pdflatex`` should work fine instead).

#. At this point, we've generated a unique exam PDF for our student(s), so now it's time to place it into a timed quiz.  We have to make it a graded quiz so it can show up in an assignment group. Another important caveat here is how Canvas handles question additions to existing quizzes.  If the quiz is already published and you add a question, Canvas requires that you re-save the quiz before the question becomes visible to students.  I have not found a good way of doing this via the API (what the hell, Canvas?), so the best solution is to generate the quiz *unpublished* add all your questions, and then edit the existing quiz object to make it published.  As a final step, we need to add an assignment override onto the quiz assignment to give it a due date, an unlock date, and to assign it to a single student. Again, showing the same single instance, which you'd loop over for all students.

    .. code-block:: python

        # select assignment group for quizzes to go into
        examgroup  = c.getAssignmentGroup("Exams")

        # write the quiz instructions.
        qdesc = (u'<h2>Stop!</h2>\n<p>By accessing this quiz, you are starting your exam,'
                 u' and the three hour window for submission.\xa0 Do\xa0<strong>not</strong>'
                 u' access the quiz before you are ready to begin.\xa0 If your solution is'
                 u' uploaded any time after the 3 hour window has expired, you will receive'
                 u' no credit for your exam.\xa0</p>\n<p>You do not need to submit this quiz.'
                 u' \xa0 All submission should be made to ' #insert link to submission assignment here
                 u' Your submission must be a\xa0<strong>single, clearly legible PDF.'
                 u' \xa0\xa0</strong>Do not submit individually scanned pages or any other'
                 u' format. You will only have one submission attempt, so be sure to check your'
                 u' work carefully before submitting.</p>')

        # set due date and unlock date
        duedate = c.localizeTime("2020-11-13")
        unlockat = c.localizeTime("2020-11-11",duetime="09:00:00")

        # generate quiz
        quizdef = {
            "title": "Prelim Questions for %s"%nid,
            "description": qdesc,
            "quiz_type":"assignment",
            "assignment_group_id": examgroup.id,
            "time_limit": 180, #this is in minutes
            "shuffle_answers": False,
            "hide_results": 'always',
            "show_correct_answers": False,
            "show_correct_answers_last_attempt": False,
            "allowed_attempts": 1,
            "one_question_at_a_time": False,
            "published": False, #super important!
            "only_visible_to_overrides": True #super important!
            }
        q1 = c.course.create_quiz(quiz=quizdef)

        # add the payload to the quiz
        purl = prelimupload[1]["url"]
        pfname = prelimupload[1]["filename"]
        pepoint = purl.split("/download")[0]
        questext = (
            """<p>Your exam can be accessed here:"""
            """<a class="instructure_file_link instructure_scribd_file" title="{0}" """
            """href="{1}&amp;wrap=1" data-api-endpoint="{2}" """
            """data-api-returntype="File">{0}</a></p>\n<p>Don\'t worry if your browser """
            """warns you about navigating away from this page when trying to download the """
            """exam - it won\'t break anything.</p>""".format(pfname, purl, pepoint)
        )
        quesdef = {
            "question_name": "Prelim",
            "question_text": questext,
            "question_type": "text_only_question",
        }
        q1.create_question(question=quesdef)

        # now we can publish
        q1.edit(quiz={"published":True})

        # create assignment override to set due and unlock dates and the target student
        quizass = c.course.get_assignment(q1.assignment_id)
        overridedef = {
            "student_ids":list(c.ids[c.netids == nid]),
            "title":'1 student',
            "due_at": duedate.strftime("%Y-%m-%dT%H:%M:%SZ"), #must be UTC
            "unlock_at": unlockat.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        quizass.create_override(assignment_override=overridedef)

    At the end of this process, you will have a quiz that is only assigned to the one student, and which will record the time at which the student accesses the exam PDF.

#. Once the exam period is over, you can now grab the submission times from the upload assignment as usual.  To get the start times, you need to access the quiz submissions.  Based on how we set this up, there should only be one submission per quiz, which makes things easier.

    .. code-block:: python

        subtime = q1.get_submissions()[0].started_at_date

        # if you want to re-localize the time:
        from pytz import timezone
        subtime.astimezone(timezone('US/Eastern'))

#. Here's some more stuff you can do in terms of post-processing.  In this case, I have set up all of the quizzes and the students have completed their exams.  I saved all of the student net ids (in a column labeled ``netid``), assigned questions (for grading purposes), along with the quiz ids (in a column labeled ``quizid``) in a CSV file called ``assigned_questions.csv``.  Now I can use that in order to access all of the individual start times, get all the end times and update the CSV file with this new info.

    .. code-block:: python

        import pandas

        dat = pandas.read_csv(os.path.join(prelimpath,'assigned_questions.csv'))

        # loop through the quiz ids and get the start times
        starts = []
        for qid in dat['quizid'].values:
            print(qid)
            q = c.course.get_quiz(qid)
            subs = q.get_submissions()
            try:
                starts.append(subs[0].started_at_date)
            except IndexError:
                starts.append(None)
        starts = np.array(starts)

        # now get the exam submission times
        # change this to the name of your particular Exam assignment:
        prelim = c.getAssignment('Prelim')
        tmp = prelim.get_submissions()
        subnetids = []
        subtimes = []
        for t in tmp:
            if t.user_id in c.ids:
                subnetids.append(c.netids[c.ids == t.user_id][0])
                if t.submitted_at:
                    subtimes.append(datetime.strptime(
                        t.submitted_at, """%Y-%m-%dT%H:%M:%S%z"""))
                else:
                    subtimes.append(np.nan)
        subnetids = np.array(subnetids)
        subtimes = np.array(subtimes)

        # now calculate each student's test duration
        testtimes = []
        subtimes2 = []
        for j in range(len(dat)):
            try:
                testtimes.append((subtimes[subnetids == dat['netid'].values[j]][0] - starts[j]).seconds/3600)
                subtimes2.append(subtimes[subnetids == dat['netid'].values[j]][0])
            except TypeError:
                testtimes.append(np.nan)
                subtimes2.append(np.nan)
        testtimes = np.array(testtimes)
        subtimes = np.array(subtimes2)

        # add info to CSV and write back to disk
        dat = dat.assign(Start_Time=starts)
        dat = dat.assign(End_Time=subtimes)
        dat = dat.assign(Duration=testtimes)
        dat.to_csv(os.path.join(prelimpath,'assigned_questions.csv'),index=False)

Split Assignments
------------------------

A colleague wanted to give two different assignments to two sub-sections of their class (with a large enrollment, so doing it manually would be very annoying).  They wanted everyone with an even netid to get one assignment, and everyone with an odd netid to get the other.  Since the assignments could be deployed via quizzes, this can be done as a trivial extension of the example above: you generate two quizzes, and use assignment overrides to assign each one to half the course.  It looks something like this:

    .. code-block:: python

        from cornellGrading import cornellGrading
        from datetime import datetime, timedelta
        import numpy as np
        import re

        #set up  course
        c = cornellGrading()
        coursenum = ...
        c.getCourse(coursenum)

        #create two groups split by netid
        netids = c.netids
        names = c.names
        canvasids = c.ids
        netids = netids[names != 'Student, Test']
        canvasids = canvasids[names != 'Student, Test']
        names = names[names != 'Student, Test']
        pn = re.compile('[a-z]+(\d+)')
        numids = np.array([int(pn.match(n).group(1)) for n in netids])
        odds = np.mod(numids,2).astype(bool)
        groups = [list(canvasids[odds]), list(canvasids[~odds])]

        #grab the assignment group you want this to go into
        assgroup  = c.getAssignmentGroup("Assignments")

        # set due date and unlock date
        duedate = c.localizeTime("2021-09-08",duetime="10:00:00")
        unlockat = c.localizeTime("2021-09-04",duetime="17:00:00")

        # generate two quizzes
        quiznames = ["Assignment 1a", "Assignment 1b"]
        for j in range(1,3):
            quizdef = {
            "title": quiznames[j-1],
            "description": "Some text here",
            "quiz_type":"assignment",
            "assignment_group_id": assgroup.id,
            #"time_limit": 180, #this is in minutes
            "shuffle_answers": False,
            "hide_results": 'always',
            "show_correct_answers": False,
            "show_correct_answers_last_attempt": False,
            "allowed_attempts": 1,
            "one_question_at_a_time": False,
            "published": False, #super important!
            "only_visible_to_overrides": True #super important!
            }
            q = c.course.create_quiz(quiz=quizdef)

            #can also add quiz payload here in form of pdf or whatever here

            # now we can publish
            q.edit(quiz={"published":True})

            # create assignment override to set due and unlock dates and the target students
            quizass = c.course.get_assignment(q.assignment_id)
            overridedef = {
                "student_ids":groups[j-1],
                "title":'Group {}'.format(j),
                "due_at": duedate.strftime("%Y-%m-%dT%H:%M:%SZ"), #must be UTC
                "unlock_at": unlockat.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            quizass.create_override(assignment_override=overridedef)

Managing Multiple Sections
----------------------------

As an alternative to the override-based strategy described above, assignments can be deployed in different ways (i.e., different due dates, or different assignment contents) to various subsections of a class by maintaining multiple course sections.  Once again, for a large course, this is quite annoying to maintain via the web interface, but setting up a section with a specific set of students is very straightforward:

    .. code-block:: python

        from cornellGrading import cornellGrading

        c = cornellGrading()
        coursenum = ...  # change to your actual number
        c.getCourse(coursenum)

        # create a new section called "Test Section 1"
        sec = c.course.create_course_section(course_section={"name": "Test Section 1"})

        # create array of userids to add to section.  
        # for example, to add everyone in the course:
        uids = c.ids

        for u in uids:
            sec.enroll_user(u)

Sections can also be deleted by executing ``sec.delete()`` on any section object ``sec``.  To remove a student from a section:

    .. code-block:: python

        uid = ... #user id of student to remove

        # get all enrollments in section
        enrollments = sec.get_enrollments()

        # iterate through enrollments to find student to delete
        for en in enrollments:
            if en.user['id'] == uid:
                en.deactivate("delete")

To get the object for a specific section:

    .. code-block:: python

        secname = "Test Section 1"
        secs = c.course.get_sections()

        for sec in secs:
            if sec.name ==  secname:
                break
        assert secname == sec.name


Uploading Qualtrics Results to Google Drive
----------------------------------------------

When I use the self-grading approach enabled by :py:meth:`~.cornellGrading.setupPrivateHW` and :py:meth:`~.cornellGrading.selfGradingImport`, I like to assign one of my TAs or graders to do spot checks of students' self-assessments (note that it is equally important to look for students who are consistently undervaluing their work as those who are overvaluing their work). The grader obviously needs to see both the assignment submissions (available via Canvas SpeedGrader) as well as the individual question self-assessments.  For the latter, I'd originally implemented the ``sharewith`` keyword for :py:meth:`~.cornellGrading.setupPrivateHW`, but using the Qualtrics web interface to do these spot checks proved to be overly tedious.  However, in the process of calculating scores and uploading them to Canvas, :py:meth:`~.cornellGrading.selfGradingImport` pulls down a full spreadsheet of all user submissions.  If we can automatically upload this to a shared Google Drive folder, that will make everyone's life much easier. Ok. Let's play the how many APIs can we tie together game?

The basics of Google Python API usage are given here: https://developers.google.com/drive/api/v3/quickstart/python. You need the ``google-api-python-client``, ``google-auth-httplib2``, and ``google-auth-oauthlib`` packages.  Then you create a project and enable the relevant API, as described here: https://developers.google.com/workspace/guides/create-project.  In particular, we're going to be using the Google Drive API Scopes: ``.../auth/drive.file`` and ``.../auth/drive.metadata``.  These will require you to create credentials and configure your OAuth consent screen, as described here: https://developers.google.com/workspace/guides/create-credentials.  Create desktop application credentials and download the resulting JSON file. Note that while the documentation is ambiguous on this, you will need to add your own google account as a test user.

In addition to the credentials file, you'll need to create a token, which can similarly be saved to disk so that you only have to do the Google OAuth procedure once.  Here's sample code, mostly based on the quickstart example (https://developers.google.com/drive/api/v3/quickstart/python):

    .. code-block:: python

        import os.path
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.http import MediaFileUpload

        SCOPES = ['https://www.googleapis.com/auth/drive.file',
                  'https://www.googleapis.com/auth/drive.metadata']

        credfile = os.path.join(os.environ['HOME'], 'Downloads', 'credentials.json')
        tokenfile = os.path.join(os.environ['HOME'], 'Downloads', 'token.json')

        creds = None
        if os.path.exists(tokenfile):
            creds = Credentials.from_authorized_user_file(tokenfile, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credfile, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(tokenfile, 'w') as token:
                token.write(creds.to_json())

        service = build('drive', 'v3', credentials=creds)

Note that the token file is specific to the scopes in use.  If you change scopes, you have to recreate the token from scratch.  With this setup complete, all we need to do is find the folder we're want to put things in, and then grab and upload our spreadsheet.  The following assumes that the folder is uniquely named in your Drive:


    .. code-block:: python

        from cornellGrading import cornellGrading
        c = cornellGrading()
        coursenum = ...
        c.getCourse(coursenum)
        c.setupQualtrics()
        hwnum = ...
        res = c.selfGradingImport(hwnum, checkLate=True)

        #find the Google Drive folder
        tmp = service.files().list(q="name = 'Folder Name Goes Here'", spaces='drive',
                                   fields='nextPageToken, files(id, name)',
                                   pageToken=None).execute()
        folderid = tmp['files'][0]['id']

        #upload the file
        media = MediaFileUpload(res[-1], resumable=True)
        file = service.files().create(body={'name':'HW{} Self Assessments.csv'.format(hwnum),
                                            'parents':[folderid]},
                                      media_body=media, fields='id').execute()

And Bob's your uncle. 
