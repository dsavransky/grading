# grading
Routines for semi-automated grading of MATLAB coding assignments and interaction with Canvas and Qualtrics

Please note: the Canvas routines have the potential to bork your gradebook. Use at your own risk. 



Canvas API Token
===================
To generate token, in Canvas: 
* Navigate to Settings>Account>Approved Integrations
* Click '+New Access Token'.  Copy the token.  *NB: It won't be displayed again.*


Qualtrics API Token
=====================
On the qualtrics site:
* Navigate to: Account Settings>Qualtrics IDs
* Click the 'Generate Token' button under API
* This page also lists all other IDs you need to know


Qualtrics De-Anonymization
==============================
By default, Cornell anonymizes all survey responses, regardless of how you have set up your survey.  To fix this, email itservicedesk@cornell.edu and request that they toggle  "View Restricted Data" to On for your qualtrics account.


Workflow
============

```python
from grading import cornellGrading 
c = cornellGrading.cornellGrading() #this will aks for your API token the first time and store it
c.getCourse(coursenum=...,coursename=...) #the coursenum is the Canvas course #, the coursename is whatever you want, but must be kept consistent
c.setupQualtrics() #only needed if you'll be interacting with qualtrics.  will store your API token on first exec
```






