from datetime import datetime, timedelta
import numpy as np
import re
import os.path

basepath = '/Users/ds264/Documents/Courses/MAE4060/2020Fall/'
curryear = '2020'
semester_dates = os.path.join(basepath,'semester_dates.txt')
with open(semester_dates) as f:
    datesraw = f.readlines()

dateparse = re.compile('\\\\newcommand{(.*?)}{(.*?)}')
dates = {}
for l in datesraw:
    m = dateparse.match(l)
    tmp = m.groups()[1].strip('~')
    if '-' in tmp:
        tmp = tmp.split('-')
        tmp = [datetime.strptime(t.strip()+'/'+curryear,"%m/%d/%Y") for t in tmp]
    else:
        tmp = datetime.strptime(tmp.strip()+'/'+curryear,"%m/%d/%Y")
    dates[m.groups()[0].strip('\\')] = tmp


now = dates['firstday']
cal = []
classdays = [1,3]
#first day ->labor day
while (dates['laborday']-now).days > 0:
    #add tuesdays and thrusdays
    if now.weekday() in classdays:
        cal.append(now.strftime('%-m/%-d'))
    now += timedelta(days=1)
#labor day-> fall break
now = dates['laborday'] + timedelta(days=1)
while (dates['fallbreak'][0]-now).days > 0:
    #add tuesdays and thrusdays
    if now.weekday() in classdays:
        cal.append(now.strftime('%-m/%-d'))
    now += timedelta(days=1)
#fall break -> thanksgiving
now = dates['fallbreak'][1] + timedelta(days=1)
while (dates['thanksgiving'][0]-now).days > 0:
    #add tuesdays and thrusdays
    if now.weekday() in classdays:
        cal.append(now.strftime('%-m/%-d'))
    now += timedelta(days=1)
#thanksgiving -> end
now = dates['thanksgiving'][1] + timedelta(days=1)
while (dates['lastday']-now).days >= 0:
    #add tuesdays and thrusdays
    if now.weekday() in classdays:
        cal.append(now.strftime('%-m/%-d'))
    now += timedelta(days=1)

lecture_dates = os.path.join(basepath,'lecture_dates.txt')
with open(lecture_dates,'w') as f:
    for c in cal:
        f.write("%s\n"%c)

###


class mylecs():
    def __init__(self,basepath):
        self.leccounter = 1
        self.hwcounter = 1
        self.basepath = basepath
        lecs = os.path.join(basepath,'lecture_topics_and_readings.txt')
        with open(lecs) as f:
            lecs = f.readlines()
        self.lecs = lecs

        self.p = re.compile('\\\\textbf{(.*?)}')
        self.convbf = lambda x: "<b>{0}</b>".format(x.groups()[0])

        hwdates = os.path.join(basepath,'hw_dates.txt')
        with open(hwdates) as f:
            hwdates = f.readlines()
        self.hwdates = hwdates

        lecdates = os.path.join(basepath,'lecture_dates.txt')
        with open(lecdates) as f:
            lecdates = f.readlines()
        self.lecdates = lecdates


    def nextlec(self):
        tmp = self.lecs.pop(0)
        tmp = tmp.split('&')
        out = r'<td style="width: 5%;">{0}</td><td style="width: 45%;">{1}. {2}</td><td style="width: 25%;">{3}</td>'.format(self.lecdates.pop(0).strip(),self.leccounter,re.sub('~',' ',tmp[0].strip()),re.sub('~',' ',tmp[1].strip()))
        self.leccounter += 1
        return out

    def nexthw(self,nrows):
        out = r'<td style="width: 15%;" rowspan={2}>HW {0}<br/>Due {1}</td>'.format(self.hwcounter,\
                self.p.sub(self.convbf,self.hwdates.pop(0).strip()),nrows)
        self.hwcounter += 1
        return out


ll = mylecs(basepath)

out = '''<table style="border-collapse: collapse; width: 100%;" border="1">
<tbody>
<tr><td style="width: 5%;">Date</td><td style="width: 45%;">Topic</td><td style="width: 25%;">Reading</td><td style="width: 15%;">Homework</td></tr>
'''
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #1
out += "<tr>"+ll.nextlec()+"</tr>\n"              #2
out += "<tr>"+ll.nextlec()+ll.nexthw(3)+"</tr>\n" #3
out += '<tr><td style="background-color: #eeeeee;" colspan=3>Labor Day {0}</td</tr>\n'.format(dates['laborday'].strftime('%-m/%-d'))
out += "<tr>"+ll.nextlec()+"</tr>\n"              #4
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #5
out += "<tr>"+ll.nextlec()+"</tr>\n"              #6
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #7
out += "<tr>"+ll.nextlec()+"</tr>\n"              #8
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #9
out += "<tr>"+ll.nextlec()+"</tr>\n"              #10
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #11
out += "<tr>"+ll.nextlec()+"</tr>\n"              #12
out += "<tr>"+ll.nextlec()+ll.nexthw(3)+"</tr>\n" #13
out += '<tr><td style="background-color: #eeeeee;" colspan=3>Fall Break {0} - {1}</td</tr>\n'.format(dates['fallbreak'][0].strftime('%-m/%-d'),dates['fallbreak'][1].strftime('%-m/%-d'))
out += "<tr>"+ll.nextlec()+"</tr>\n"              #14
out += "<tr>"+ll.nextlec()+"<td></td></tr>\n"     #15
out += "<tr>"+ll.nextlec()+ll.nexthw(4)+"</tr>\n" #16
out += "<tr>"+ll.nextlec()+"</tr>\n"              #17
out += '<tr><td style="background-color: #eeeeee;" colspan=3>Prelim {0}</td</tr>\n'.format(dates['prelim'].strftime('%-m/%-d'))
out += "<tr>"+ll.nextlec()+"</tr>\n"              #18
out += "<tr>"+ll.nextlec()+ll.nexthw(3)+"</tr>\n" #19
out += "<tr>"+ll.nextlec()+"</tr>\n"              #20
out += "<tr>"+ll.nextlec()+"</tr>\n"              #21
out += "<tr>"+ll.nextlec()+ll.nexthw(2)+"</tr>\n" #22
out += "<tr>"+ll.nextlec()+"</tr>\n"              #23
out += "<tr>"+ll.nextlec()+ll.nexthw(5)+"</tr>\n" #24
out += "<tr>"+ll.nextlec()+"</tr>\n"              #25
out += '<tr><td style="background-color: #eeeeee;" colspan=3>Thanksgiving Break {0} - {1}</td</tr>\n'.format(dates['thanksgiving'][0].strftime('%-m/%-d'),dates['thanksgiving'][1].strftime('%-m/%-d'))
out += "<tr>"+ll.nextlec()+"</tr>\n"              #26
out += "<tr>"+ll.nextlec()+"</tr>\n"              #27
out += "<tr>"+ll.nextlec()+"<td></td></tr>\n"     #28
out += '<tr><td style="background-color: #eeeeee;" colspan=4>Final Exam</td</tr>\n'

out+='''
</tbody>
</table>'''

with open('/Users/ds264/Downloads/feh.html','w') as f: f.write(out)


#####
class mylecs2():
    def __init__(self,basepath):
        self.weekcounter = 0
        self.leccounter = 1
        self.hwcounter = 1
        self.basepath = basepath
        lecs = os.path.join(basepath,'weekly_lectures_readings.txt')
        with open(lecs) as f:
            lecs = f.readlines()
        self.lecs = lecs

        self.p = re.compile('\\\\textbf{(.*?)}')
        self.convbf = lambda x: "<b>{0}</b>".format(x.groups()[0])

        hwdates = os.path.join(basepath,'hw_dates.txt')
        with open(hwdates) as f:
            hwdates = f.readlines()
        self.hwdates = hwdates

        lecdates = os.path.join(basepath,'lecture_dates.txt')
        with open(lecdates) as f:
            lecdates = f.readlines()
        self.lecdates = lecdates

    def nextweek(self):
        self.weekcounter += 1
        return r'<td style="width: 5%;">{0}</td>'.format(self.weekcounter)

    def nextdates(self,n=1):
        out = r'<td style="width: 5%;">'

        for j in range(n):
            out += r"{} ".format(self.lecdates.pop(0).strip())

        out += r'</td>'

        return out

    def nextlec(self):
        tmp = self.lecs.pop(0)
        tmp = tmp.split('&')
        out = r'<td style="width: 45%;">{0}</td><td style="width: 25%;">{1}</td>'.format(re.sub('~',' ',tmp[0].strip()),re.sub('~',' ',tmp[1].strip()))
        self.leccounter += 1
        return out

    def nexthw(self):
        out = r'<td style="width: 15%;">HW {0}<br/>Due {1}</td>'.format(self.hwcounter,\
                self.p.sub(self.convbf,self.hwdates.pop(0).strip()))
        self.hwcounter += 1
        return out


ll = mylecs2(basepath)

out = '''<table style="border-collapse: collapse; width: 100%;" border="1">
<tbody>
<tr><td style="width: 5%;">Week</td><<td style="width: 5%;">Dates</td><td style="width: 45%;">Topic</td><td style="width: 25%;">Supplemental Reading</td><td style="width: 15%;">Homework</td></tr>
'''

out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #1
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #2
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #3
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #4
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #5
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #6
out += '<tr><td style="background-color: #eeeeee;" colspan=5>No classes 10/14</td></tr>\n'
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #7
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #8
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #9
out += "<tr>"+ll.nextweek()+ll.nextdates(3)+ll.nextlec()+ll.nexthw()+"</tr>\n" #10
out += "<tr>"+ll.nextweek()+ll.nextdates(2)+ll.nextlec()+ll.nexthw()+"</tr>\n" #11
out += "<tr>"+ll.nextweek()+ll.nextdates(3)+ll.nextlec()+ r'<td style="width: 15%;">Project Drafts <br/> Due 12/16</td></tr>\n' #12
out += '<tr><td style="background-color: #eeeeee;" colspan=5>Last Day of Classes 12/16. Final Exams 12/17-12/21</td></tr>\n'

out+='''
</tbody>
</table>'''

with open('/Users/ds264/Downloads/feh.html','w') as f: f.write(out)

