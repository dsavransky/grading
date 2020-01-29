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


[Qualtrics API Token](#qualtrics-api-token)
=============================================
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
* Navigate to Settings>Course Details and change course name to something unique (suggestion: Name: Semester).  Be sure to click 'Update Course Details' at the bottom.
* Navigate to Settings>Course Details, scroll to the very bottom, click 'more options', and check 'Hide totals in student grades summary'. Click 'Updated Course Details'
* Navigate to Settings>Navigation and ensure that 'Grades' and 'Assignments' are both in the active items (top part of page).  If you want students to be able to directly access files (rather than only via links), then add 'Files' to the active navigation items as well. Don't forget to click 'Save' at the bottom of the page.
* Go to Student View (button on right-hand side of home page), and then ensure that the 'test student' appears in People (only necessary if you want the test student to be part of the qualtrics mailing list for debugging purposes).
* Navigate to Grades.  Click the settings icon (right of the search box) and go to the 'Grade Posting Policy tab'. Ensure that 'Automatically Post Grades' is clicked (this allows for students to see comments on HWs before grades are entered, which is necessary for link injection to the self-grading surveys. Be sure to click 'Update' if any changes are made.

Now, in python:

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

Upload a Homework and Create a New Assignment
-----------------------------------------------

This procedure automates the creation of new assignments, assuming that your homework statement is in a single PDF document.  This assumes that there already exists an 'Assignments' assignment group (Canvas default), and will create a 'Homeworks' folder under Files that is not directly accessible to students (assuming it does not already exist).

The assignment will be titled 'HW?' where ? is the assignment number (i.e., 'HW1', 'HW2', etc.).


In python:

```python
from cornellGrading import cornellGrading
c = cornellGrading() 
coursenum =   #insert your course number here
c.getCourse(coursenum)

assignmentNum =   #enter assignment number (must be integer)
duedate =         #enter assignment duedate in 'YYYY-MM-DD' format. The due time will be 5pm by default.
hwfile =          #string - full path on your local disk to the HW pdf file
res = c.uploadHW(assignmentNum,duedate,hwfile) 

#by default, the created assignment will be worth 10 points.  To change this, instead run:
res = c.uploadHW(assignmentNum,duedate,hwfile,totscore=N) #N must be an integer

#by default, the created assignment will be immediate visible. To change this, instead run:
res = c.uploadHW(assignmentNum,duedate,hwfile,unlockDelta=M) 
#where M is a positive float and represents the number of days prior to the due date to unlock the assignment.
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

You can also share the created survey with another qualtrics user (say, your TA).  To do so, you will need them to give you their Qualtrics id, which they can find in the Qualtrics IDs page (see Qualtrics API Token).






