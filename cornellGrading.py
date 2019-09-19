import pandas
import numpy as np
import getpass,keyring
import time
from datetime import datetime, timedelta
import pytz
from canvasapi import Canvas 
from canvasapi.exceptions import InvalidAccessToken 
import requests
import zipfile
import json
import io, os, sys, re
import tempfile

class cornellGrading():
    """ Class for io methods for Canvas and Qualtrics 
    
        Args:
            canvasurl (str):
                Base url for canvas API calls.  
                Defaults to https://canvas.cornell.edu
    
    """

    def __init__(self,canvasurl="https://canvas.cornell.edu"):
        """ Ask for token, store it if you can connect, and 
        save resulting canvas object 
        
        To generate token: in Canvas: Settings>Account>Approved Integrations
        Click '+New Access Token'.  Copy the token.  It won't be displayed again.
        """

        token = keyring.get_password('canvas_test_token1', 'canvas')
        if token is None:
            token = getpass.getpass("Enter canvas token:\n")
            try:
                canvas = Canvas(canvasurl,token)
                canvas.get_current_user()
                keyring.set_password('canvas_test_token1', 'canvas', token)
                print("Connected.  Token Saved")
            except InvalidAccessToken:
                print("Could not connect. Token not saved.")
        else:
            canvas = Canvas(canvasurl,token)
            canvas.get_current_user()
            print("Connected to Canvas.")

        self.canvas = canvas


    def getCourse(self, coursenum = 5773, coursename="MAE4060 Fall2019"):
        """ Access course and load all student names, ids and netids
    
        Args:
            coursenum (int):
                Canvas course number to access. This can be looked
                up in Canvas, or you can look up all your courses:
                >> c = cornellGrading.cornellGrading() 
                >> for cn in c.canvas.get_courses(): print(cn)
            coursename (str):
                Short course name for use in creating surveys, etc.
                
    
        """

        #get the course
        course = self.canvas.get_course(coursenum)
        tmp = course.get_users() 
        names = []
        ids = []
        netids = []
        for t in tmp:
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

        self.coursename = coursename

    def localizeTime(self,duedate,duetime="17:00:00", tz="US/Eastern"):
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
            datetime.datetime
                tzinfo will be <UTC>!
                    
        """
        local = pytz.timezone(tz)
        naive = datetime.strptime(duedate+" "+duetime, "%Y-%m-%d %H:%M:%S")
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)              

        return utc_dt
    
    def getAssignment(self,assignmentName):
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

        assert hw is not None,"Could not find assignment."

        return hw


    def getAssignmentGroup(self,groupName):
        """ Locate assignment group by name
    
        Args:
            assignmentGroup (str):
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

        assert group is not None,"Could not find assignment group."

        return group


    def createAssignment(self,name,groupid,submission_types=["none"],\
                         points_possible=10,published=True,description=None,\
                         due_at = None, unlock_at = None):
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
                duh
            published (bool):
                duh (defaults True)
            description (str):
                The html assignment text.  Not added if None (default).
            due_at (datetime.datetime):
                Due date (not included if None). Must be timezone aware and UTC!
            unlock_at (datetime.datetime):
                Unlock date (not included if None). Must be timezone aware and UTC!


        Returns:
            canvasapi.assignment.Assignment

        Notes:
            https://canvas.instructure.com/doc/api/assignments.html#method.assignments_api.create
        """


        assert isinstance(submission_types,list),"submission_types must be a list."

        #create payload
        assignment = {'name':name,
                      'submission_types':submission_types,
                      'points_possible':points_possible,
                      'assignment_group_id':groupid,
                      'published':published}

        if description:
            assignment['description'] = description

        if due_at:
            assignment['due_at'] = due_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        if unlock_at:
            assignment['unlock_at'] = unlock_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        res = self.course.create_assignment(assignment=assignment)

        return res

    def matlabImport(self,assignmentNum,gradercsv,duedate):
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

            NB: We are assuming that the timezone on your machine matches the timezone of
            the grader submitted time column.  If there is a mismatch, there will be errors.
        """

        
        duedate = self.localizeTime(duedate)

        name = "MATLAB "+str(assignmentNum)
        try:
            ass = self.getAssignment(name)
        except AssertionError:
            mg = self.getAssignmentGroup("MATLAB Assignments")
            ass = self.createAssignment(name,mg.id)

        #process grader output
        grader = pandas.read_csv(gradercsv)
        
        #on windows, EDT/EST aren't in time.tzname, so we're going to
        #parse the grader timestring manually and then force localization
        timep = re.compile('(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) \S*')
        timetmp = []
        for t in grader['Submitted Time']:
            tmp = timep.match(t)
            timetmp.append(self.localizeTime(tmp.groups()[0],duetime=tmp.groups()[1]))


        emails = grader['Student Email'].values
        testspassed = grader['Tests Passed'].values.astype(float)
        tottests = grader['Total Tests'].values.astype(float)
        probs = grader['Problem Title'].values
        subtimes = np.array([(duedate - t).total_seconds() for t in timetmp])
        islate = grader['Late Submission?'].values == 'Y'

        uprobs = np.unique(probs)
        uemails = np.unique(emails)
        
        netids = np.array([e.split('@')[0] for e in uemails])
        scores = np.zeros(netids.size)
        for prob in uprobs:
            tottest = np.max(tottests[probs == prob])
            pscores = testspassed[probs == prob]/tottest
            pscores[(subtimes[probs == prob] < -5*60.) & (islate[probs == prob])] -= 0.25
            pscores[(subtimes[probs == prob] < -5*60. - 3*86400.) & (islate[probs == prob])] = 0
            pscores[pscores < 0 ] = 0
            pemails = emails[probs == prob]
            for e,s in zip(pemails,pscores):
                scores[uemails == e] +=  s
        
        scores *= 10./len(uprobs)

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
            Only netids matching those found in the currently loaded course will be uplaoded.
        """
        

        #let's build up the submission dictionary
        #want API structure of grade_data[<student_id>][posted_grade]
        #this becomes grade_data = {'id (number)':{'posted_grade':'grade (number)', ...}
        unmatchedids = []
        grade_data = { }
        for i,s in zip(netids,scores):
            if (i == i): 
                if (i in self.netids):
                    grade_data['%d'%self.ids[self.netids == i]] = {'posted_grade':'%f'%s}
                else:
                    unmatchedids.append(i)

        if unmatchedids:
            print("Could not match netids: %s"%", ".join(unmatchedids))

        #send payload
        print("Uploading Grades.")
        res = ass.submissions_bulk_update(grade_data=grade_data)
        self.waitForSubmit(res)
        print("Done.")


    def waitForSubmit(self,res):
        """ Wait for async result object to finish """
        while res.query().workflow_state != 'completed':
            time.sleep(0.5)

        return



    def setupQualtrics(self, dataCenter="cornell.ca1"):
        """ Save/Load qualtrics api token and verify connection

        Args:
            dataCenter (str):
                Root of datacenter url.  Defaults to Cornell value.
        Returns:
            None

        Notes:
            The dataCenter is the leading part of the qualtrics URL before "qualtrics.com"
            For an API token, on the qualtrics site, go to: Account Settings>Qualtrics IDs
            and click the 'Generate Token' button under API.
        """

        self.dataCenter = dataCenter
        apiToken = keyring.get_password('qualtrics_token', 'cornell.ca1')
        if apiToken is None:
            apiToken = getpass.getpass("Enter qualtrics token:\n")
            self.apiToken = apiToken
            res = self.listSurveys()
            if (res.status_code == 200):
                keyring.set_password('qualtrics_token', 'cornell.ca1', apiToken)
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
            requests.models.Response
                
        """

        baseUrl = "https://{0}.qualtrics.com/API/v3/surveys".format(self.dataCenter)
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
        for el in res.json()['result']['elements']:
            surveynames.append(el['name'])

        return surveynames


    def getSurveyId(self,surveyname):
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
        for el in res.json()['result']['elements']:
            if el['name'] == surveyname:
                surveyid = el['id']
                break
        assert surveyid, "Couldn't find survey for this assignment."

        return surveyid


    def exportSurvey(self,surveyId, fileFormat="csv"):
        """ Download and extract survey results

        Args:
            surveyId (str):
                Unique id string of survey.  Get either from web interface or via getSurveyId
            fileFormat (str):
                Format to download (must be csv, tsv, or spss

        Returns:
            str:
                Full path to temp directory where unzipped file will be.  Filename should be the same as
                the survey name.

        Notes:
            Adapted from https://api.qualtrics.com/docs/getting-survey-responses-via-the-new-export-apis
            "useLabels":true is hardcoded (returns label values instead of choice indices.  
            Change if you don't want that. 

                
        """
        assert fileFormat in ["csv", "tsv", "spss"], "fileFormat must be either csv, tsv, or spss"

        # Setting static parameters
        requestCheckProgress = 0.0
        progressStatus = "inProgress"
        baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/export-responses/".format(self.dataCenter, surveyId)
        headers = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

        # Step 1: Creating Data Export
        downloadRequestUrl = baseUrl
        downloadRequestPayload = '{"useLabels":true, "format":"' + fileFormat + '"}'
        downloadRequestResponse = requests.request("POST", downloadRequestUrl, data=downloadRequestPayload, headers=headers)
        progressId = downloadRequestResponse.json()["result"]["progressId"]
        #print(downloadRequestResponse.text)
        print("Qualtrics download started.")

        # Step 2: Checking on Data Export Progress and waiting until export is ready
        while progressStatus != "complete" and progressStatus != "failed":
            #print ("progressStatus=", progressStatus)
            requestCheckUrl = baseUrl + progressId
            requestCheckResponse = requests.request("GET", requestCheckUrl, headers=headers)
            requestCheckProgress = requestCheckResponse.json()["result"]["percentComplete"]
            #print("Download is " + str(requestCheckProgress) + " complete")
            progressStatus = requestCheckResponse.json()["result"]["status"]

        #step 2.1: Check for error
        if progressStatus is "failed":
            raise Exception("export failed")

        print("Download complete.")

        fileId = requestCheckResponse.json()["result"]["fileId"]

        # Step 3: Downloading file
        requestDownloadUrl = baseUrl + fileId + '/file'
        requestDownload = requests.request("GET", requestDownloadUrl, headers=headers, stream=True)

        # Step 4: Unzipping the file
        tmpdir = os.path.join(tempfile.gettempdir(),surveyId)
        zipfile.ZipFile(io.BytesIO(requestDownload.content)).extractall(tmpdir)
        
        return tmpdir

                        
    def createSurvey(self,surveyname):
        """ Create a new survey

        Args:
            surveyname (str):
                Name of survey

        Returns:
            str:
                Unique survey id

        Notes:
            Adapted from https://api.qualtrics.com/reference#create-survey
            English and ProjectCategory: CORE are hard-coded.  Qualtrics will allow you to 
            create multiple surveys with the same name, but we would like to enforce uniqueness
            so this is explicitly dissallowed by the method.
                
        """

        res = self.getSurveyNames()

        assert surveyname not in res, "Survey with that name already exists."

        baseUrl = "https://{0}.qualtrics.com/API/v3/survey-definitions".format(self.dataCenter)
        headers = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json"
        }

        data = {"SurveyName": surveyname, "Language": "EN","ProjectCategory": "CORE"}

        response = requests.post(baseUrl, json=data, headers=headers)

        try:
            assert response.status_code == 200
        except AssertionError:
            print("Survey create failed.")
            print(response.text)

        surveyId = response.json()['result']['SurveyID']

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
        """


        surveyId = self.createSurvey(surveyname)

        baseUrl = "https://{0}.qualtrics.com/API/v3/survey-definitions/{1}/questions".format(self.dataCenter, surveyId)
        headers = {
           'accept': "application/json",
           'content-type': "application/json",
           "x-api-token": self.apiToken,
        }


        #add netid question first
        questionDef = {
         'QuestionText': 'Enter your netid',
         'DefaultChoices': False,
         'DataExportTag': 'Q1',
         'QuestionID': 'QID1',
         'QuestionType': 'TE',
         'Selector': 'SL',
         'DataVisibility': {'Private': False, 'Hidden': False},
         'Configuration': {'QuestionDescriptionOption': 'UseText'},
         'QuestionDescription': 'Enter your netid',
         'Validation': {'Settings': {'ForceResponse': 'ON',
           'ForceResponseType': 'ON',
           'Type': 'None'}},
         'GradingData': [],
         'Language': [],
         'NextChoiceId': 1,
         'NextAnswerId': 1,
         'SearchSource': {'AllowFreeResponse': 'false'},
         'QuestionText_Unsafe': 'Enter your netid'}

        response = requests.post(baseUrl, json=questionDef, headers=headers)
        assert response.status_code == 200, "Couldn't add netid question."

        #add rubric questions for all problems
        for j in range(1,nprobs+1):
            questionDef = {
                 'QuestionText': 'Question %d Score'%j,
                 'DataExportTag': 'Q%d'%(j+1),
                 'QuestionType': 'MC',
                 'Selector': 'SAVR',
                 'SubSelector': 'TX',
                 'Configuration': {'QuestionDescriptionOption': 'UseText'},
                 'QuestionDescription': 'Question %d Score'%j,
                 'Choices': {'1': {'Display': '0'},
                  '2': {'Display': '1'},
                  '3': {'Display': '2'},
                  '4': {'Display': '3'}},
                 'ChoiceOrder': [1, 2, 3, 4],
                 'Validation': {'Settings': {'ForceResponse': 'ON',
                   'ForceResponseType': 'ON',
                   'Type': 'None'}},
                 'Language': [],
                 'QuestionID': 'QID%d'%(j+1),
                 'DataVisibility': {'Private': False, 'Hidden': False},
                 'NextChoiceId': 5,
                 'NextAnswerId': 1,
                 'QuestionText_Unsafe': 'Question %d Score'%j}
            response = requests.post(baseUrl, json=questionDef, headers=headers)
            assert response.status_code == 200, "Couldn't add problem question."

        #publish
        baseUrl2 = "https://{0}.qualtrics.com/API/v3/survey-definitions/{1}/versions".format(self.dataCenter, surveyId)

        data = {
            "Description": surveyname,
            "Published": True
        }

        response = requests.post(baseUrl2, json=data, headers=headers)
        assert response.status_code == 200, "Could not publish."

        #activate
        baseUrl3 = "https://{0}.qualtrics.com/API/v3/surveys/{1}".format(self.dataCenter, surveyId)
        headers3 = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
            }

        data3 = { 
            "isActive": True, 
           }

        response = requests.put(baseUrl3, json=data3, headers=headers3)


        link = "https://cornell.qualtrics.com/jfe/form/%s"%surveyId

        return link



    def setupHW(self,assignmentNum,duedate,nprobs):
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

        Notes:
            Note that this does not embed the solutions - still need to do that manually.

        """

        duedate = self.localizeTime(duedate) 

        surveyname = "%s HW%d Self-Grade"%(self.coursename,assignmentNum)
        assname = "HW%d Self-Grading"%assignmentNum

        link = self.genHWSurvey(surveyname, nprobs)

        sg = self.getAssignmentGroup("Homework Self-Grading")
        
        desc = """<p>Solutions: </p>
                  <p>Grade yourself against the rubric in the syllabus and enter your scores for each problem here:</p>
                  <p><a class="survey-link ng-binding" href="{0}" target="_blank">{0}</a></p>
                  <p>Be sure to enter your correct netid or you will not receive credit.</p>""".format(link)

        ass = self.createAssignment(assname,sg.id,points_possible=0,description=desc,\
                due_at=duedate+timedelta(days=7),unlock_at=duedate+timedelta(days=3))



    def selfGradingImport(self,assignmentNum,duedate,totscore=10):
        """ Qualtrics self-grading survey import. 

        Args:
            assignmentNum (int):
                Number of assignment. Name of survey will be 
                "self.coursename HW# Self-Grade"
                Name of assignment will be HW#
            duedate (str):
                Due date in format: YYYY-MM-DD (5pm assumed local time)
            totscore (int):
                Total score for assignment (defaults to 10)
        Returns:
            None

        Notes:
            To whitelist late submissions, in Canvas gradebook, click on the submission, 
            click the right arrow, and then set status to 'None'.

        """

        duedate = self.localizeTime(duedate)

        surveyname = "%s HW%d Self-Grade"%(self.coursename,assignmentNum)
        surveyId = self.getSurveyId(surveyname)
        tmpdir = self.exportSurvey(surveyId)

        tmpfile = os.path.join(tmpdir,surveyname+".csv")
        assert  os.path.isfile(tmpfile), "Survey results not where expected."

        qualtrics = pandas.read_csv(tmpfile,header=[0,1,2])
        #find netid and question cols in Qualtrics
        qnetidcol = qualtrics.columns.get_level_values(0)[np.array(["Enter your netid" in c for c in qualtrics.columns.get_level_values(1)])]
        assert not(qnetidcol.empty), "Could not identify netid qualtrics column"
        qnetids = qualtrics[qnetidcol].values.flatten()

        #calculate total scores
        quescols = qualtrics.columns.get_level_values(0)[np.array(["Question" in c and "Score" in c for c in qualtrics.columns.get_level_values(1)])]
        scores = qualtrics[quescols].values.sum(axis=1)/3./len(quescols)*totscore

        #ok, now we need to grab the canvas column
        hwname = "HW%d"%assignmentNum
        hw = self.getAssignment(hwname)

        tmp = hw.get_submissions() 
        subnetids = []
        subtimes = []
        lates = []
        for t in tmp:
            if t.user_id in self.ids:
                subnetids.append(self.netids[self.ids == t.user_id][0])
                if t.submitted_at:
                    subtime = datetime.strptime(t.submitted_at, """%Y-%m-%dT%H:%M:%S%z""")
                    tdelta = duedate - subtime
                    subtimes.append(tdelta.total_seconds())
                else:
                    subtimes.append(np.nan)
                lates.append(t.late)

        subnetids = np.array(subnetids)
        subtimes = np.array(subtimes)
        lates = np.array(lates)

        #let's build up the submission dictionary
        #want API structure of grade_data[<student_id>][posted_grade]
        #this becomes grade_data = {'id (number)':{'posted_grade':'grade (number)', ...}
        for j,i in enumerate(qnetids):
            if (i == i) and (i in self.netids):
                if np.isnan(subtimes[subnetids == i][0]):
                    scores[j] = 0
                else:
                    #if late but within 3 days, take away 25% of the totscore
                    if (subtimes[subnetids == i][0] < -5*60.) and lates[subnetids == i][0]:
                        scores[j] -= totscore*0.25
                    #if more than 3 days, they get NOTHING
                    if (subtimes[subnetids == i][0] < -5*60. - 3*86400.):
                        scores[j] = 0

        self.uploadScores(hw, qnetids, scores)

