import pandas
import numpy as np
import getpass
import keyring
import time
from datetime import datetime, timedelta
import pytz
import canvasapi
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken
import tempfile
import os
import re
import warnings
from cornellGrading.cornellQualtrics import cornellQualtrics
import urllib.parse
import subprocess
import shutil
import requests
import uuid
from cornellGrading.utils import convalllatex

try:
    from cornellGrading.pandocHTMLParser import pandocHTMLParser
except ImportError:
    pass


class cornellGrading:
    """Class for io methods for Canvas and Qualtrics

    Args:
        canvasurl (str):
            Base url for canvas API calls.
            Defaults to https://canvas.cornell.edu

    """

    def __init__(self, canvasurl="https://canvas.cornell.edu", canvas_token_file=None):
        """Ask for token, store it if you can connect, and
        save resulting canvas object

        Args:
            canvasurl (str):
                Base URL of Canvas
            canvas_token_file (str):
                Full path to text file with canvas token on disk.

        Notes:
            To generate token: in Canvas: Settings>Account>Approved Integrations
            Click '+New Access Token'.  Copy the token.

        .. warning::
            The token will *not* be displayed again. However, it will be saved securely
            in your keychain as soon as the first successful connection is made.

        .. warning::
            Windows users will have likely not be able to copy/paste this token into the
            command prompt.  The best course is to use the canvas_token_file input, or
            just retype it into the prompt.

        """

        token = keyring.get_password("canvas_test_token1", "canvas")
        if token is None:
            if canvas_token_file is None:
                token = getpass.getpass("Enter canvas token:\n")
            else:
                with open(canvas_token_file, "r") as f:
                    tmp = f.read()
                token = tmp.strip()
            try:
                canvas = Canvas(canvasurl, token)
                canvas.get_current_user()
                keyring.set_password("canvas_test_token1", "canvas", token)
                print("Connected.  Token Saved")
            except InvalidAccessToken:
                print("Could not connect. Token not saved.")
        else:
            canvas = Canvas(canvasurl, token)
            canvas.get_current_user()
            print("Connected to Canvas.")

        self.canvas = canvas

    def listCourses(self):
        """Returns a list of courses

        Returns:
            tuple:
                courseStrs (list):
                    Matched ordered list of course strings (str list)
                courseNums (list):
                    Matched ordered list of course numbers (int list)
        """

        crss = self.canvas.get_courses()

        courseStrs = []
        courseNums = []
        for c in crss:
            courseStrs.append(str(c))
            courseNums.append(c.id)

        return courseStrs, courseNums

    def getCourse(self, coursenum):
        """Access course and load all student names, ids and netids

        Args:
            coursenum (int):
                Canvas course number to access. This can be looked
                up in Canvas, or you can look up all your courses:

                .. code-block:: python

                    >>> c = cornellGrading.cornellGrading()
                    >>> for cn in c.canvas.get_courses(): print(cn)

        Returns:
            None

        """

        assert isinstance(coursenum, int), "coursenum must be an int"

        # get the course
        course = self.canvas.get_course(coursenum)
        tmp = course.get_users(include=["enrollments", "test_student"])
        names = []
        ids = []
        netids = []
        for t in tmp:
            isstudent = False
            for e in t.enrollments:
                if e["course_id"] == coursenum:
                    isstudent = e["role"] == "StudentEnrollment"

            if isstudent:
                if not hasattr(t, "login_id"):
                    print(
                        (
                            f"Warning: Skipping {t.sortable_name}: "
                            "is in the course, but not enrolled."
                        )
                    )
                    continue
                names.append(t.sortable_name)
                ids.append(t.id)
                netids.append(t.login_id)

        names = np.array(names)
        ids = np.array(ids)
        netids = np.array(netids)

        self.course = course
        self.names = names
        self.ids = ids
        self.netids = netids

        self.coursename = course.name

    def localizeTime(self, duedate, duetime="17:00:00", tz="US/Eastern"):
        """Helper method for setting the proper UTC time while being
        DST-aware

        Args:
            duedate (str):
                Date in YYYY-MM-DD format
            duetime (str):
                Time in HH-mm-SS format (default 17:00:00)
            tz (str):
                pyzt timezone string (defaults to US/Eastern)

        Returns:
            datetime.datetime:
                A time object. tzinfo will be <UTC>!

        """
        local = pytz.timezone(tz)
        naive = datetime.strptime(duedate + " " + duetime, "%Y-%m-%d %H:%M:%S")
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt

    def listAssignments(self):
        """Returns a list of assignments

        Returns:
            tuple:
                asgnNames (list):
                    Matched ordered list of assignment strings (str list)
                asgnIDs (list):
                    Matched ordered list of assignment IDs (int list)
        """

        asgns = self.course.get_assignments()

        asgnNames = []
        asgnIDs = []
        for a in asgns:
            asgnNames.append(str(a))
            asgnIDs.append(a.id)

        return asgnNames, asgnIDs

    def getAssignment(self, assignmentName):
        """Locate assignment by name

        Args:
            assignmentName (str):
                Name of assignment to return.  Must be exact match.
                To see all assignments do:
                >> for a in c.course.get_assignments(): print(a)

        Returns:
            canvasapi.assignment.Assignment:
                The Assignment object

        """

        tmp = self.course.get_assignments(search_term=assignmentName)
        hw = None
        for t in tmp:
            if t.name == assignmentName:
                hw = t
                break

        assert hw is not None, "Could not find assignment."

        return hw

    def getAssignmentGroup(self, groupName):
        """Locate assignment group by name

        Args:
            groupName (str):
                Name of assignment group to return.  Must be exact match.
                To see all assignments do:
                >> for a in c.course.get_assignment_groups(): print(a)

        Returns:
            canvasapi.assignment.AssignmentGroup:
                The assignment group object

        """

        tmp = self.course.get_assignment_groups()
        group = None
        for t in tmp:
            if t.name == groupName:
                group = t
                break

        assert group is not None, "Could not find assignment group %s" % groupName

        return group

    def createAssignmentGroup(self, groupName):
        """Create assignment group by name

        Args:
            groupName (str):
                Name of assignment group to create. Cannot be name of existing group

        Returns:
            canvasapi.assignment.AssignmentGroup:
                The assignment group object

        """
        tmp = self.course.get_assignment_groups()
        currGroups = [t.name for t in tmp]

        assert groupName not in currGroups, (
            "Assignment group %s already exists" % groupName
        )

        group = self.course.create_assignment_group(name=groupName)

        return group

    def getFolder(self, folderName):
        """Locate folder by name

        Args:
            folderName (str):
                Name of folder to return.  Must be exact match.
                To see all folders do:
                >> for a in c.course.get_folders(): print(a.name)

        Returns:
            canvasapi.folder.Folder:
                The folder object

        """

        tmp = self.course.get_folders()
        folder = None
        for t in tmp:
            if t.name == folderName:
                folder = t
                break

        assert folder is not None, "Could not find folder %s" % folderName

        return folder

    def createFolder(self, folderName, parentFolder="course files", hidden=False):
        """Create folder by name

        Args:
            folderName (str):
                Name of folder to create. Cannot be name of existing folder.
                Name can be nested (i.e., "Homework/HW1"), in which case createFolder
                will be called recursively until the folder is created. Do not put a
                leading slash on paths (they will always be relative to the
                parentFolder).
            parentFolder (str):
                Name of parent folder to create in.
            hidden (bool):
                Whether to toggle to hidden (false by default). If parent folder is
                hidden, you cannot make the subfolder visible.

        Returns:
            canvasapi.folder.Folder:
                The folder object

        Notes:
            Currently, all individual folder names should be unique (i.e., you shouldn't
            have "HW1" in multiple heirarchies, as all folder listing is flattened).

            TODO: Fix this as soon as canvaspai wraps resolve_path
            https://github.com/ucfopen/canvasapi/issues/375

        """

        # recurse down any paths given
        if "/" in folderName:
            folders = folderName.split("/")
            _ = self.createFolder(
                "/".join(folders[:-1]), parentFolder=parentFolder, hidden=hidden
            )
            parentFolder = folders[-2]
            folderName = folders[-1]

        parent = self.getFolder(parentFolder)
        tmp = parent.get_folders()
        subFolders = [t.name for t in tmp]

        if folderName in subFolders:
            # print("Folder %s already exists"%folderName)
            return tmp[int(np.where(np.array(subFolders) == folderName)[0][0])]

        folder = self.course.create_folder(
            folderName, parent_folder_id=str(parent.id), hidden=hidden
        )

        return folder

    def createAssignment(
        self,
        name,
        groupid,
        submission_types=["none"],
        points_possible=10,
        published=True,
        description=None,
        allowed_extensions=None,
        due_at=None,
        unlock_at=None,
        external_tool_tag_attributes=None,
    ):
        """Create an assignment

        Args:
            name (str):
                Name of assignment.
            groupid (int):
                Assignment group to put assignment in.  Get group via
                getAssignmentGroup, and then use group.id attribute.
            submission_types (list):
                See canvas API. Defaults to None.
            points_possible (int):
                duh. If 0, will set grading_type to 'not_graded'.
            published (bool):
                duh (defaults True)
            description (str):
                The html assignment text.  Not added if None (default).
            allowed_extensions (list):
                List of strings for allowed extensions
            due_at (datetime.datetime):
                Due date (not included if None). Must be timezone aware and UTC!
            unlock_at (datetime.datetime):
                Unlock date (not included if None). Must be timezone aware and UTC!
            external_tool_tag_attributes (dict):
                See API docs, which are incredibly unhelpful.  Best to inspect an
                existing external tool assignment object

        Returns:
            canvasapi.assignment.Assignment:
                The assignment object

        Notes:
            https://canvas.instructure.com/doc/api/assignments.html#method.assignments_api.create
        """

        assert isinstance(submission_types, list), "submission_types must be a list."
        if allowed_extensions:
            assert isinstance(
                allowed_extensions, list
            ), "allowed_extensions must be a list."

        # create payload
        assignment = {
            "name": name,
            "submission_types": submission_types,
            "points_possible": points_possible,
            "assignment_group_id": groupid,
            "published": published,
        }

        if points_possible == 0:
            assignment["grading_type"] = "not_graded"
            assignment["submission_types"] = ["not_graded"]

        if description:
            assignment["description"] = description

        if due_at:
            assignment["due_at"] = due_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        if unlock_at:
            assignment["unlock_at"] = unlock_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        if allowed_extensions:
            assignment["allowed_extensions"] = allowed_extensions

        if external_tool_tag_attributes:
            assignment["external_tool_tag_attributes"] = external_tool_tag_attributes

        res = self.course.create_assignment(assignment=assignment)

        return res

    def listPages(self):
        """List all pages in course

        Args:
            None

        Returns:
            list:
                list of strings containing page titles

        """

        pgs = self.course.get_pages()

        pages = []
        for pg in pgs:
            pages.append(pg.title)

        return pages

    def getPage(self, title):
        """Locate page by title

        Args:
            title (str):
                Title of page to return.  Must be exact match.

        Returns:
            canvasapi.module.Module:
                The page object

        """

        tmp = self.course.get_pages()
        pg = None
        for t in tmp:
            if t.title == title:
                pg = t
                break

        assert pg is not None, f"Could not find a page with title {title}."

        return pg

    def createPage(
        self, title, body, editing_roles="teachers", published=False, publish_at=None
    ):
        """Create a Page

        Args:
            title (str):
                Page title
            body (str):
                Content of page (html formatted string)
            editing_roles (str):
                See canvas API. Comma sepeated string, defaults to "teachers"
            published (bool):
                Whether page is published on create (defaults False)
            publish_at (datetime.datetime):
                Publish date (not included if None). Must be timezone aware and UTC! If
                set, overrides any inputs for published. Defaults None.

        Returns:
            canvasapi.page.Page:
                The new page object

        Notes:
            https://canvas.instructure.com/doc/api/pages.html#method.wiki_pages_api.create

            If the title is the same as an existing page, Canvas will automatically
            append "-?" to the title, where ? is an incrementing integer.
        """

        assert isinstance(editing_roles, str), "editing_roles must be a string."
        if publish_at is not None:
            published = False

        wiki_page = {
            "title": title,
            "body": body,
            "editing_roles": editing_roles,
            "published": published,
        }
        if publish_at:
            wiki_page["publish_at"] = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        res = self.course.create_page(wiki_page=wiki_page)

        return res

    def latex2page(
        self,
        fname,
        title,
        folder="Images",
        hidden=True,
        editing_roles="teachers",
        published=False,
        publish_at=None,
        insertPDF=False,
    ):
        """Generate a new canvas page out of a LaTex source file

        Args:
            fname (str):
                Full path of filename to process.  If it has a PDF extension, assume
                that we're looking for the same filename .tex in the same directory.
                Otherwise, assumes that you're giving it the source file.
            title (str):
                Page title
            folder (str):
                Canvas folder to upload any images or other supporting material to.
                Defaults to Images.  If the folder does not exist, it will be created.
                See :py:meth:`cornellGrading.cornellGrading.createFolder` for details.
            hidden (bool):
                If the folder for image upload doesn't exist and needs to be created,
                it will have student visibility set by hidden. Defaults True (not
                visible to students without link).
            editing_roles (str):
                See canvas API. Comma sepeated string, defaults to "teachers"
            published (bool):
                Whether page is published on create (defaults False)
            publish_at (datetime.datetime):
                Publish date (not included if None). Must be timezone aware and UTC! If
                set, overrides any inputs for published. Defaults None.
            insertPDF (bool):
                If true, also include the original file in the page (this assumes that
                fname points at the compiled PDF and not the source).

        Returns:
            canvasapi.page.Page:
                The new page object

        Notes:
            Requires pandoc to be installed and callable!

        .. warning::

            Uploaded files will overwrite files of the same name in the upload folder.

        """

        if insertPDF:
            # grab the folder
            upfolder = self.createFolder(folder, hidden=hidden)
            res = upfolder.upload(fname)
            assert res[0], "File upload failed."

            upurl = res[1]["url"]
            upfname = res[1]["filename"]
            upepoint = upurl.split("/download")[0]

            body = (
                """<p>Downloadable PDF: <a class="instructure_file_link """
                """instructure_scribd_file" title="{0}" href="{1}&amp;wrap=1" """
                """data-api-endpoint="{2}" data-api-returntype="File">{0}</a>"""
                """</p>""".format(upfname, upurl, upepoint)
            )
        else:
            body = ""

        out = self.latex2html(fname, folder=folder, hidden=hidden)
        body += " " + out

        res = self.createPage(
            title,
            body,
            editing_roles=editing_roles,
            published=published,
            publish_at=publish_at,
        )

        return res

    def matlabImport(self, assignmentNum, gradercsv, duedate):
        """MATLAB grader grade import. Create the assignment in the MATLAB
        group and upload grades to it.

        Args:
            assignmentNum (int):
                Number of assignment. Name will be "MATLAB N"
            gradercsv (str):
                Full path to grader csv output.
            duedate (str):
                Due date in format: YYYY-MM-DD (5pm assumed local time)
        Returns:
            None

        Notes:
            In assignment main page: Actions>Report.
            Choose 'Best solution as of today', Output:csv

            If anyone was allowed a late submission, change the Late column entry to 'N'

        .. warning::
            We are assuming that the timezone on your machine matches the timezone
            of the grader submitted time column.  If there is a mismatch, there will be
            errors.
        """

        duedate = self.localizeTime(duedate)

        name = "MATLAB " + str(assignmentNum)
        try:
            ass = self.getAssignment(name)
        except AssertionError:
            mg = self.getAssignmentGroup("MATLAB Assignments")
            ass = self.createAssignment(name, mg.id)

        # process grader output
        grader = pandas.read_csv(gradercsv)

        # on windows, EDT/EST aren't in time.tzname, so we're going to
        # parse the grader timestring manually and then force localization
        timep = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) \S*")
        timetmp = []
        for t in grader["Submitted Time"]:
            tmp = timep.match(t)
            timetmp.append(self.localizeTime(tmp.groups()[0], duetime=tmp.groups()[1]))

        emails = grader["Student Email"].values
        testspassed = grader["Tests Passed"].values.astype(float)
        tottests = grader["Total Tests"].values.astype(float)
        probs = grader["Problem Title"].values
        subtimes = np.array([(duedate - t).total_seconds() for t in timetmp])
        islate = grader["Late Submission?"].values == "Y"

        uprobs = np.unique(probs)
        uemails = np.unique(emails)

        netids = np.array([e.split("@")[0] for e in uemails])
        scores = np.zeros(netids.size)
        for prob in uprobs:
            tottest = np.max(tottests[probs == prob])
            pscores = testspassed[probs == prob] / tottest
            pscores[
                (subtimes[probs == prob] < -5 * 60.0) & (islate[probs == prob])
            ] -= 0.25
            pscores[
                (subtimes[probs == prob] < -5 * 60.0 - 3 * 86400.0)
                & (islate[probs == prob])
            ] = 0
            pscores[pscores < 0] = 0
            pemails = emails[probs == prob]
            for e, s in zip(pemails, pscores):
                scores[uemails == e] += s

        scores *= 10.0 / len(uprobs)

        self.uploadScores(ass, netids, scores)

    def uploadScores(self, ass, netids, scores):
        """Upload scores to Canvas

        Args:
            ass (canvasapi.assignment.Assignment):
                Assignment object
            netids (ndarray of str):
                Array of netids
            scores (ndarray of floats):
                Array of scores matching ordering of netids
        Returns:
            None

        Notes:
            Only netids matching those found in the currently loaded course will be
            uplaoded.
        """

        # let's build up the submission dictionary
        # want API structure of grade_data[<student_id>][posted_grade]
        # this becomes grade_data = {'id (number)':{'posted_grade':'grade (number)',...}
        unmatchedids = []
        grade_data = {}
        for i, s in zip(netids, scores):
            if i == i:
                if i in self.netids:
                    grade_data["%d" % self.ids[self.netids == i]] = {
                        "posted_grade": "%f" % s
                    }
                else:
                    unmatchedids.append(i)

        if unmatchedids:
            print("Could not match netids: %s" % ", ".join(unmatchedids))

        # send payload
        print("Uploading Grades.")
        res = ass.submissions_bulk_update(grade_data=grade_data)
        self.waitForSubmit(res)
        print("Done.")

    def waitForSubmit(self, res):
        """Wait for async result object to finish"""
        while res.query().workflow_state != "completed":
            time.sleep(0.5)

        return

    def setupQualtrics(
        self,
        dataCenter="cornell.ca1",
        qualtricsapi=".qualtrics.com/API/v3/",
        qualtrics_token_file=None,
    ):
        """Save/Load qualtrics api token and verify connection

        Args:
            dataCenter (str):
                Root of datacenter url.  Defaults to Cornell value.
            qualtricsapi (str):
                API url.  Defaults to v3 (current).
            qualtrics_token_file (str):
                Full path to text file with qualtrics token on disk.

        Returns:
            None

        Notes:
            The dataCenter is the leading part of the qualtrics URL before
            "qualtrics.com"
            For an API token, on the qualtrics site, go to:
            Account Settings>Qualtrics IDs
            and click the 'Generate Token' button under API.

        .. warning::
            Windows users will have likely not be able to copy/paste this token into the
            command prompt.  The best course is to use the qualtrics_token_file input,
            or just retype it into the prompt.

        """

        self.qualtrics = cornellQualtrics()

    def genCourseMailingList(self):
        """Generates a qualtrics mailing list with all the netids from the course

        Args:
           None

        Returns:
            None

        """

        # check that this one doesn't already exist
        res = self.qualtrics.getMailingLists()
        assert self.coursename not in [
            el["name"] for el in res.json()["result"]["elements"]
        ], "Mailing list already exists for this course."

        names = np.array([n.split(", ") for n in self.names])
        emails = np.array([nid + "@cornell.edu" for nid in self.netids])
        firstNames = names[:, 1]
        lastNames = names[:, 0]

        mailingListId = self.qualtrics.genMailingList(self.coursename)

        for fN, lN, em in zip(firstNames, lastNames, emails):
            self.qualtrics.addListContact(mailingListId, fN, lN, em)

    def updateCourseMailingList(self):
        """Compares course qualtrics mailing list to current roster and updates
        as needed

        Args:
           None

        Returns:
            None

        """

        # grab current list contacts and ids
        mailingListId = self.qualtrics.getMailingListId(self.coursename)
        tmp = self.qualtrics.getListContacts(mailingListId)

        listids = []
        listemails = []
        for el in tmp:
            listids.append(el["id"])
            listemails.append(el["email"])

        names = np.array([n.split(", ") for n in self.names])
        emails = np.array([nid + "@cornell.edu" for nid in self.netids])
        firstNames = names[:, 1]
        lastNames = names[:, 0]

        # find missing
        missing = list(set(emails) - set(listemails))
        if missing:
            for m in missing:
                ind = emails == m
                self.qualtrics.addListContact(
                    mailingListId, firstNames[ind][0], lastNames[ind][0], m
                )

        # find extraneous names
        extra = list(set(listemails) - set(emails))
        if extra:
            for e in extra:
                self.qualtrics.deleteListContact(
                    mailingListId, np.array(listids)[np.array(listemails) == e][0]
                )

    def genHWSurvey(self, surveyname, nprobs):
        """Create a HW self-grade survey

        Args:
            surveyname (str):
                Name of survey
            nprobs (int):
                Number of problems on the HW


        Returns:
            str:
                Link url to the survey.

        Notes:
            The survey will be created with a mandatory text entry field for the netid
            and then nprobs multiple choice fields for the problems with responses 0-4.
            The survey will be published and activated, so the link should be functional
            as soon as the method returns.

            This survey will be public with an anonymous link.

        .. warning::
            .. deprecated:: 1.0.0
                Use :py:meth:`cornellGrading.cornellGrading.genPrivateHWSurvey` instead.

        """
        warnings.warn(
            "`genHWSurvey` is deprecated and is not the preferred method. "
            "Use `genPrivateHWSurvey` instead",
            DeprecationWarning,
        )

        # generate survey
        surveyId = self.qualtrics.createSurvey(surveyname)

        # add netid question first
        questionDef = {
            "QuestionText": "Enter your netid",
            "DefaultChoices": False,
            "DataExportTag": "Q1",
            "QuestionID": "QID1",
            "QuestionType": "TE",
            "Selector": "SL",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Enter your netid",
            "Validation": {
                "Settings": {
                    "ForceResponse": "ON",
                    "ForceResponseType": "ON",
                    "Type": "None",
                }
            },
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 1,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionText_Unsafe": "Enter your netid",
        }

        self.qualtrics.addSurveyQuestion(surveyId, questionDef)

        # add rubric questions for all problems
        for j in range(1, nprobs + 1):
            questionDef = {
                "QuestionText": "Question %d Score" % j,
                "DataExportTag": "Q%d" % (j + 1),
                "QuestionType": "MC",
                "Selector": "SAVR",
                "SubSelector": "TX",
                "Configuration": {"QuestionDescriptionOption": "UseText"},
                "QuestionDescription": "Question %d Score" % j,
                "Choices": {
                    "1": {"Display": "0"},
                    "2": {"Display": "1"},
                    "3": {"Display": "2"},
                    "4": {"Display": "3"},
                },
                "ChoiceOrder": [1, 2, 3, 4],
                "Validation": {
                    "Settings": {
                        "ForceResponse": "ON",
                        "ForceResponseType": "ON",
                        "Type": "None",
                    }
                },
                "Language": [],
                "QuestionID": "QID%d" % (j + 1),
                "DataVisibility": {"Private": False, "Hidden": False},
                "NextChoiceId": 5,
                "NextAnswerId": 1,
                "QuestionText_Unsafe": "Question %d Score" % j,
            }
            self.qualtrics.addSurveyQuestion(surveyId, questionDef)

        # publish and activate
        self.qualtrics.publishSurvey(surveyId)
        self.qualtrics.activateSurvey(surveyId)

        # genrate link
        link = "https://cornell.qualtrics.com/jfe/form/%s" % surveyId

        return link

    def setupHW(self, assignmentNum, duedate, nprobs):
        """Create qualtrics self-grading survey and Canvas column for
        a homework.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW# Self-Grading
            duedate (str):
                Due date in format: YYYY-MM-DD (5pm assumed local time)
            nprobs (int):
                Number of howmework problems
        Returns:
            None

        .. warning::
            .. deprecated:: 1.0.0
                Use :py:meth:`cornellGrading.cornellGrading.setupPrivateHW` instead.
        """

        warnings.warn(
            "`setupHW` is deprecated and is not the preferred method. "
            "Use `setupPrivateHW` instead",
            DeprecationWarning,
        )

        duedate = self.localizeTime(duedate)

        surveyname = "%s HW%d Self-Grade" % (self.coursename, assignmentNum)
        assname = "HW%d Self-Grading" % assignmentNum

        link = self.genHWSurvey(surveyname, nprobs)

        try:
            sg = self.getAssignmentGroup("Homework Self-Grading")
        except AssertionError:
            sg = self.createAssignmentGroup("Homework Self-Grading")

        desc = """<p>Solutions: </p>
                  <p>Grade yourself against the rubric in the syllabus and enter your
                  scores for each problem here:</p>
                  <p><a class="survey-link ng-binding" href="{0}" target="_blank">{0}
                  </a></p>
                  <p>Be sure to enter your correct netid or you will not receive
                  credit.</p>""".format(
            link
        )

        _ = self.createAssignment(
            assname,
            sg.id,
            points_possible=0,
            description=desc,
            due_at=duedate + timedelta(days=7),
            unlock_at=duedate + timedelta(days=3),
        )

    def uploadHW(
        self,
        assignmentNum,
        duedate,
        hwfile,
        totscore=10,
        unlockDelta=None,
        injectText=False,
        allowed_extensions=None,
        moduleName=None,
        matlabParts=0,
    ):
        """Create a Canvas assignment, set the duedae, upload an associated
        PDF and link in the assignment description, set the number of points, and
        (optionally), set an unlock time and inject the assignment text into the
        description along with the PDF link.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW# Self-Grading
            duedate (str):
                Due date in format: YYYY-MM-DD (5pm assumed local time)
            hwfile (str):
                Full path to homework file
            totscore (int, float):
                Total number of points for the assignment. Defaults to 10.
            unlockDelta (float):
                Unlock this number of days before due date. Defaults to None,
                which makes the assignment initially unlocked.
            injectText (bool):
                If True, will attempt to locate the tex file associated with the
                provided PDF in hwfile (looking in the same directory), will then
                convert to Canvas compatible html using pandoc, and add to the
                assignment description.  Requires pandoc to be installed and callable!
            allowed_extensions (list):
                List of strings for allowed extensions
            moduleName (str):
                Name of module to add assignment object to.
            matlabParts (int):
                If non-zero, this is a MATLAB assignment, and the relevant number of
                external tool Mathworks grader assignments will be created in the MATLAB
                Assignment group.

        Returns:
            canvasapi.assignment.Assignment

        Notes:
            All related files will be placed in path "Homeworks/HW?" where ? is the
            assignmentNum.  Folders will be created as needed and will all be hidden.

        """

        duedate = self.localizeTime(duedate)

        hwname = "HW%d" % assignmentNum
        if matlabParts > 0:
            hwname = "MATLAB " + hwname

        if matlabParts > 1:
            hwnames = []
            for j in range(1, matlabParts + 1):
                hwnames.append("{0} Part {1}".format(hwname, j))
        else:
            hwnames = [hwname]

        # ensure that assignment(s) don't already exist
        for h in hwnames:
            try:
                hw = self.getAssignment(h)
                alreadyExists = True
            except AssertionError:
                alreadyExists = False

            assert not (alreadyExists), "%s already exists" % h

        # grab assignment group, homeworks folder and upload and set description
        if matlabParts > 0:
            hwgroup = self.getAssignmentGroup("MATLAB Assignments")
            desc = None
            external_tool_tag_attributes = {
                "url": "https://lms-grader.mathworks.com/launch",
                "new_tab": False,
            }
            submission_types = ["external_tool"]
        else:
            hwgroup = self.getAssignmentGroup("Assignments")

            # grab homeworks folder
            hwfoldername = "Homeworks/" + hwname
            hwfolder = self.createFolder(hwfoldername, hidden=True)

            res = hwfolder.upload(hwfile)
            assert res[0], "HW Upload failed."

            hwurl = res[1]["url"]
            hwfname = res[1]["filename"]
            hwepoint = hwurl.split("/download")[0]

            desc = (
                """<p>Downloadable Assignment: <a class="instructure_file_link """
                """instructure_scribd_file" title="{0}" href="{1}&amp;wrap=1" """
                """data-api-endpoint="{2}" data-api-returntype="File">{0}</a></p>""".format(
                    hwfname, hwurl, hwepoint
                )
            )

            if injectText:
                out = self.latex2html(hwfile, folder=hwfoldername)
                desc = desc + " " + out

            external_tool_tag_attributes = None
            submission_types = ["online_upload"]

        # calculate unlock date if given delta
        if unlockDelta:
            unlockAt = duedate - timedelta(days=unlockDelta)
        else:
            unlockAt = None

        # create assignments as needed
        for hwname in hwnames:
            hw = self.createAssignment(
                hwname,
                hwgroup.id,
                points_possible=10,
                description=desc,
                due_at=duedate,
                unlock_at=unlockAt,
                submission_types=submission_types,
                allowed_extensions=allowed_extensions,
                external_tool_tag_attributes=external_tool_tag_attributes,
            )

            if moduleName:
                module = self.getModule(moduleName)
                self.add2module(module, hw.name, hw)

        return hw

    def latex2html(self, fname, folder="Images", hidden=True):
        """Convert LaTex source into Canvas-compatible html
        and upload any required figures along the way

        Args:
            fname (str):
                Full path of filename to process.  If it has a PDF extension, assume
                that we're looking for the same filename .tex in the same directory.
                Otherwise, assumes that you're giving it the source file.
            folder (str):
                Canvas folder to upload any images or other supporting material to.
                Defaults to Images.  If the folder does not exist, it will be created.
                See createFolder for details.
            hidden (bool):
                If the folder for image upload doesn't exist and needs to be created,
                it will have student visibility set by hidden. Defaults True (not
                visible to students without link).

        Returns:
            list:
                List of strings of fully formatted html corresponding to the <body>
                block of a webpage

        Notes:
            Requires pandoc to be installed and callable!

        .. warning::
            Uploaded files will overwrite files of the same name in the upload folder.
        """

        # won't work if we don't have pandoc
        assert shutil.which("pandoc"), (
            "Cannot locate pandoc. Please visit https://pandoc.org/installing.html"
            "for installation instructions."
        )

        # going to assume that the pdf file is located in the working dir with the tex
        # and everything else that's needed for compilation
        hwd, hwf = os.path.split(fname)

        if hwf.split(os.extsep)[1].lower() == "pdf":
            texf = hwf.split(os.extsep)[0] + os.extsep + "tex"
        else:
            texf = hwf
        assert os.path.exists(os.path.join(hwd, texf)), (
            "Cannot locate LaTeX source %s" % texf
        )

        # all new products are going into the system tmp dir
        tmpdir = tempfile.gettempdir()
        htmlf = os.path.join(tmpdir, hwf.split(os.extsep)[0] + os.extsep + "html")

        # preflight: let's replace tex commands that Canvas can't handle
        texsubdict = {
            r"\\nicefrac": r"\\frac",
            r"\\ensuremath": r"",
            r"\\leftmoon": r"\\mathrm{Moon}",
            r"\\Venus": r"Venus",
        }

        # read orig tex
        with open(os.path.join(hwd, texf)) as f:
            lines = f.readlines()

        # parse orig tex, flattening any inputs
        inputp = re.compile(r"\\input{([^}]+)}")
        linesout = []
        for ll in lines:
            # if line contains and input, repace it with the input.
            if inputp.search(ll):
                tmp = inputp.search(ll)
                with open(os.path.join(hwd, tmp.group(1))) as f:
                    newlines = f.readlines()

                ll = ll.replace(tmp.group(0), " ".join(newlines))

            # apply substitutions
            for key, val in texsubdict.items():
                ll = re.sub(key, val, ll)

            linesout.append(ll)

        with open(os.path.join(tmpdir, texf), "w") as f:
            for ll in linesout:
                f.write(ll)

        # run pandoc
        if not (hwd):
            hwd = os.path.curdir

        pandoc_comm = [
            "pandoc",
            os.path.join(tmpdir, texf),
            "-s",
            "--webtex",
            "-o",
            htmlf,
            "--default-image-extension=png",
        ]

        if shutil.which("pandoc-crossref") is not None:
            pandoc_comm += ["--filter", "pandoc-crossref"]
            have_crossref = True
        else:
            have_crossref = False

        _ = subprocess.run(
            pandoc_comm,
            cwd=hwd,
            check=True,
            capture_output=True,
        )

        assert os.path.exists(htmlf), "Cannot locate html output %s" % htmlf

        # read result
        with open(htmlf) as f:
            lines = f.readlines()

        upfolder = self.createFolder(folder, hidden=hidden)

        # latex conversion
        p = re.compile(r'src="https://latex.codecogs.com/png.latex\?(.*?)"')

        def convlatex(x):
            return re.sub(x.groups()[0], urllib.parse.quote(x.groups()[0]), x.group())

        # now we need to parse the result and fix things
        parser = pandocHTMLParser(hwd, upfolder)
        out = []
        for line in lines:
            parser.feed(line)
            if parser.inBody:
                tmp = p.sub(convlatex, line)

                if (len(parser.figcaptions) > 0) and not (have_crossref):
                    figcap = parser.figcaptions.pop()
                    tmp = re.sub(r'alt=""', r'alt="{0}"'.format(figcap), tmp)

                if parser.spanDefs:
                    for cl, val in parser.spanDefs.items():
                        tmp = re.sub(cl, 'style="{}"'.format(val), tmp)

                if parser.inNestedOL:
                    tmp = re.sub(r"<ol>", r'<ol type="a">', tmp)

                out.append(tmp)

        # put everything together into a isngle string
        out = out[1:]
        out = " ".join(out)

        # global replacements
        repdict = {
            r'class="math display"': r'style="display: block; text-align: center; margin: 0.5rem auto;"',
            r'img[\s]*style="vertical-align:middle"': r'img class="equation_image"',
            r'src="https://latex.codecogs.com/png.latex\?': r'src="https://canvas.cornell.edu/equation_images/',
            r"<figcaption": '<figcaption style="text-align: center;"',
        }

        for k, v in repdict.items():
            out = re.sub(k, v, out)

        # handle all uploaded figures:
        while parser.imagesUploaded:
            imup = parser.imagesUploaded.pop()
            canvasimurl = (
                r'src="https://canvas.cornell.edu{0}/preview" '
                r'data-api-endpoint="https://canvas.cornell.edu/api/'
                r'v1{0}" data-api-returntype="File" '.format(imup["url"])
            )
            out = re.sub(r'src="{0}"'.format(imup["orig"]), canvasimurl, out)

        # figures less than 100% width get centered:
        p2 = re.compile(r'style="([\S]*)?(?=")"')

        def convwidth(x):
            return re.sub(
                x.group(1),
                f"{x.group(1)}; display: block; margin-left: auto; margin-right: auto;",
                x.group(),
            )

        out = p2.sub(convwidth, out)

        # handle any labeled equations
        if parser.eqlabels:
            for label, (eqnum, labelstr) in parser.eqlabels.items():
                enclabel = urllib.parse.quote(urllib.parse.quote(labelstr))

                # for every equation image with a label, find it, and replace with a
                # span with an equation number
                imtag = re.search(
                    rf'(<img class="equation_image"[\s]*src="https://canvas.cornell.edu/equation_images/([\w%.-]*?)(?={enclabel})([\s\S]*?)(?=/>)/>)',
                    out,
                )

                imspan = (
                    r'<span style="margin: 1ex auto; display: table; '
                    r'text-align: center; width: 100%; vertical-align: middle;"> '
                    r'{0}<span id="{1}" style="display: table-cell; '
                    r'text-align: left; vertical-align: middle;">'
                    r"({2})</span></span>"
                ).format(imtag.groups()[0], label, eqnum)

                out = out.replace(imtag.group(), imspan)

                # if encoded or unencoded label in string, kill them
                out = out.replace(labelstr, "")
                out = out.replace(enclabel, "")

                # replace instances of [label] with eq num
                out = out.replace("[{}]".format(label), "{}".format(eqnum))

        # handle any figure labels
        if (len(parser.figLabels) > 0) and not (have_crossref):
            for cl, val in parser.figLabels.items():
                out = out.replace(cl, val)

        return out

    def genPrivateHWSurvey(self, surveyname, nprobs, scoreOptions=None, ecprobs=[]):
        """Create a HW self-grade survey and make private

        Args:
            surveyname (str):
                Name of survey
            nprobs (int):
                Number of problems on the HW. Set to 0 for total score only.
            scoreOptions (list of ints):
                Possible responses to each question.  Defaults to 0,1,2,3
            ecprobs (list of ints):
                Problems to be marked as extra credit (problem numbering starts at 1)

        Returns:
            str:
                Unique survey ID

        Notes:
            The survey will be created with nprobs multiple choice fields for the
            problems with responses 0-4.
            The survey will be published and activated, but made private.  No
            distributions will be created.
        """

        assert isinstance(nprobs, int), "nprobs must be an int"
        assert nprobs >= 0, "nprobs must be a positive integer (or zero)"

        surveyId = self.qualtrics.createSurvey(surveyname)

        if scoreOptions is None:
            scoreOptions = [0, 1, 2, 3]
        assert isinstance(ecprobs, list), "ecprobs must be a list"

        choices = {}
        for j, choice in enumerate(scoreOptions):
            choices[str(j + 1)] = {"Display": str(choice)}
        choiceOrder = list(range(1, len(choices) + 1))

        if nprobs == 0:
            questionDef = {
                "QuestionText": "HW Score",
                "DataExportTag": "Q1",
                "QuestionType": "MC",
                "Selector": "SAVR",
                "SubSelector": "TX",
                "Configuration": {"QuestionDescriptionOption": "UseText"},
                "QuestionDescription": "HW Score",
                "Choices": choices,
                "ChoiceOrder": choiceOrder,
                "Validation": {
                    "Settings": {
                        "ForceResponse": "ON",
                        "ForceResponseType": "ON",
                        "Type": "None",
                    }
                },
                "Language": [],
                "QuestionID": "QID1",
                "DataVisibility": {"Private": False, "Hidden": False},
                "NextChoiceId": 5,
                "NextAnswerId": 1,
                "QuestionText_Unsafe": "HW Score",
            }
            self.qualtrics.addSurveyQuestion(surveyId, questionDef)

        # add rubric questions for all problems
        for j in range(1, nprobs + 1):
            if j in ecprobs:
                desc = "Question %d (Extra Credit) Score" % j
            else:
                desc = "Question %d Score" % j

            questionDef = {
                "QuestionText": desc,
                "DataExportTag": "Q%d" % (j + 1),
                "QuestionType": "MC",
                "Selector": "SAVR",
                "SubSelector": "TX",
                "Configuration": {"QuestionDescriptionOption": "UseText"},
                "QuestionDescription": desc,
                "Choices": choices,
                "ChoiceOrder": choiceOrder,
                "Validation": {
                    "Settings": {
                        "ForceResponse": "ON",
                        "ForceResponseType": "ON",
                        "Type": "None",
                    }
                },
                "Language": [],
                "QuestionID": "QID%d" % (j + 1),
                "DataVisibility": {"Private": False, "Hidden": False},
                "NextChoiceId": 5,
                "NextAnswerId": 1,
                "QuestionText_Unsafe": desc,
            }
            self.qualtrics.addSurveyQuestion(surveyId, questionDef)

        # publish and activate
        self.qualtrics.publishSurvey(surveyId)
        self.qualtrics.activateSurvey(surveyId)

        # make private
        self.qualtrics.makeSurveyPrivate(surveyId)

        return surveyId

    def setupPrivateHW(
        self,
        assignmentNum,
        nprobs,
        ecprobs=[],
        sharewith=None,
        scoreOptions=None,
        createAss=False,
        solutions=None,
        injectText=False,
        selfGradeDueDelta=7,
        selfGradeReleasedDelta=3,
    ):
        """Create qualtrics self-grading survey, individualized links distribution,
        a Canvas post for where the solutions will go, and injects links into assignment
        columns.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW# Self-Grading
            nprobs (int):
                Number of howmework problems
            ecprobs (list of ints):
                Problems to be marked as extra credit (problem numbering starts at 1)
            sharewith (str):
                Qualtrics id to share survey with. Defaults to None
            scoreOptions (list of ints):
                Possible responses to each question.  Defaults to 0,1,2,3
            createAss (bool):
                Whether to create a self-grading assignment in Canvas (defaults False)
            solutions (str):
                Full path to solutions file to upload.
            injectText (bool):
                If True, will attempt to locate the tex file associated with the
                provided PDF in solutions (looking in the same directory), will then
                convert to Canvas compatible html using pandoc, and add to the
                assignment description.  Requires pandoc to be installed and callable!
            selfGradeDueDelta (float):
                Days after initial hw duedate that self-grading is due
            selfGradeReleasedDelta (float):
                Days after initial hw duedate that self-grading (and solutions) are
                released.


        Returns:
            None

        """

        # create survey and distribution
        surveyname = "%s HW%d Self-Assessment" % (self.coursename, assignmentNum)
        surveyId = self.genPrivateHWSurvey(
            surveyname, nprobs, ecprobs=ecprobs, scoreOptions=scoreOptions
        )

        if sharewith:
            self.qualtrics.shareSurvey(surveyId, sharewith)

        mailingListId = self.qualtrics.getMailingListId(self.coursename)
        dist = self.qualtrics.genDistribution(surveyId, mailingListId)

        distnetids = np.array([d["email"].split("@")[0] for d in dist])

        # grab the original assignment and all the submissions
        hwname = "Written HW%d" % assignmentNum
        hw = self.getAssignment(hwname)
        subs = hw.get_submissions()

        # inject links to all users in distribution
        missing = []
        for s in subs:
            if self.netids[self.ids == s.user_id][0] in distnetids:
                link = dist[
                    np.where(distnetids == self.netids[self.ids == s.user_id])[0][0]
                ]["link"]
                _ = s.edit(
                    comment={
                        "text_comment": "One-time link to self-grading survey:\n %s"
                        % link
                    }
                )
            else:
                missing.append(self.netids[self.ids == s.user_id][0])

        if missing:
            print("Could not identify links for the following users:")
            print("\n".join(missing))

        if createAss:
            duedate = datetime.strptime(hw.due_at, """%Y-%m-%dT%H:%M:%S%z""")
            assname = "HW%d Self-Grading" % assignmentNum

            # grab self-grading group
            try:
                sg = self.getAssignmentGroup("Homework Self-Grading")
            except AssertionError:
                sg = self.createAssignmentGroup("Homework Self-Grading")

            # grab homeworks folder
            hwfoldername = "Homeworks/HW%d" % assignmentNum
            hwfolder = self.createFolder(hwfoldername, hidden=True)

            # upload
            res = hwfolder.upload(solutions)
            assert res[0], "Solutions Upload failed."

            solurl = res[1]["url"]
            solfname = res[1]["filename"]
            solepoint = solurl.split("/download")[0]

            desc = (
                """<p>Solutions: <a class="instructure_file_link """
                """instructure_scribd_file" title="{0}" href="{1}&amp;wrap=1" """
                """data-api-endpoint="{2}" data-api-returntype="File">{0}</a></p>
                    <p>Grade yourself against the rubric in the syllabus and enter your
                    scores for each problem by following the link in the comments on
                    your original submission.</p>""".format(
                    solfname, solurl, solepoint
                )
            )

            if injectText:
                out = self.latex2html(solutions, folder=hwfoldername)
                desc += " " + out

            _ = self.createAssignment(
                assname,
                sg.id,
                points_possible=0,
                description=desc,
                due_at=duedate + timedelta(days=selfGradeDueDelta),
                unlock_at=duedate + timedelta(days=selfGradeReleasedDelta),
            )

    def selfGradingImport(
        self,
        assignmentNum,
        ecscore=3,
        checkLate=True,
        latePenalty=0.25,
        maxDaysLate=3,
        noUpload=False,
        saveDir=None,
    ):
        """Qualtrics self-grading survey import.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW#
            ecscore (int):
                Extra credit score (defaults to 3)
            checkLate (bool):
                Check for late submissions (defaults true)
            latePenalty (float):
                Fraction of score to remove for lateness (defaults to 0.25).
                Must be in (0,1).
            maxDaysLate (float):
                After this number of days past deadline, HW gets zero. Defaults to 3.
            noUpload (bool):
                Don't upload if True (defaults False)
            saveDir (str):
                Save path for raw survey output.  Defaults to None (in which case it
                goes to the system tmp dir)
        Returns:
            tuple:
                netids (str array):
                    Student netids
                scores (float array):
                    Student scores
                surveyfile (str):
                    Full path to survey download


        Notes:
            To whitelist late submissions, in Canvas gradebook, click on the submission,
            click the right arrow, and then set status to 'None'.

        """

        # grab the canvas column
        hwname = "HW%d" % assignmentNum
        hw = self.getAssignment(hwname)
        duedate = datetime.strptime(hw.due_at, """%Y-%m-%dT%H:%M:%S%z""")
        totscore = hw.points_possible

        # grab the survey
        surveyname = "%s HW%d Self-Grade" % (self.coursename, assignmentNum)
        surveyId = self.qualtrics.getSurveyId(surveyname)
        tmpdir = self.qualtrics.exportSurvey(surveyId, saveDir=saveDir)

        if ":" in surveyname:
            surveyname = surveyname.replace(":", "_")
        surveyfile = os.path.join(tmpdir, surveyname + ".csv")
        assert os.path.isfile(surveyfile), "Survey results not where expected."

        qualtrics = pandas.read_csv(surveyfile, header=[0, 1, 2])
        # find netid and question cols in Qualtrics
        qnetidcol = qualtrics.columns.get_level_values(0)[
            np.array(
                ["Enter your netid" in c for c in qualtrics.columns.get_level_values(1)]
            )
        ]

        # if not netid col, assume that this is a private survey and grab the email col
        if qnetidcol.empty:
            qnetids = np.array(
                [e[0].split("@")[0] for e in qualtrics["RecipientEmail"].values]
            )
        else:
            qnetids = np.array([n[0].lower() for n in qualtrics[qnetidcol].values])

        # calculate total scores
        quescolinds = np.array(
            [
                "Question" in c and "Score" in c
                for c in qualtrics.columns.get_level_values(1)
            ]
        )
        if np.any(quescolinds):
            quescols = qualtrics.columns.get_level_values(0)[quescolinds]
            quesnames = qualtrics.columns.get_level_values(1)[quescolinds]
            isec = np.array(["Extra Credit" in c for c in quesnames])

            scores = (
                qualtrics[quescols[~isec]].values.sum(axis=1)
                / 3.0
                / len(quescols[~isec])
                * totscore
            )
            if np.any(isec):
                scores += (
                    qualtrics[quescols[isec]].values.sum(axis=1)
                    / 3.0
                    / len(quescols[isec])
                    * ecscore
                )
        else:
            totscorecol = qualtrics.columns.get_level_values(0)[
                np.array(
                    ["HW Score" in c for c in qualtrics.columns.get_level_values(1)]
                )
            ]
            assert not (totscorecol.empty), "Cannot locate any scores."
            scores = np.array(qualtrics[totscorecol].values).astype(float)

        if checkLate:
            # get submission times
            tmp = hw.get_submissions()
            subnetids = []
            subtimes = []
            lates = []
            for t in tmp:
                if t.user_id in self.ids:
                    subnetids.append(self.netids[self.ids == t.user_id][0])
                    if t.submitted_at:
                        subtime = datetime.strptime(
                            t.submitted_at, """%Y-%m-%dT%H:%M:%S%z"""
                        )
                        tdelta = duedate - subtime
                        subtimes.append(tdelta.total_seconds())
                    else:
                        subtimes.append(np.nan)
                    lates.append(t.late)

            subnetids = np.array(subnetids)
            subtimes = np.array(subtimes)
            lates = np.array(lates)

            # update scores based on lateness
            for j, i in enumerate(qnetids):
                if (i == i) and (i in self.netids):
                    if np.isnan(subtimes[subnetids == i][0]):
                        scores[j] = 0
                    else:
                        # if late take away 25% of the totscore
                        if (subtimes[subnetids == i][0] < -5 * 60.0) and lates[
                            subnetids == i
                        ][0]:
                            scores[j] -= totscore * latePenalty
                        # if more than maxDaysLate, you get NOTHING! good day, sir!
                        if (
                            subtimes[subnetids == i][0]
                            < -5 * 60.0 - maxDaysLate * 86400.0
                        ):
                            scores[j] = 0
            scores[scores < 0] = 0

        if not (noUpload):
            self.uploadScores(hw, qnetids, scores)

        return qnetids, scores, surveyfile

    def getGroups(self, outfile=None):
        """Create a csv file of group membership

        Args:
            outfile (str):
                Full path to output file. If not set, defaults to coursename Groups.csv
                in current directory.

        Returns:
            None

        Notes:
            This functionality is targeted at generating zoom breakout rooms, which is
            why the csv headers are what they are.

        """

        if outfile is None:
            outfile = "{} Groups.csv".format(self.coursename)

        grps = self.course.get_groups()

        grpname = []
        grpmember = []
        for grp in grps:
            usrs = grp.get_users()
            for usr in usrs:
                grpname.append(grp.name)
                grpmember.append(usr.login_id + "@cornell.edu")

        out = pandas.DataFrame(
            {"Pre-assign Room Name": grpname, "Email Address": grpmember}
        )
        out.to_csv(outfile, index=False)

    def dir2page(
        self,
        path,
        title,
        extensions=None,
        prefix="",
        folder="Lecture Notes",
        hidden=True,
        editing_roles="teachers",
        published=False,
    ):
        """Generate new canvas page from a local dir with choice of file extensions

        Args:
            path (str):
                Full path of the directory to process
            title (str):
                Page title
            extensions (list):
                List of strings for extensions to upload
            prefix (str):
                Any HTML text to put before the links
            folder (str):
                Canvas folder to upload the files or other supporting material to.
                Defaults to Images.  If the folder does not exist, it will be created.
                See :py:meth:`cornellGrading.cornellGrading.createFolder` for details.
            hidden (bool):
                If the folder for image upload doesn't exist and needs to be created,
                it will have student visibility set by hidden. Defaults True (not
                visible to students without link).
            editing_roles (str):
                See canvas API. Comma sepeated string, defaults to "teachers"
            published (bool):
                Whether page is published on create (defaults False)

        Returns:
            canvasapi.page.Page:
                The new page object

        .. warning::
            Uploaded files will overwrite files of the same name in the upload folder.

        """

        # get files from path with extensions
        files = os.listdir(path)
        if extensions:
            files = [f for f in files if any(f.endswith(ext) for ext in extensions)]

        # grab the folder to put files in
        upfolder = self.createFolder(folder, hidden=hidden)

        # upload and link to files
        body = prefix
        for fname in files:

            res = upfolder.upload(os.path.join(path, fname))
            assert res[0], f"File {fname} upload failed."
            print(f"Uploaded {fname}.")

            upurl = res[1]["url"]
            upfname = res[1]["filename"]
            upepoint = upurl.split("/download")[0]

            body += (
                """<p>File: <a class="instructure_file_link """
                """instructure_scribd_file" title="{0}" href="{1}&amp;wrap=1" """
                """data-api-endpoint="{2}" data-api-returntype="File">{0}</a>"""
                """</p>""".format(upfname, upurl, upepoint)
            )

        res = self.createPage(
            title, body, editing_roles=editing_roles, published=published
        )
        print(f"Created page '{title}'.")

        return res

    def listModules(self):
        """List all modules in course

        Args:
            None
        Returns:
            list:
                list of strings containing module names

        """

        mdls = self.course.get_modules()

        modules = []
        for md in mdls:
            modules.append(md.name)

        return modules

    def getModule(self, moduleName):
        """Locate module by name

        Args:
            moduleName (str):
                Name of module to return.  Must be exact match.
                To see all assignments do:
                >> for a in c.listModules(): print(a)
        Returns:
            canvasapi.module.Module:
                The Module object

        """

        tmp = self.course.get_modules()
        md = None
        for t in tmp:
            if t.name == moduleName:
                md = t
                break

        assert md is not None, f"Could not find module {moduleName}."

        return md

    def add2module(self, module, title, obj, indent=0, position="bottom"):
        """Adds an object to a module

        Args:
            module (canvasapi.Module):
                The module to add the item to
            title (str):
                Title of the module item
            obj (canvasapi.CanvasObject):
                The object to be added to the module. Tested with Page and Assignment
                so far. Type should be one of [File, Page, Discussion, Assignment, Quiz,
                SubHeader, ExternalUrl, ExternalTool].
            indent (int):
                Item indent level (defaults to zero)
            position (str, int, or None):
                If None, add new item in the module's default position
                (typically at the bottom, but, confusingly, sometimes at the top). If
                a string, must be either 'top' or 'bottom' (case-isensitive). If int,
                this is interpreted as the desired position. Defaults to 'bottom'.

        """

        obj_type = type(obj).__name__

        item = {"title": title, "type": obj_type, "indent": int(indent)}
        if obj_type == "Page":
            item["page_url"] = obj.url
        else:
            item["content_id"] = str(obj.id)

        if position is not None:
            assert isinstance(
                position, (str, int, float)
            ), "position input may only be a str or an int"
            if isinstance(position, str):
                assert position.lower() in [
                    "top",
                    "bottom",
                ], "position strings must be either 'top' or 'bottom'"

                if position.lower() == "bottom":
                    # module may have been updated, so let's find the true largest
                    # position
                    maxpos = 0
                    for mi in module.get_module_items():
                        if mi.position > maxpos:
                            maxpos = mi.position

                    position = maxpos + 1
                else:
                    minpos = 999999
                    for mi in module.get_module_items():
                        if mi.position < minpos:
                            minpos = mi.position

                    position = minpos

            else:
                position = int(position)

            item["position"] = position

        module.create_module_item(item)

    def addNewQuizItem(self, quizid, item):
        """

        Args:
            quizid (int):
                ID of New Quiz to add item to.\
            item (dict):
                Item payload dictionary.  This is the contents of the 'item' key in the
                JSON payload. For details, see:
                https://canvas.instructure.com/doc/api/new_quiz_items.html#Question+Types-appendix

        """

        full_url = "{}{}".format(
            self.course._requester.new_quizzes_url,
            "courses/{}/quizzes/{}/items".format(self.course.id, quizid),
        )
        headers = {
            "Authorization": "Bearer {}".format(self.course._requester.access_token)
        }

        r = requests.post(full_url, json={"item": item}, headers=headers)
        assert r.status_code == 200

    def genHomeworkName(self, assignmentNum, preamble=""):
        """Synthesize assignment name based on number and optional preamble

        Args:
            assignmentNum (int):
                Assignment names will be of the form "[preamble] HW#"
                where # is `assignmentNum`. See also `preamble` input.

            preamble (str):
                If not "", then assignment name will be "[preamble] HW#". Otherwise,
                name will be "HW#".  Defaults to ""

        Returns:
            tuple:
                hwname (str):
                    Full assignment name
                hw (canvasapi.assignment.Assignment):
                    Assignment object
        """

        # if preamble set, make sure it ends in a space
        if preamble != "":
            preamble = f"{preamble.strip()} "

        # generate the name and grab the assignment
        hwname = f"{preamble}HW{assignmentNum}"

        return hwname

    def getHomework(self, assignmentNum, preamble=""):
        """Retrieve assignment based on number and optional preamble

        Args:
            assignmentNum (int):
                Assignment names will be of the form "[preamble] HW#"
                where # is `assignmentNum`. See also `preamble` input.

            preamble (str):
                If not "", then assignment name will be "[preamble] HW#". Otherwise,
                name will be "HW#".  Defaults to ""

        Returns:
            tuple:
                hwname (str):
                    Full assignment name
                hw (canvasapi.assignment.Assignment):
                    Assignment object
        """

        # get the name and grab the assignment
        hwname = self.genHomeworkName(assignmentNum, preamble=preamble)
        hw = self.getAssignment(hwname)

        return hwname, hw

    def setupNewQuizSelfAssessment(
        self,
        assignmentNum,
        nprobs,
        solfile,
        npoints=3,
        preamble="",
        selfGradeDueDelta=7,
        selfGradeReleasedDelta=3,
        extraQuestions=[],
    ):
        """Create a page with reference solutions and a New Quiz linking to the page for
        student self-assemssent.

        Args:
            assignmentNum (int):
                Number of assignment.
                See :py:meth:`cornellGrading.cornellGrading.getHomework` for details.
            nprobs (int):
                Number of howmework problems
            solfile (str):
                Full path to solutions file to upload
            npoints (int):
                Number of points each question is scored out of. Defaults to 3.
            preamble (str):
                Preamble for all naming.
                See :py:meth:`cornellGrading.cornellGrading.getHomework` for details.
            selfGradeDueDelta (float):
                Days after initial hw duedate that self-grading is due
            selfGradeReleasedDelta (float):
                Days after initial hw duedate that self-grading (and solutions) are
                released.
            extraQuestions (list(dict)):
                List of dicts defining additional questions to ask

        Returns:
            None

        """

        # ensure solutions file exists
        assert os.path.exists(solfile)

        # get original assignment
        hwname, hw = self.getHomework(assignmentNum, preamble=preamble)

        # figure out all dates
        duedate = datetime.strptime(hw.due_at, """%Y-%m-%dT%H:%M:%S%z""")
        unlockdate = duedate + timedelta(days=selfGradeReleasedDelta)
        selfgradeduedate = unlockdate + timedelta(days=selfGradeDueDelta)

        # generate reference solutions page
        pagename = f"{hwname} Solutions"

        hwfoldername = "Homeworks/HW%d" % assignmentNum
        _ = self.createFolder(hwfoldername, hidden=True)

        p = self.latex2page(
            solfile,
            pagename,
            folder=hwfoldername,
            publish_at=unlockdate,
        )

        # get self-assessment assignment group and generate new quiz there
        assgrp = self.getAssignmentGroup("Homework Self-Assessment")

        instructions = (
            rf"<p>{hwname} Solutions are available here: "
            rf'<a title={pagename} href="{p.html_url.split(".edu")[-1]}" '
            rf'data-course-type="wikiPages">{pagename}</a>. Check your work and score '
            r" yourself based on the rubric in the syllabus.</p>"
        )

        nq = self.course.create_new_quiz(
            quiz={
                "title": f"{hwname} Self-Assessment",
                "assignment_group_id": assgrp.id,
                "points_possible": hw.points_possible,
                "due_at": selfgradeduedate,
                "unlock_at": unlockdate,
                "grading_type": "points",
                "instructions": instructions,
            }
        )

        # create item
        item = self.genNpointNewQuizItem(npoints)

        # add new quiz items
        for j in range(nprobs):
            tmp = item.copy()
            tmp["position"] = j + 1
            tmp["entry"]["title"] = f"Problem {j + 1} score"
            self.addNewQuizItem(nq.id, tmp)

        for j, q in enumerate(extraQuestions):
            q["position"] = nprobs + j + 1
            self.addNewQuizItem(nq.id, q)

        # publish quiz
        ass = self.getAssignment(nq.title)
        ass.edit(assignment={"published": True})

    def linearTimePenalty(self, hw, latePenalty=0.25, maxDaysLate=3):
        """Compute late penalty as linearly increasing in time.

        Args:
            hw (canvasapi.assignment.Assignment):
                Assignment object
            latePenalty (float):
                Maximum fraction of score to remove for lateness (defaults to 0.25).
                Must be in (0,1).
            maxDaysLate (float):
                After this number of days past deadline, HW gets zero. Defaults to 3.
                Students submitting at exactly the maximum time will recieve the maximum
                late penalty.

        Returns:
            dict:
                Dictionary of late penalties in absolute points. Keys are netids.
                The dictionary will only contain values for students with submissions.

        """

        totscore = hw.points_possible
        duedate = datetime.strptime(hw.due_at, """%Y-%m-%dT%H:%M:%S%z""")

        lates = {}
        for t in hw.get_submissions():
            if t.user_id in self.ids:
                netid = self.netids[self.ids == t.user_id][0]

                if t.submitted_at:
                    subtime = datetime.strptime(
                        t.submitted_at, """%Y-%m-%dT%H:%M:%S%z"""
                    )
                    if not t.late:
                        tdelta = 0
                    else:
                        tdelta = np.abs((duedate - subtime).total_seconds()) / 86400

                    if tdelta > maxDaysLate:
                        lates[netid] = totscore
                    else:
                        lates[netid] = tdelta / maxDaysLate * totscore * latePenalty

        return lates

    def importNewQuizSelfAssessment(
        self,
        assignmentNum,
        latePenalty=0.25,
        maxDaysLate=3,
        preamble="",
    ):
        """

        Args:
            assignmentNum (int):
                Number of assignment.
                See :py:meth:`cornellGrading.cornellGrading.getHomework` for details.
            latePenalty (float):
                Maximum fraction of score to remove for lateness (defaults to 0.25).
                Must be in (0,1).
            maxDaysLate (float):
                After this number of days past deadline, HW gets zero. Defaults to 3.
                Students submitting at exactly the maximum time will recieve the maximum
                late penalty.
            preamble (str):
                Preamble for all naming.
                See :py:meth:`cornellGrading.cornellGrading.getHomework` for details.

        Returns:
            tuple:
                submittedScoreNoAssignment (list):
                    netids of students who submitted scores but not the original
                    assignment
                submittedAssignmentNoScore (list):
                    netids of students who submitted original assignments but not
                    self-assessment scores

        """

        # get original assignments
        hwname, hw = self.getHomework(assignmentNum, preamble=preamble)

        # compute late penalties
        lates = self.linearTimePenalty(
            hw, latePenalty=latePenalty, maxDaysLate=maxDaysLate
        )

        # get the self-grading assignment and process submissions
        sg = self.getAssignment(f"{hwname} Self-Assessment")
        netids = []
        scores = []
        submittedScoreNoAssignment = []
        for sub in sg.get_submissions():
            if sub.user_id not in self.ids:
                continue
            if sub.grade is None:
                continue
            netid = self.netids[self.ids == sub.user_id][0]
            if netid not in lates:
                print(f"{netid} submitted self-grading but not the assignment!")
                submittedScoreNoAssignment.append(netid)
                continue

            netids.append(netid)
            scores.append(float(sub.grade) - lates[netid])

        # identify students with submitted assignments but no self-assessments
        submittedAssignmentNoScore = list(set(lates.keys()) - set(netids))

        self.uploadScores(hw, netids, scores)

        return submittedScoreNoAssignment, submittedAssignmentNoScore

    def genNpointNewQuizItem(self, n, item_body=None, title=None, position=0):
        """Generate a New Quiz multiple choice, variable point question with answers
        ranging from 0 to n and each answer worth the equivalent number of points.

        Args:
            n (int):
                Number of points possible.  Question will have n+1 options (from 0 to n)
                with each response worth the equivalent number of points
            item_body (str, optional):
                Question text (html formatted).  If None (default) this is set to
                <p>Enter your score based on the rubric in the syllabus</p>
            title (str, optional):
                Question title.  If None (default) this is set to:
                HW Problem Score
            position (int):
                Position of question in quiz.  Defaults to 0

        Returns:
            dict:
                New Quiz Multiple choice question definition

        """

        # set default body text and title
        if item_body is None:
            item_body = "<p>Enter your score based on the rubric in the syllabus</p>"

        if title is None:
            title = "HW Problem Score"

        # generate UUIDs
        uuids = [uuid.uuid4() for _ in range(n + 1)]

        # create choices and values dict list
        choices = []
        values = []
        for j in range(n + 1):
            choices.append(
                {"id": f"{uuids[j]}", "position": j + 1, "item_body": f"<p>{j}</p>"}
            )
            values.append({"value": f"{uuids[j]}", "points": j})

        q = {
            "position": position,
            "points_possible": float(n),
            "entry_type": "Item",
            "status": "immutable",
            "entry": {
                "title": title,
                "item_body": item_body,
                "calculator_type": "none",
                "interaction_data": {"choices": choices},
                "properties": {
                    "shuffle_rules": {"choices": {"to_lock": [], "shuffled": False}},
                    "vary_points_by_answer": True,
                },
                "scoring_data": {
                    "value": f"{uuids[-1]}",
                    "values": values,
                },
                "answer_feedback": {f"{uuids[0]}": ""},
                "scoring_algorithm": "VaryPointsByAnswer",
                "interaction_type_slug": "choice",
                "feedback": {},
            },
        }

        return q

    def genBinaryNewQuizItem(self, n, item_body, title, position=0):
        """Generate a New Quiz multiple choice, variable point question with answers
        'Yes' (earning n points) and 'No' (earning 0 points).

        Args:
            n (int):
                Number of points possible.  Question will have n+1 options (from 0 to n)
                with each response worth the equivalent number of points
            item_body (str):
                Question text (html formatted). This will automatically be wrapped in
                <p>...</p>
            title (str):
                Question title
            position (int):
                Position of question in quiz.  Defaults to 0

        Returns:
            dict:
                New Quiz Multiple choice question definition

        """

        # generate UUIDs
        uuids = [uuid.uuid4() for _ in range(2)]

        # create choices and values dict list
        choices = []
        values = []
        for j, val in enumerate(["Yes", "No"]):
            choices.append(
                {"id": f"{uuids[j]}", "position": j + 1, "item_body": f"<p>{val}</p>"}
            )
            values.append({"value": f"{uuids[j]}", "points": int(val == "Yes") * n})

        q = {
            "position": position,
            "points_possible": float(n),
            "entry_type": "Item",
            "status": "immutable",
            "entry": {
                "title": title,
                "item_body": f"<p>{item_body}</p>",
                "calculator_type": "none",
                "interaction_data": {"choices": choices},
                "properties": {
                    "shuffle_rules": {"choices": {"to_lock": [], "shuffled": False}},
                    "vary_points_by_answer": True,
                },
                "scoring_data": {
                    "value": f"{uuids[0]}",
                    "values": values,
                },
                "answer_feedback": {},
                "scoring_algorithm": "VaryPointsByAnswer",
                "interaction_type_slug": "choice",
                "feedback": {},
            },
        }

        return q

    def genNewQuizMultipleChoice(
        self, question, options, correct_ind, points=1, position=0, fightml=None
    ):
        """Generate a new quiz-style multiple choice question dictionary

        Args:
            question (str):
                The raw question text (may include LaTeX)
            options (list(str) or ~numpy.ndarray(str)):
                Possible answers. All contents must be strings (may include LaTeX)
            correct_ind (ind):
                Index of correct answer in `options` input.
            points (int):
                Number of points for correct answer (defaults to 1).
            position (int):
                Position of question in quiz.  Defaults to 0
            fightml (str, optional):
                HTML string from figure upload. Defaults to None.

        Returns:
            dict:
                Question-defining dictionary

        """

        # generate UUIDs
        uuids = [uuid.uuid4() for _ in range(len(options))]

        # create choices dict list
        choices = []
        for j in range(len(options)):
            choices.append(
                {
                    "id": f"{uuids[j]}",
                    "position": j + 1,
                    "item_body": f"<p>{convalllatex(options[j])}</p>",
                }
            )

        qtxt = f"<p>{convalllatex(question)}</p>"
        if fightml is not None:
            qtxt = f"{qtxt}\n<p>{fightml}</p>"

        q = {
            "position": position,
            "points_possible": float(points),
            "properties": {},
            "entry_type": "Item",
            "entry_editable": True,
            "stimulus_quiz_entry_id": "",
            "status": "mutable",
            "entry": {
                "title": question,
                "item_body": qtxt,
                "calculator_type": "none",
                "interaction_data": {"choices": choices},
                "properties": {
                    "shuffle_rules": {"choices": {"to_lock": [], "shuffled": False}},
                    "vary_points_by_answer": False,
                },
                "scoring_data": {"value": f"{uuids[correct_ind]}"},
                "answer_feedback": {},
                "scoring_algorithm": "Equivalence",
                "interaction_type_slug": "choice",
                "feedback": {},
            },
        }

        return q

    def genQuizMultipleChoice(
        self, question, options, correct_ind, points=1, position=0, fightml=None
    ):
        """ "Generate a classic quiz-style multiple choice question dictionary

        Args:
            question (str):
                The raw question text (may include LaTeX)
            options (list(str) or ~numpy.ndarray(str)):
                Possible answers. All contents must be strings (may include LaTeX)
            correct_ind (ind):
                Index of correct answer in `options` input.
            points (int):
                Number of points for correct answer (defaults to 1).
            position (int):
                Position of question in quiz.  Defaults to 0
            fightml (str, optional):
                HTML string from figure upload. Defaults to None.

        Returns:
            dict:
                Question-defining dictionary

        """

        # create answers dict list
        answers = []
        for j in range(len(options)):
            answers.append(
                {
                    "answer_html": f"<p>{convalllatex(options[j])}</p>",
                    "answer_weight": 100 if j == correct_ind else 0,
                }
            )

        qtxt = f"<p>{convalllatex(question)}</p>"
        if fightml is not None:
            qtxt = f"{qtxt}\n<p>{fightml}</p>"

        q = {
            "question_name": question,
            "question_text": qtxt,
            "question_type": "multiple_choice_question",
            "position": 0,
            "points_possible": points,
            "answers": answers,
        }

        return q

    def genQuizFromPollEv(self, allqs, quiz, imagePath=None, imageFolder="QuizImages"):
        """Generate quiz items from a PollEv formatted CSV input file

        Args:
            allqs (pandas.DataFrame):
                Table of questions and answers, formatted in PolEV CSV upload style
            quiz (canvasapi.new_quiz.NewQuiz or canvasapi.quiz.Quiz):
                Quiz object
            imagePath (str, optional):
                Full path to location on disk of any image files to use in questions.
            imageFolder (str):
                Name of Canvas folder to upload images to. Defaults to 'QuizImages'. If
                folder does not exist, it will be created as a hidden folder.

        Returns:
            None

        .. note::
            Poll Everywhere upload format documentation is available here:
            https://support.polleverywhere.com/hc/en-us/articles/1260801546530-Import-questions
            The format is expanded by adding a 'Figure' column.  The contents of this
            column should be the filename (without extension) of a figure associated
            with the question.  If any figures are present, input `imagePath` must be
            set. Images must be in png format with extension .png.

        """

        assert isinstance(
            quiz, (canvasapi.new_quiz.NewQuiz, canvasapi.quiz.Quiz)
        ), "quiz input must be a Quiz or New Quiz object."

        # identify response columns:
        optcols = []
        for col in allqs.columns:
            if col.startswith("Option"):
                optcols.append(col)

        # check for any figures and make sure we have enough information to upload them
        if np.any(~allqs["Figure"].isna()):
            assert (
                imagePath is not None
            ), "imagePath must be set if questions include figures."
            try:
                figFolder = self.getFolder(imageFolder)
            except AssertionError:
                figFolder = self.createFolder(imageFolder, hidden=True)

        # iterate through rows, creating the questions
        for k, row in allqs.iterrows():
            # process question and responses
            question = row.Title
            opts = row[optcols].values
            opts = opts[~pandas.isna(opts)].astype(str)
            correct_ind = [
                j
                for j, s in enumerate(opts)
                if isinstance(s, str) and s.startswith("***")
            ]
            assert len(correct_ind) == 1
            correct_ind = correct_ind[0]
            opts[correct_ind] = opts[correct_ind].strip("***")

            # process figure (if any)
            if not (pandas.isna(row.Figure)):
                impath = os.path.join(imagePath, f"{row.Figure}.png")
                fightml = self.uploadFigure(impath, figFolder)
            else:
                fightml = None

            # create and add the question depending on quiz type
            if isinstance(quiz, canvasapi.new_quiz.NewQuiz):
                q = self.genNewQuizMultipleChoice(
                    question,
                    opts.astype(str),
                    correct_ind,
                    position=k + 1,
                    fightml=fightml,
                )

                self.addNewQuizItem(quiz.id, q)
            else:
                q = self.genQuizMultipleChoice(
                    question,
                    opts.astype(str),
                    correct_ind,
                    position=k + 1,
                    fightml=fightml,
                )
                quiz.create_question(question=q)

    def uploadFigure(self, impath, figFolder):
        """Upload a figure and generate an HTML string for embedding it. If filename
        already exists in the folder, use that rather than overwriting.

        Args:
            impath (str):
                Full path of disk to figure file
            figFolder (canvasapi.folder.Folder):
                Canvas folder to upload to

        Returns:
            str:
                HTML string representing the figure
        """

        filename = os.path.split(impath)[-1]
        haveFile = False
        for file in figFolder.get_files():
            if file.filename == filename:
                haveFile = True
                fig = {
                    "id": file.id,
                    "uuid": file.uuid,
                    "display_name": file.display_name,
                }
                break

        if not haveFile:
            assert os.path.exists(impath), f"Can not locate {impath}."
            status, fig = figFolder.upload(impath)
            assert status, f"Failed to upload {impath}."

        figsrc = (
            f"{self.canvas._Canvas__requester.original_url}/courses/"
            f"{self.course.id}/files/{fig['id']}/preview?verifier={fig['uuid']}"
        )
        apisrc = (
            f"{self.canvas._Canvas__requester.base_url}courses/"
            f"{self.course.id}/files/{fig['id']}"
        )

        fightml = (
            f'<img id="{fig["id"]}" src="{figsrc}" alt="{fig["display_name"]}" '
            f'width="600" data-api-endpoint="{apisrc}" data-api-returntype="File">'
        )

        return fightml
