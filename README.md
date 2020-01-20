# grading
Routines for semi-automated grading of MATLAB coding assignments and interaction with Canvas and Qualtrics

Please note: the Canvas routines have the potential to bork your gradebook. Use at your own risk. 


cornellGrading Installation
==============================
In the cloned grading directory:

```
pip install --user .
```

or, to install in developer mode:

```
pip install --user -e .
```


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

Initial Course Setup
------------------------

In Canvas:
* Navigate to Settings, change course name to something unique (suggestion: Name: Semester)
* Go to Student View, and then ensure that the 'test student' appears in People (only necessary if you want the test student to be part of the qualtrics mailing list for debugging purposes).

```python
from cornellGrading import cornellGrading

#connect to canvas
c = cornellGrading() 


#get your coursenumber (the part in parentheses):
for cn in c.canvas.get_courses(): print(cn) 

coursenum = ... #change to your actual number from list printed above

c.getCourse(coursenum)

#sanity check
print(c.coursename) #should be the course name you set in Canvas
print(c.names) #should be all your students

#connect to qualtrics
c.setupQualtrics() 

#generate course mailing list
c.genCourseMailingList()
```

Create a HW Survey
--------------------

This assumes that you have set up your assignment with the name 'HW?' where ? is the assignment number (i.e., 'HW1', 'HW2', etc.).

```python
from cornellGrading import cornellGrading
c = cornellGrading() 
coursenum =   #insert your course number here
c.getCourse(coursenum)
c.setupQualtrics() 
assignmentNum = 1 #change to actual assignment number
nprobs = 3 #number of problems in assignment
c.setupPrivateHW(assignmentNum,nprobs)

#or, let's say you're a weirdo who only wants a single grade for the whole assignment, 
#and wants the students to grade themselves out of 10,9,7,5,3, exclusively.  
#Then the last line becomes:
c.setupPrivateHW(assignmentNum,0,scoreOptions=[10,9,7,5,3])
```

After executing (assuming no errors), you should see a new survey in Qualtrics with the name "Coursename HW? Self-Grade", and a personalized link should be injected into the comments for each student in the original assignment. 

If your course roster has changed, be sure to run `c.updateCourseMailingList()` prior to `setupPrivateHW`.





