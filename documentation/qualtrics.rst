Qualtrics Workflows
=====================

Quotas for Dynamic Response Updates
------------------------------------

Use case:  you wish to create a survey with a selection of one of many items and a standard set of questions related to that item (for example, ranking candidates).  To avoid user error, you would like to remove items from the selection set once a response has been registered for them.  This is relatively easy to do by setting up quotas for each item, and associating the quotas back to the display options in the item.  Below is a worked example.

#. Create sample data:

    .. code-block:: python

        items = ['Choice 1', 'Choice 2', 'Choice 3', 'Choice 4', 'Choice 5']

#. Set up qualtrics and create a survey

    .. code-block:: python

        from cornellGrading import cornellQualtrics
        c = cornellQualtrics()
        surveyId = c.createSurvey('Test Quota Survey')

#. Add dropdown menu question for choices

    .. code-block:: python

        desc = "Select Item"
        choices = {}
        for j, choice in enumerate(items):
            choices[str(j + 1)] = {"Display": choice}
        choiceOrder = list(range(1, len(choices) + 1))
        questionDef = {
            'QuestionText': desc,
            'DefaultChoices': False,
            'DataExportTag': 'Q1',
            'QuestionType': 'MC',
            'Selector': 'DL',
            'Configuration': {'QuestionDescriptionOption': 'UseText'},
            'QuestionDescription': desc,
            'Choices': choices,
            'ChoiceOrder': choiceOrder,
            'Validation': {
                'Settings': {
                    'ForceResponse': 'ON',
                    'ForceResponseType': 'ON',
                    'Type': 'None'
                }
            },
            'Language': [],
            'QuestionID': 'QID1',
            'QuestionText_Unsafe': desc}
        qid1 = c.addSurveyQuestion(surveyId, questionDef)

#. Now we add some general multiple choice questions related to each item

    .. code-block:: python

        nrubrics = 5
        scoreOptions = [0, 1, 2, 3]
        choices = {}
        for j, choice in enumerate(scoreOptions):
            choices[str(j + 1)] = {"Display": str(choice)}
        choiceOrder = list(range(1, len(choices) + 1))

        for j in range(1, nrubrics + 1):
            desc = "Rubric %d Score" % j
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
                "QuestionID": "QID%d" % (j + 3),
                "DataVisibility": {"Private": False, "Hidden": False},
                "QuestionText_Unsafe": desc,
            }
            c.addSurveyQuestion(surveyId, questionDef)

#. Now that we have the basic survey set up, we can add quotas for each item.  There are no quota groups in the survey yet, so first you need to create a group, and then all quotas will be assigned to it by default.

    .. code-block:: python

        quotaGroupName = "q1quotas"
        quotaGroupId = c.addSurveyQuotaGroup(surveyId, quotaGroupName)

        quotas = []
        for j,s in enumerate(items):
            quotaDef = {
                'Name': 'name{}quota'.format(j+1),
                'Occurrences': 1,
                'Logic': {'0': {'0': {'LogicType': 'Question',
                            'QuestionID': 'QID1',
                            'QuestionIsInLoop': 'no',
                            'ChoiceLocator': 'q://QID1/SelectableChoice/{}'.format(j+1),
                            'Operator': 'Selected',
                            'QuestionIDFromLocator': 'QID1',
                            'LeftOperand': 'q://QID1/SelectableChoice/{}'.format(j+1),
                            'Type': 'Expression',
                            'Description': ''},
                            'Type': 'If'},
                        'Type': 'BooleanExpression'},
                'LogicType': 'Simple',
                'QuotaAction': 'ForBranching',
                'ActionInfo': {'0': {'0': {'ActionType': 'ForBranching',
                                'Type': 'Expression',
                                'LogicType': 'QuotaAction'},
                                'Type': 'If'},
                            'Type': 'BooleanExpression'},
                'QuotaRealm': 'Survey',
                'Count': 0}
            quotas.append(c.addSurveyQuota(surveyId, quotaDef))

#. As a last step, we need to redo the original first question to add display logic to each of the entries, associated with each quota

    .. code-block:: python

        desc = "Select Item"
        choices = {}
        for j, choice in enumerate(items):
            choices[str(j + 1)] = {'Display': choice,
                                   'DisplayLogic': {'0': {'0': {'LogicType': 'Quota',
                                    'QuotaID': quotas[j],
                                    'QuotaType': 'Simple',
                                    'Operator': 'QuotaNotMet',
                                    'LeftOperand': 'qo://{}/QuotaNotMet'.format(quotas[j]),
                                    'QuotaName': 'name{}quota'.format(j+1),
                                    'Type': 'Expression',
                                    'Description': ''},
                                    'Type': 'If'},
                                    'Type': 'BooleanExpression',
                                    'inPage': False}}
        choiceOrder = list(range(1, len(choices) + 1))
        questionDef = {
            'QuestionText': desc,
            'DefaultChoices': False,
            'DataExportTag': 'Q1',
            'QuestionType': 'MC',
            'Selector': 'DL',
            'Configuration': {'QuestionDescriptionOption': 'UseText'},
            'QuestionDescription': desc,
            'Choices': choices,
            'ChoiceOrder': choiceOrder,
            'Validation': {
                'Settings': {
                    'ForceResponse': 'ON',
                    'ForceResponseType': 'ON',
                    'Type': 'None'
                }
            },
            'Language': [],
            'QuestionID': 'QID1',
            'QuestionText_Unsafe': desc}

        c.updateSurveyQuestion(surveyId, qid1, questionDef)

You will now have a survey where, after a submission is made for any item, the item will no longer appear in question 1 selection options upon reload of the survey.
