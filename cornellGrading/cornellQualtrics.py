import getpass
import keyring
import requests
import zipfile
import tempfile
import io
import os
from datetime import datetime


class cornellQualtrics:
    """Class for io methods for Qualtrics

    Args:
        dataCenter (str):
            Root of datacenter url.  Defaults to Cornell value.
        qualtricsapi (str):
            API url.  Defaults to v3 (current).

    """

    def __init__(
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

        self.dataCenter = dataCenter
        self.qualtricsapi = qualtricsapi

        apiToken = keyring.get_password("qualtrics_token", "cornell.ca1")
        if apiToken is None:
            if qualtrics_token_file is None:
                apiToken = getpass.getpass("Enter qualtrics token:\n")
            else:
                with open(qualtrics_token_file, "r") as f:
                    tmp = f.read()
                apiToken = tmp.strip()

            self.apiToken = apiToken
            self.setupHeaders()

            res = self.listSurveys()
            assert res.status_code == 200, "Connection error."
            keyring.set_password("qualtrics_token", "cornell.ca1", apiToken)
            print("Connected to Qualtrics. Token Saved")
        else:
            self.apiToken = apiToken
            self.setupHeaders()

            res = self.listSurveys()
            assert res.status_code == 200, "Connection error."
            print("Connected to Qualtrics.")

    def setupHeaders(self):
        """Generate standard headers

        Args:
            None

        Returns:
            None

        """

        # set up standard headers
        self.headers_tokenOnly = {
            "x-api-token": self.apiToken,
        }
        self.headers_post = {
            "x-api-token": self.apiToken,
            "content-type": "application/json",
            "Accept": "application/json",
        }
        self.headers_put = {
            "content-type": "application/json",
            "x-api-token": self.apiToken,
        }

    def listSurveys(self):
        """Grab all available Qualtrics surveys

        Args:
            None

        Returns:
            requests.models.Response:
                The response object with the surveys.

        """

        baseUrl = "https://{0}{1}surveys".format(self.dataCenter, self.qualtricsapi)
        response = requests.get(baseUrl, headers=self.headers_tokenOnly)

        return response

    def getSurveyNames(self):
        """Return a list of all current survey names.

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
        """Find qualtrics survey id by name.  Matching is exact.

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

    def getSurveyQuestions(self, surveyId):
        """Grab all available survey questions

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            requests.models.Response:
                The response object with the questions.

        """

        baseUrl = "https://{0}{1}survey-definitions/{2}/questions".format(
            self.dataCenter, self.qualtricsapi, surveyId
        )
        response = requests.get(baseUrl, headers=self.headers_tokenOnly)

        return response

    def getMailingLists(self):
        """Grab all available Qualtrics mailing lists

        Args:
            None

        Returns:
            requests.models.Response:
                response object with all mailing lists

        """

        baseUrl = "https://{0}{1}mailinglists".format(
            self.dataCenter,
            self.qualtricsapi,
        )
        response = requests.get(baseUrl, headers=self.headers_tokenOnly)

        return response

    def getMailingListId(self, listName):
        """Find qualtrics mailinglist id by name.  Matching is exact.

        Args:
            listName (str):
                Exact text of list name

        Returns:
            str:
                Unique list id

        """

        res = self.getMailingLists()
        mailinglistid = None
        for el in res.json()["result"]["elements"]:
            if el["name"] == listName:
                mailinglistid = el["id"]
                break
        assert mailinglistid, "Couldn't find this mailing list."

        return mailinglistid

    def genMailingList(self, listName):
        """Generate mailing list

        Args:
            listName (str):
                List name

        Returns:
            str:
                Unique list id

        """

        # first we need to figure out what our personal library id is
        tmp = requests.get(
            "https://{0}{1}libraries".format(self.dataCenter, self.qualtricsapi),
            headers=self.headers_tokenOnly,
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
            headers=self.headers_post,
            json=data,
        )
        assert response.status_code == 200, "Could not create mailing list."

        return response.json()["result"]["id"]

    def getListContacts(self, mailingListId):
        """Get all contacts in a mailing list

        Args:
            mailingListId (str):
                Unique id string of mailing lists.  Get either from we interface or via
                getMailingListId

        Returns:
            requests.models.Response:
                response object with all mailing list contacts

        Notes:


        """
        response = requests.get(
            "https://{0}{2}mailinglists/{1}/contacts".format(
                self.dataCenter,
                mailingListId,
                self.qualtricsapi,
            ),
            headers=self.headers_tokenOnly,
        )

        assert (
            response.status_code == 200
        ), "Could not get contacts for list {}.".format(mailingListId)

        return response

    def addListContact(self, mailingListId, firstName, lastName, email):
        """Add a contact to a mailing list

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

        data = {
            "firstName": firstName,
            "lastName": lastName,
            "email": email,
        }

        response = requests.post(baseUrl, json=data, headers=self.headers_post)
        assert response.status_code == 200, "Could not add contact to list."

    def deleteListContact(self, mailingListId, contactId):
        """Add a contact to a mailing list

        Args:
            mailingListId (str):
                Unique id string of mailing lists.  Get either from we interface or via
                getMailingListId
            contactId (str):
                Unique id string of contact to remove (as returned by getListContacts)

        Returns:
            None

        Notes:


        """

        response = requests.delete(
            "https://{0}{3}mailinglists/{1}/contacts/{2}".format(
                self.dataCenter,
                mailingListId,
                contactId,
                self.qualtricsapi,
            ),
            headers=self.headers_post,
        )
        assert response.status_code == 200, "Could not remove contact from list."

    def genDistribution(self, surveyId, mailingListId):
        """Create a survey distribution for the given mailing list

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

        data = {
            "surveyId": surveyId,
            "linkType": "Individual",
            "description": "distribution %s"
            % datetime.now().strftime("%Y-%m-%dT%H:%M:%S%Z"),
            "action": "CreateDistribution",
            "mailingListId": mailingListId,
        }

        response = requests.post(baseUrl, json=data, headers=self.headers_post)
        assert response.status_code == 200

        distributionId = response.json()["result"]["id"]

        baseUrl2 = "https://{0}{3}distributions/{1}/links?" "surveyId={2}".format(
            self.dataCenter, distributionId, surveyId, self.qualtricsapi
        )
        response2 = requests.get(baseUrl2, headers=self.headers_tokenOnly)

        return response2.json()["result"]["elements"]

    def exportSurvey(self, surveyId, fileFormat="csv", useLabels="true"):
        """Download and extract survey results

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

        # Step 1: Creating Data Export
        downloadRequestUrl = baseUrl
        downloadRequestPayload = '{{"useLabels":{0}, "format":"{1}"}}'.format(
            useLabels, fileFormat
        )
        downloadRequestResponse = requests.request(
            "POST",
            downloadRequestUrl,
            data=downloadRequestPayload,
            headers=self.headers_post,
        )
        progressId = downloadRequestResponse.json()["result"]["progressId"]
        # print(downloadRequestResponse.text)
        print("Qualtrics download started.")

        # Step 2: Checking on Data Export Progress and waiting until export is ready
        while progressStatus != "complete" and progressStatus != "failed":
            # print ("progressStatus=", progressStatus)
            requestCheckUrl = baseUrl + progressId
            requestCheckResponse = requests.request(
                "GET", requestCheckUrl, headers=self.headers_tokenOnly
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
            "GET", requestDownloadUrl, headers=self.headers_post, stream=True
        )

        # Step 4: Unzipping the file
        tmpdir = os.path.join(tempfile.gettempdir(), surveyId)
        zipfile.ZipFile(io.BytesIO(requestDownload.content)).extractall(tmpdir)

        return tmpdir

    def createSurvey(self, surveyname):
        """Create a new survey

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

        data = {"SurveyName": surveyname, "Language": "EN", "ProjectCategory": "CORE"}

        response = requests.post(baseUrl, json=data, headers=self.headers_post)

        try:
            assert response.status_code == 200
        except AssertionError:
            print("Survey create failed.")
            print(response.text)

        surveyId = response.json()["result"]["SurveyID"]

        return surveyId

    def shareSurvey(self, surveyId, sharewith):
        """Share survey with another qualtrics user
        Args:
            surveyId (str):
                Unique survey id string
            sharewith (str):
                Qualtrics id to share survey with
        Returns:
            None

        Notes:
        """

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

        tmp = requests.post(baseUrl, headers=self.headers_post, json=data)
        assert tmp.status_code == 200, "Could not share survey."

    def getSurvey(self, surveyId):
        """Get a Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            dict:
                Dictionary of survey (response.json()['result'])

        """

        baseUrl = "https://{0}{2}survey-definitions/{1}".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        response = requests.get(baseUrl, headers=self.headers_tokenOnly)
        assert response.status_code == 200, "Could not get surveyId: {}".format(
            surveyId
        )

        return response.json()["result"]

    def publishSurvey(self, surveyId):
        """Publish a Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            None

        """

        s = self.getSurvey(surveyId)

        baseUrl = "https://{0}{2}survey-definitions/{1}/versions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {"Description": s["SurveyName"], "Published": True}

        response = requests.post(baseUrl, json=data, headers=self.headers_post)
        assert response.status_code == 200, "Could not publish."

    def activateSurvey(self, surveyId):
        """Activate a Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            None

        """
        baseUrl = "https://{0}{2}surveys/{1}".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {
            "isActive": True,
        }

        response = requests.put(baseUrl, json=data, headers=self.headers_put)
        assert response.status_code == 200, "Could not activate."

    def makeSurveyPrivate(self, surveyId):
        """Make a Survey private

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            None

        """

        baseUrl = "https://{0}{2}survey-definitions/{1}/options".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )
        response = requests.get(baseUrl, headers=self.headers_tokenOnly)
        assert response.status_code == 200, "Could not query options."

        data = response.json()["result"]
        data["SurveyProtection"] = "ByInvitation"

        response = requests.put(baseUrl, json=data, headers=self.headers_post)
        assert response.status_code == 200, "Could not update options."

    def addSurveyQuestion(self, surveyId, questionDef):
        """Add question to existing Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId
            questionDef (dict):
                Full question definition dictionary

        Returns:
            str:
                Question ID

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/questions".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        response = requests.post(baseUrl, json=questionDef, headers=self.headers_post)
        assert response.status_code == 200, "Couldn't add question."

        return response.json()["result"]["QuestionID"]

    def updateSurveyQuestion(self, surveyId, qId, questionDef):
        """Add question to existing Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId
            qId (str):
                Question ID string as returned by addSurveyQuestion
            questionDef (dict):
                Full question definition dictionary

        Returns:
            None

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/questions/{3}".format(
            self.dataCenter, surveyId, self.qualtricsapi, qId
        )

        response = requests.put(baseUrl, json=questionDef, headers=self.headers_post)
        assert response.status_code == 200, "Couldn't update question."

    def getSurveyQuotas(self, surveyId):
        """Get all quotas for a survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            dict:
                Dictionary of quotas (response.json()['result'])

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/quotas".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        response = requests.get(baseUrl, headers=self.headers_tokenOnly)
        assert (
            response.status_code == 200
        ), "Could not get quotas for surveyId: {}".format(surveyId)

        return response.json()["result"]

    def getSurveyQuotaGroups(self, surveyId):
        """Get a Survey's quota groups

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId

        Returns:
            list:
                 Quota ids (response.json()['result']["elements"][0]["Quotas"])

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/quotagroups".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        response = requests.get(baseUrl, headers=self.headers_tokenOnly)
        assert (
            response.status_code == 200
        ), "Could not get quotas for surveyId: {}".format(surveyId)

        return response.json()["result"]["elements"][0]["Quotas"]

    def addSurveyQuotaGroup(self, surveyId, quotaGroupName):
        """Add quota to existing Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId
            quotaDef (dict):
                Full question definition dictionary

        Returns:
            str:
                Quota Group ID

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/quotagroups".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        data = {"Name": quotaGroupName, "Public": False, "MultipleMatch": "PlaceInAll"}

        response = requests.post(baseUrl, json=data, headers=self.headers_post)
        assert response.status_code == 200, "Couldn't add quota group."

        return response.json()["result"]["QuotaGroupID"]

    def addSurveyQuota(self, surveyId, quotaDef):
        """Add quota to existing Survey

        Args:
            surveyId (str):
                Survey ID string as returned by getSurveyId
            quotaDef (dict):
                Full question definition dictionary

        Returns:
            str:
                Quota ID

        """
        baseUrl = "https://{0}{2}survey-definitions/{1}/quotas".format(
            self.dataCenter, surveyId, self.qualtricsapi
        )

        response = requests.post(baseUrl, json=quotaDef, headers=self.headers_post)
        assert response.status_code == 200, "Couldn't add quota."

        return response.json()["result"]["QuotaID"]
