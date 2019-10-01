from grading import cornellGrading 
import numpy as np
from datetime import datetime, timedelta


c = cornellGrading.cornellGrading() 
c.getCourse()


#hwnums = np.arange(7,11)
#duedates = ['2019-10-23','2019-11-08','2019-11-15','2019-11-22']

hwnums = np.arange(8,11)
duedates = ['2019-11-08','2019-11-15','2019-11-22']



ag = c.getAssignmentGroup("Assignments") 
agdesc = """<p>Written Portion:   </p>
            <p>MATLAB Portion:    </p>"""


sg = c.getAssignmentGroup("Homework Self-Grading") 
sgdesc = """<p>Solutions: </p>
            <p>Grade yourself against the rubric in the syllabus and enter your scores for each problem using the survey link posted as a comment to your assignment submission. Please note that this is a one time link.</p>"""


for hwnum,dd in zip(hwnums,duedates):
    duedate = c.localizeTime(dd)
    assname = "HW%d"%hwnum           
    ass = c.createAssignment(assname,ag.id,description=agdesc,\
              due_at=duedate,unlock_at=duedate-timedelta(days=7,hours=5),\
              submission_types=['online_upload'],allowed_extensions=['pdf'])

    assname = "HW%d Self-Grading"%hwnum           
    ass = c.createAssignment(assname,sg.id,points_possible=0,description=sgdesc,\
            due_at=duedate+timedelta(days=7),unlock_at=duedate+timedelta(days=3))



