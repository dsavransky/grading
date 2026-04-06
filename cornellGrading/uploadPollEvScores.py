from cornellGrading import cornellGrading
from cornellGrading.utils import email2netid
import argparse
import tomllib
from datetime import datetime
import os
import glob
import pandas


def main():
    parser = argparse.ArgumentParser(description=("Upload PollEv scores to Canvas."))

    parser.add_argument(
        "--date", help="Date string in format YYYY-MM-DD. Defaults to today's date."
    )
    parser.add_argument(
        "--infile", default="input_values.toml", help="Full path to input values file."
    )
    parser.add_argument(
        "--firstday",
        action="store_true",
        help="First day poll.  Only 1 point assigned for any participation.",
    )

    args = parser.parse_args()
    if args.date is not None:
        today = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        today = datetime.today()
    input_file = args.infile

    # locate and read toml file
    assert os.path.exists(input_file), f"Cannot locate input file {input_file}."
    with open(input_file, "rb") as f:
        data = tomllib.load(f)

    # load accommodations
    accommodations = pandas.read_excel(
        os.path.join(data["basepath"], "Accommodation_Request.xlsx")
    )
    accommodations["NetID"] = email2netid(accommodations["Email Address"].values)
    accom_cols = accommodations.columns[
        accommodations.columns.str.startswith("Exams")
        & accommodations.columns.str.contains("%")
    ]
    accom_netids = accommodations.loc[
        (accommodations[accom_cols] == "Yes").sum(axis=1).astype(bool), "NetID"
    ].values

    # connect to Canvas
    c = cornellGrading()
    c.getCourse(data["coursenum"])

    # find polling result
    polldir = os.path.join(data["basepath"], "Polls")
    pollfile = glob.glob(os.path.join(polldir, f"*{today.strftime('%m-%d-%Y')}*.csv"))
    assert len(pollfile) == 1
    pollfile = pollfile[0]
    pollname = f"Poll {today.strftime('%m/%d/%Y')}"

    if args.firstday:
        _ = c.importPollEvScores(
            pollfile,
            pollname,
            exempt_netids=accom_netids,
            max_correct_points=0,
            participation_points=1,
            participation_fraction=0.01,
        )
    else:
        _ = c.importPollEvScores(pollfile, pollname, exempt_netids=accom_netids)


if __name__ == "__main__":
    main()
