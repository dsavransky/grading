from datetime import datetime, timedelta
import re
import os.path
import json
import copy


def genSemesterCalendar(
    classdays=[0, 2, 4], datesfile="semester_dates.json", outfile="lecture_dates.txt"
):
    """
    Generate semester calendar for specific class meeting days.
    classdays is an array of days of the week (0 for monday).
    The default [0,2,4] is MWF.
    """

    with open(datesfile) as f:
        data = json.load(f)

    dateparse = re.compile(
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s*-{0,1}\s*(\d{1,2}/\d{1,2}/\d{2,4})*"
    )

    firstday = datetime.strptime(
        dateparse.match(data["firstday"]).groups()[0], "%m/%d/%Y"
    )
    lastday = datetime.strptime(
        dateparse.match(data["lastday"]).groups()[0], "%m/%d/%Y"
    )
    noclass = []
    for b in data["breaks"]:
        tmp = dateparse.match(b).groups()
        st = datetime.strptime(tmp[0], "%m/%d/%Y")
        if tmp[1]:
            nd = datetime.strptime(tmp[1], "%m/%d/%Y")
            while (nd - st).days >= 0:
                noclass.append(st)
                st += timedelta(days=1)
        else:
            noclass.append(st)

    now = copy.copy(firstday)
    cal = []

    # loop from first day to last day
    while (lastday - now).days >= 0:
        # add if class day and not day off
        if (now.weekday() in classdays) and (now not in noclass):
            cal.append(now.strftime("%-m/%-d"))
        now += timedelta(days=1)

    lecture_dates = os.path.join(outfile)
    with open(lecture_dates, "w") as f:
        for c in cal:
            f.write("%s\n" % c)
