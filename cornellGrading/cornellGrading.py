import pandas
import numpy as np
import getpass
import keyring
import time
from datetime import datetime, timedelta
import pytz
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken
import requests
import zipfile
import tempfile
import io
import os
import re
import warnings

try:
    import urllib.parse
    import subprocess
    import shutil
    from html.parser import HTMLParser
    import pdf2image
except ImportError:
    pass


class cornellGrading:
    """ Class for io methods for Canvas and Qualtrics

        Args:
            canvasurl (str):
                Base url for canvas API calls.
                Defaults to https://canvas.cornell.edu

    """

    def __init__(self, canvasurl="https://canvas.cornell.edu", canvas_token_file=None):
        """ Ask for token, store it if you can connect, and
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
            Windows users have reported issues copying and pasting this token into the
            command prompt.  It may be safest to just retype it into the prompt.

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

    def getCourse(self, coursenum):
        """ Access course and load all student names, ids and netids

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
        """ Helper method for setting the proper UTC time while being
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

    def getAssignment(self, assignmentName):
        """ Locate assignment by name

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
        """ Locate assignment group by name

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
        """ Create assignment group by name

        Args:
            assignmentGroup (str):
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
        """ Locate folder by name

        Args:
             (str):
                Name of folder to return.  Must be exact match.
                To see all assignments do:
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
        """ Create folder by name

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
    ):
        """ Create an assignment

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

        res = self.course.create_assignment(assignment=assignment)

        return res

    def createPage(self, title, body, editing_roles="teachers", published=False):
        """ Create an assignment

        Args:
            title (str):
                Page title
            body (str):
                Content of page (html formatted string)
            editing_roles (str):
                See canvas API. Comma sepeated string, defaults to "teachers"
            published (bool):
                Whether page is published on create (defaults True)

        Returns:
            canvasapi.page.Page:
                The new page object

        Notes:
            https://canvas.instructure.com/doc/api/pages.html#method.wiki_pages_api.create

            If the title is the same as an existing page, Canvas will automatically
            append "-?" to the title, where ? is an incrementing integer.
        """

        assert isinstance(editing_roles, str), "editing_roles must be a string."

        wiki_page = {
            "title": title,
            "body": body,
            "editing_roles": editing_roles,
            "published": published,
        }

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
        insertPDF=False,
    ):
        """ Generate a new canvas page out of a LaTex source file

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
        body += " ".join(out)

        res = self.createPage(
            title, body, editing_roles=editing_roles, published=published
        )

        return res

    def matlabImport(self, assignmentNum, gradercsv, duedate):
        """ MATLAB grader grade import. Create the assignment in the MATLAB
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
        """ Upload scores to Canvas

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
        """ Wait for async result object to finish """
        while res.query().workflow_state != "completed":
            time.sleep(0.5)

        return

    def setupQualtrics(
        self, dataCenter="cornell.ca1", qualtricsapi=".qualtrics.com/API/v3/"
    ):
        """ Save/Load qualtrics api token and verify connection

        Args:
            dataCenter (str):
                Root of datacenter url.  Defaults to Cornell value.
            qualtricsapi (str):
                API url.  Defaults to v3 (current).
        Returns:
            None

        Notes:
            The dataCenter is the leading part of the qualtrics URL before
            "qualtrics.com"
            For an API token, on the qualtrics site, go to:
            Account Settings>Qualtrics IDs
            and click the 'Generate Token' button under API.
        """

        self.dataCenter = dataCenter
        self.qualtricsapi = qualtricsapi
        apiToken = keyring.get_password("qualtrics_token", "cornell.ca1")
        if apiToken is None:
            apiToken = getpass.getpass("Enter qualtrics token:\n")
            self.apiToken = apiToken
            res = self.listSurveys()
            if res.status_code == 200:
                keyring.set_password("qualtrics_token", "cornell.ca1", apiToken)
                print("Connected. Token Saved")
        else:
            self.apiToken = apiToken
            res = self.listSurveys()

        try:
            assert res.status_code == 200
            print("Connected to Qualtrics.")
        except AssertionError:
            self.apiToken = None
            print("Could not connect.")

    def listSurveys(self):
        """ Grab all available Qualtrics surveys

        Args:
            None

        Returns:
            requests.models.Response:
                The response object with the surveys.

        """

        baseUrl = "https://{0}{1}surveys".format(self.dataCenter, self.qualtricsapi)
        headers = {
            "x-api-token": self.apiToken,
        }
        response = requests.get(baseUrl, headers=headers)

        return response

    def getSurveyNames(self):
        """ Return a list of all current survey names.

        Args:
            None

        Returns:
            list:
                All survey names

        """
        res = self.listSurveys()
        surveynames = []
        for el in res.json()["result"]["elements"]:
            surveynames.append(el["name"])

        return surveynames

    def getSurveyId(self, surveyname):
        """ Find qualtrics survey id by name.  Matching is exact.

        Args:
            surveyname (str):
                Exact text of survey name

        Returns:
            str:
                Unique survey id

        """

        res = self.listSurveys()
        surveyid = None
        for el in res.json()["result"]["elements"]:
            if el["name"] == surveyname:
                surveyid = el["id"]
                break
        assert surveyid, "Couldn't find survey for this assignment."

        return surveyid

    def listMailingLists(self):
        """ Grab all available Qualtrics mailing lists

        Args:
            None

        Returns:
            requests.models.Response:
                response object with all mailing lists

        """

        baseUrl = "https://{0}{1}mailinglists".format(
            self.dataCenter, self.qualtricsapi,
        )
        headers = {
            "x-api-token": self.apiToken,
        }
        response = requests.get(baseUrl, headers=headers)

        return response

    def getMailingListId(self, listname):
        """ Find qualtrics mailinglist id by name.  Matching is exact.

        Args:
            listname (str):
                Exact text of list name

        Returns:
            str:
                Unique list id

        """

        res = self.listMailingLists()
        mailinglistid = None
        for el in res.json()["result"]["elements"]:
            if el["name"] == listname:
                mailinglistid = el["id"]
                break
        assert mailinglistid, "Couldn't find this mailing list."

        return mailinglistid

    def genCourseMailingList(self):
        """ Generates a qualtrics mailing list with all the netids from the course

        Args:
           None

        Returns:
            None

        """

        # check that this one doesn't already exist
        res = self.listMailingLists()
        assert self.coursename not in [
            el["name"] for el in res.json()["result"]["elements"]
        ], "Mailing list already exists for this course."

        names = np.array([n.split(", ") for n in self.names])
        emails = np.array([nid + "@cornell.edu" for nid in self.netids])
        firstNames = names[:, 1]
        lastNames = names[:, 0]

        mailingListId = self.genMailingList(self.coursename)

        for fN, lN, em in zip(firstNames, lastNames, emails):
            self.addListContact(mailingListId, fN, lN, em)

        # out = {'FirstName':names[:,1],'LastName':names[:,0],'PrimaryEmail':emails}
        # out = pandas.DataFrame(out)
        # out.to_csv(outfile,encoding="utf-8",index=False)

    def updateCourseMailingList(self):
        """ Compares course qualtrics mailing list to current roster and updates
        as needed

        Args:
           None

        Returns:
            None

        """

        mailingListId = self.getMailingListId(self.coursename)

        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        tmp = requests.get(
            "https://{0}{2}mailinglists/{1}/contacts".format(
                self.dataCenter, mailingListId, self.qualtricsapi,
            ),
            headers=headers,
        )

        listids = []
        listemails = []

        for el in tmp.json()["result"]["elements"]:
            listids.append(el["id"])
            listemails.append(el["email"])

        names = np.array([n.split(", ") for n in self.names])
        emails = np.array([nid + "@cornell.edu" for nid in self.netids])
        firstNames = names[:, 1]
        lastNames = names[:, 0]

        missing = list(set(emails) - set(listemails))
        if missing:
            for m in missing:
                ind = emails == m
                self.addListContact(
                    mailingListId, firstNames[ind][0], lastNames[ind][0], m
                )

        extra = list(set(listemails) - set(emails))
        if extra:
            for e in extra:
                response = requests.delete(
                    "https://{0}{3}mailinglists/{1}/contacts/{2}".format(
                        self.dataCenter,
                        mailingListId,
                        np.array(listids)[np.array(listemails) == e][0],
                        self.qualtricsapi,
                    ),
                    headers=headers,
                )
                assert (
                    response.status_code == 200
                ), "Could not remove contact from list."

    def genMailingList(self, listName):
        """ Generate mailing list

        Args:
            listname (str):
                List name

        Returns:
            str:
                Unique list id

        """

        # first we need to figure out what our personal library id is
        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        tmp = requests.get(
            "https://{0}{1}libraries".format(self.dataCenter, self.qualtricsapi),
            headers=headers,
        )

        libId = None
        for el in tmp.json()["result"]["elements"]:
            if "UR_" in el["libraryId"] or "URH_" in el["libraryId"]:
                libId = el["libraryId"]
                break
        assert libId is not None, "Could not identify library id."

        data = {"libraryId": libId, "name": listName}

        response = requests.post(
            "https://{0}{1}mailinglists".format(self.dataCenter, self.qualtricsapi),
            headers=headers,
            json=data,
        )
        assert response.status_code == 200, "Could not create mailing list."

        return response.json()["result"]["id"]

    def addListContact(self, mailingListId, firstName, lastName, email):
        """ Add a contact to a mailing list

        Args:
            mailingListId (str):
                Unique id string of mailing lists.  Get either from we interface or via
                getMailingListId
            firstName (str):
                First name
            lastName (str):
                duh
            email (str):
                double duh

        Returns:
            None

        Notes:


        """

        baseUrl = "https://{0}{2}mailinglists/{1}/contacts".format(
            self.dataCenter, mailingListId, self.qualtricsapi
        )

        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        data = {
            "firstName": firstName,
            "lastName": lastName,
            "email": email,
        }

        response = requests.post(baseUrl, json=data, headers=headers)
        assert response.status_code == 200, "Could not add contact to list."

    def genDistribution(self, surveyId, mailingListId):
        """ Create a survey distribution for the given mailing list

        Args:
            surveyId (str):
                Unique id string of survey.  Get either from web interface or via
                getSurveyId
            mailingListId (str):
                Unique id string of mailing lists.  Get either from we interface or via
                getMailingListId

        Returns:
            list:
                Dicts containing unique links ['link'] for each person in the mailing
                list ['email']

        Notes:


        """

        baseUrl = "https://{0}{1}distributions".format(
            self.dataCenter, self.qualtricsapi
        )

        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        data = {
            "surveyId": surveyId,
            "linkType": "Individual",
            "description": "distribution %s"
            % datetime.now().strftime("%Y-%m-%dT%H:%M:%S%Z"),
            "action": "CreateDistribution",
            "mailingListId": mailingListId,
        }

        response = requests.post(baseUrl, json=data, headers=headers)
        assert response.status_code == 200

        distributionId = response.json()["result"]["id"]

        baseUrl2 = "https://{0}{3}distributions/{1}/links?" "surveyId={2}".format(
            self.dataCenter, distributionId, surveyId, self.qualtricsapi
        )
        response2 = requests.get(baseUrl2, headers=headers)

        return response2.json()["result"]["elements"]

    def exportSurvey(self, surveyId, fileFormat="csv"):
        """ Download and extract survey results

        Args:
            surveyId (str):
                Unique id string of survey.  Get either from web interface or via
                getSurveyId
            fileFormat (str):
                Format to download (must be csv, tsv, or spss

        Returns:
            str:
                Full path to temp directory where unzipped file will be.  Filename
                should be the same as
                the survey name.

        Notes:
            Adapted from
            https://api.qualtrics.com/docs/getting-survey-responses-via-the-new-export-apis
            "useLabels":true is hardcoded (returns label values instead of choice
            indices. Change if you don't want that.


        """
        assert fileFormat in [
            "csv",
            "tsv",
            "spss",
        ], "fileFormat must be either csv, tsv, or spss"

        # Setting static parameters
        # requestCheckProgress = 0.0
        progressStatus = "inProgress"
        baseUrl = "https://{0}{2}surveys/{1}/export-responses/".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        headers = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

        # Step 1: Creating Data Export
        downloadRequestUrl = baseUrl
        downloadRequestPayload = '{"useLabels":true, "format":"' + fileFormat + '"}'
        downloadRequestResponse = requests.request(
            "POST", downloadRequestUrl, data=downloadRequestPayload, headers=headers
        )
        progressId = downloadRequestResponse.json()["result"]["progressId"]
        # print(downloadRequestResponse.text)
        print("Qualtrics download started.")

        # Step 2: Checking on Data Export Progress and waiting until export is ready
        while progressStatus != "complete" and progressStatus != "failed":
            # print ("progressStatus=", progressStatus)
            requestCheckUrl = baseUrl + progressId
            requestCheckResponse = requests.request(
                "GET", requestCheckUrl, headers=headers
            )
            # requestCheckProgress = \
            #    requestCheckResponse.json()["result"]["percentComplete"]
            # print("Download is " + str(requestCheckProgress) + " complete")
            progressStatus = requestCheckResponse.json()["result"]["status"]

        # step 2.1: Check for error
        if progressStatus == "failed":
            raise Exception("export failed")

        print("Download complete.")

        fileId = requestCheckResponse.json()["result"]["fileId"]

        # Step 3: Downloading file
        requestDownloadUrl = baseUrl + fileId + "/file"
        requestDownload = requests.request(
            "GET", requestDownloadUrl, headers=headers, stream=True
        )

        # Step 4: Unzipping the file
        tmpdir = os.path.join(tempfile.gettempdir(), surveyId)
        zipfile.ZipFile(io.BytesIO(requestDownload.content)).extractall(tmpdir)

        return tmpdir

    def createSurvey(self, surveyname):
        """ Create a new survey

        Args:
            surveyname (str):
                Name of survey

        Returns:
            str:
                Unique survey id

        Notes:
            Adapted from https://api.qualtrics.com/reference#create-survey
            English and ProjectCategory: CORE are hard-coded.  Qualtrics will allow you
            to create multiple surveys with the same name, but we would like to enforce
            uniqueness so this is explicitly dissallowed by the method.

        """

        res = self.getSurveyNames()

        assert surveyname not in res, "Survey with that name already exists."

        baseUrl = "https://{0}{1}survey-definitions".format(
            self.dataCenter, self.qualtricsapi
        )
        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        data = {"SurveyName": surveyname, "Language": "EN", "ProjectCategory": "CORE"}

        response = requests.post(baseUrl, json=data, headers=headers)

        try:
            assert response.status_code == 200
        except AssertionError:
            print("Survey create failed.")
            print(response.text)

        surveyId = response.json()["result"]["SurveyID"]

        return surveyId

    def genHWSurvey(self, surveyname, nprobs):
        """ Create a HW self-grade survey

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

        surveyId = self.createSurvey(surveyname)

        baseUrl = "https://{0}{2}survey-definitions/{1}/questions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

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

        response = requests.post(baseUrl, json=questionDef, headers=headers)
        assert response.status_code == 200, "Couldn't add netid question."

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
            response = requests.post(baseUrl, json=questionDef, headers=headers)
            assert response.status_code == 200, "Couldn't add problem question."

        # publish
        baseUrl2 = "https://{0}{2}survey-definitions/{1}/versions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {"Description": surveyname, "Published": True}

        response = requests.post(baseUrl2, json=data, headers=headers)
        assert response.status_code == 200, "Could not publish."

        # activate
        baseUrl3 = "https://{0}{2}surveys/{1}".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        headers3 = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

        data3 = {
            "isActive": True,
        }

        response = requests.put(baseUrl3, json=data3, headers=headers3)

        link = "https://cornell.qualtrics.com/jfe/form/%s" % surveyId

        return link

    def setupHW(self, assignmentNum, duedate, nprobs):
        """ Create qualtrics self-grading survey and Canvas column for
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
    ):
        """ Create a Canvas assignment, set the duedae, upload an associated
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
            unlockDelta (float):
                Unlock this number of days before due date. Defaults to None,
                which makes the assignment initially unlocked.
            injectText (bool):
                If True, will attempt to locate the tex file associated with the
                provided PDF in hwfile (looking in the same directory), will then
                convert to Canvas compatible html using pandoc, and add to the
                assignment description.  Requires pandoc to be installed and callable!

        Returns:
            canvasapi.assignment.Assignment

        Notes:
            All related files will be placed in path "Homeworks/HW?" where ? is the
            assignmentNum.  Folders will be created as needed and will all be hidden.

        """

        duedate = self.localizeTime(duedate)

        hwname = "HW%d" % assignmentNum

        try:
            hw = self.getAssignment(hwname)
            alreadyExists = True
        except AssertionError:
            alreadyExists = False

        assert not (alreadyExists), "%s already exists" % hwname

        # grab assignment group
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

        if unlockDelta:
            unlockAt = duedate - timedelta(days=unlockDelta)
        else:
            unlockAt = None

        if injectText:
            out = self.latex2html(hwfile, folder=hwfoldername)
            desc = desc + " ".join(out)

        hw = self.createAssignment(
            hwname,
            hwgroup.id,
            points_possible=10,
            description=desc,
            due_at=duedate,
            unlock_at=unlockAt,
            submission_types=["online_upload"],
        )

        return hw

    def latex2html(self, fname, folder="Images", hidden=True):
        """ Convert LaTex source into Canvas-compatible html
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
            "for intallation instructions."
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

        # run pandoc
        if hwd:
            _ = subprocess.run(
                [
                    "pandoc",
                    texf,
                    "-s",
                    "--webtex",
                    "-o",
                    htmlf,
                    "--default-image-extension=png",
                ],
                cwd=hwd,
                check=True,
                capture_output=True,
            )
        else:
            _ = subprocess.run(
                [
                    "pandoc",
                    texf,
                    "-s",
                    "--webtex",
                    "-o",
                    htmlf,
                    "--default-image-extension=png",
                ],
                cwd=os.path.curdir,
                check=True,
                capture_output=True,
            )
        assert os.path.exists(htmlf), "Cannot locate html output %s" % htmlf

        # read result
        with open(htmlf) as f:
            lines = f.readlines()

        upfolder = self.createFolder(folder, hidden=hidden)

        # now we need to parse the result and fix things
        class MyHTMLParser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.inBody = False
                self.inFigcaption = False
                self.inSpan = False
                self.imagesUploaded = []
                self.figcaptions = []
                self.inStyle = False
                self.spanp = re.compile(r"span.(.*?) {(.*?)}")
                self.spanDefs = {}

            def handle_starttag(self, tag, attrs):
                if tag == "body":
                    self.inBody = True

                if tag == "img":
                    imsrc = dict(attrs)["src"]
                    # anyting that's not a link must be an actual image
                    if not (imsrc.startswith("http")):
                        # if you don't see it in the source directory, it's probably a
                        # PDF and needs to be converted to PNG
                        if not (os.path.exists(os.path.join(hwd, imsrc))):
                            # look for the pdf of this image
                            imf = os.path.join(
                                hwd, imsrc.split(os.extsep)[0] + os.extsep + "pdf"
                            )
                            if not os.path.exists(imf):
                                imf = os.path.join(
                                    hwd,
                                    imsrc.split(os.extsep)[0]
                                    + "-eps-converted-to"
                                    + os.extsep
                                    + "pdf",
                                )
                            assert os.path.exists(imf), (
                                "Original image file not found for %s" % imsrc
                            )

                            pilim = pdf2image.convert_from_path(
                                imf,
                                dpi=150,
                                output_folder=None,
                                fmt="png",
                                use_cropbox=False,
                                strict=False,
                            )
                            pngf = os.path.join(tmpdir, imsrc)
                            pilim[0].save(pngf)
                            assert os.path.exists(pngf), (
                                "Cannot locate png output %s" % htmlf
                            )
                        else:
                            pngf = os.path.join(hwd, imsrc)

                        # push PNG up into the HW folder
                        res = upfolder.upload(pngf)
                        assert res[0], "Imag upload failed: %s" % pngf
                        self.imagesUploaded.append(
                            {
                                "orig": imsrc,
                                "url": res[1]["preview_url"].split("/file_preview")[0],
                            }
                        )

                if tag == "figcaption":
                    self.inFigcaption = True

                if tag == "span":
                    self.inSpan = True

                if tag == "style":
                    self.inStyle = True

            def handle_endtag(self, tag):
                if tag == "body":
                    self.inBody = False

                if tag == "figcaption":
                    self.inFigcaption = False

                if tag == "span":
                    self.inSpan = False

                if tag == "style":
                    self.inStyle = False

            def handle_data(self, data):
                if self.inFigcaption and not (self.inSpan):
                    self.figcaptions.append(data)

                if self.inStyle:
                    tmp = self.spanp.findall(data)
                    if tmp:
                        for t in tmp:
                            self.spanDefs['class="{}"'.format(t[0])] = t[1]

            # end MyHTMLParser

        imstyles = r'img style="vertical-align:middle"'
        imstyler = r'img class="equation_image"'

        srcstrs = r'src="https://latex.codecogs.com/png.latex\?'
        srcstrr = r'src="https://canvas.cornell.edu/equation_images/'

        p = re.compile(r'src="https://latex.codecogs.com/png.latex\?(.*?)"')

        def convlatex(x):
            return re.sub(x.groups()[0], urllib.parse.quote(x.groups()[0]), x.group())

        parser = MyHTMLParser()
        out = []
        for line in lines:
            _ = parser.feed(line)
            if parser.inBody:
                tmp = p.sub(convlatex, line)
                tmp = re.sub(srcstrs, srcstrr, re.sub(imstyles, imstyler, tmp))
                while parser.imagesUploaded:
                    imup = parser.imagesUploaded.pop()
                    figcap = parser.figcaptions.pop()
                    canvasimurl = (
                        r'src="https://canvas.cornell.edu{0}/preview" '
                        r'data-api-endpoint="https://canvas.cornell.edu/api/'
                        r'v1{0}" data-api-returntype="File" '.format(imup["url"])
                    )
                    tmp = re.sub(r'src="{0}"'.format(imup["orig"]), canvasimurl, tmp)
                    tmp = re.sub(r'alt=""', r'alt="{0}"'.format(figcap), tmp)

                if parser.spanDefs:
                    for cl, val in parser.spanDefs.items():
                        tmp = re.sub(cl, 'style="{}"'.format(val), tmp)

                out.append(tmp)

        out = out[1:]
        return out

    def genPrivateHWSurvey(self, surveyname, nprobs, scoreOptions=None):
        """ Create a HW self-grade survey and make private

        Args:
            surveyname (str):
                Name of survey
            nprobs (int):
                Number of problems on the HW. Set to 0 for total score only.
            scoreOptions (list of ints):
                Possible responses to each question.  Defaults to 0,1,2,3


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

        surveyId = self.createSurvey(surveyname)

        baseUrl = "https://{0}{2}survey-definitions/{1}/questions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

        if scoreOptions is None:
            scoreOptions = [0, 1, 2, 3]

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
            response = requests.post(baseUrl, json=questionDef, headers=headers)
            assert response.status_code == 200, "Couldn't add problem question."

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
                "QuestionText_Unsafe": "Question %d Score" % j,
            }
            response = requests.post(baseUrl, json=questionDef, headers=headers)
            assert response.status_code == 200, "Couldn't add problem question."

        # publish
        baseUrl2 = "https://{0}{2}survey-definitions/{1}/versions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {"Description": surveyname, "Published": True}

        response = requests.post(baseUrl2, json=data, headers=headers)
        assert response.status_code == 200, "Could not publish."

        # activate
        baseUrl3 = "https://{0}{2}surveys/{1}".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        headers3 = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

        data3 = {
            "isActive": True,
        }

        response = requests.put(baseUrl3, json=data3, headers=headers3)
        assert response.status_code == 200, "Could not activate."

        # let's set this to private.  first need to get current options as a template
        baseUrl4 = "https://{0}{2}survey-definitions/{1}/options".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        tmp = requests.get(baseUrl4, headers=headers3)
        assert response.status_code == 200, "Could not query options."

        data4 = tmp.json()["result"]
        data4["SurveyProtection"] = "ByInvitation"

        response = requests.put(baseUrl4, json=data4, headers=headers3)
        assert response.status_code == 200, "Could not update options."

        return surveyId

    def setupPrivateHW(
        self,
        assignmentNum,
        nprobs,
        sharewith=None,
        scoreOptions=None,
        createAss=False,
        solutions=None,
        injectText=False,
        selfGradeDueDelta=7,
        selfGradeReleasedDelta=3,
    ):
        """ Create qualtrics self-grading survey, individualized links distribution,
        a Canvas post for where the solutions will go, and injects links into assignment
        columns.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW# Self-Grading
            nprobs (int):
                Number of howmework problems
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
        surveyname = "%s HW%d Self-Grade" % (self.coursename, assignmentNum)
        surveyId = self.genPrivateHWSurvey(
            surveyname, nprobs, scoreOptions=scoreOptions
        )

        if sharewith:
            self.shareSurvey(surveyId, sharewith)

        mailingListId = self.getMailingListId(self.coursename)
        dist = self.genDistribution(surveyId, mailingListId)

        distnetids = np.array([d["email"].split("@")[0] for d in dist])

        # grab the original assignment and all the submissions
        hwname = "HW%d" % assignmentNum
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
                desc = desc + " ".join(out)

            _ = self.createAssignment(
                assname,
                sg.id,
                points_possible=0,
                description=desc,
                due_at=duedate + timedelta(days=selfGradeDueDelta),
                unlock_at=duedate + timedelta(days=selfGradeReleasedDelta),
            )

    def shareSurvey(self, surveyId, sharewith):
        """ Share survey with another qualtrics user
        Args:
            surveyId (str):
                Unique survey id string
            sharewith (str):
                Qualtrics id to share survey with
        Returns:
            None

        Notes:
        """

        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }

        baseUrl = "https://{0}{2}surveys/{1}/permissions/" "collaborations".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {
            "userId": sharewith,
            "permissions": {
                "surveyDefinitionManipulation": {
                    "copySurveyQuestions": True,
                    "editSurveyFlow": True,
                    "useBlocks": True,
                    "useSkipLogic": True,
                    "useConjoint": True,
                    "useTriggers": True,
                    "useQuotas": True,
                    "setSurveyOptions": True,
                    "editQuestions": True,
                    "deleteSurveyQuestions": True,
                    "useTableOfContents": True,
                    "useAdvancedQuotas": True,
                },
                "surveyManagement": {
                    "editSurveys": True,
                    "activateSurveys": True,
                    "deactivateSurveys": True,
                    "copySurveys": True,
                    "distributeSurveys": True,
                    "deleteSurveys": True,
                    "translateSurveys": True,
                },
                "response": {
                    "editSurveyResponses": True,
                    "createResponseSets": True,
                    "viewResponseId": True,
                    "useCrossTabs": True,
                    "useScreenouts": True,
                },
                "result": {
                    "downloadSurveyResults": True,
                    "viewSurveyResults": True,
                    "filterSurveyResults": True,
                    "viewPersonalData": True,
                },
            },
        }

        tmp = requests.post(baseUrl, headers=headers, json=data)
        assert tmp.status_code == 200, "Could not share survey."

    def selfGradingImport(
        self, assignmentNum, ecscore=3, checkLate=True, latePenalty=0.25, maxDaysLate=3
    ):
        """ Qualtrics self-grading survey import.

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW#
            escore (int):
                Extra credit score (defaults to 3)
            checkLate (bool):
                Check for late submissions (defaults true)
            latePenalty (float):
                Fraction of score to remove for lateness (defaults to 0.25).
                Must be in (0,1).
            maxDaysLate (float):
                After this number of days past deadline, HW gets zero. Defaults to 3.
        Returns:
            None

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
        surveyId = self.getSurveyId(surveyname)
        tmpdir = self.exportSurvey(surveyId)

        if ":" in surveyname:
            surveyname = surveyname.replace(":", "_")
        tmpfile = os.path.join(tmpdir, surveyname + ".csv")
        assert os.path.isfile(tmpfile), "Survey results not where expected."

        qualtrics = pandas.read_csv(tmpfile, header=[0, 1, 2])
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
                        # if late but within 3 days, take away 25% of the totscore
                        if (subtimes[subnetids == i][0] < -5 * 60.0) and lates[
                            subnetids == i
                        ][0]:
                            scores[j] -= totscore * latePenalty
                        # if more than 3 days, they get NOTHING
                        if (
                            subtimes[subnetids == i][0]
                            < -5 * 60.0 - maxDaysLate * 86400.0
                        ):
                            scores[j] = 0

        self.uploadScores(hw, qnetids, scores)
