# fission test tracker


Scripts for updating Google Spreadsheet reports for Fission mochitests.  

This script pulls down the latest fission and xorigin mochitest results against mozilla-central via the Treeherder API and merges any changes with the an existing report in Google Spreadsheets. It also preserves any comments/additional annotations in the spreadsheet between updates.

### Set Up

You'll need to create a Google API account and project, enable the Google Sheets API on that project and generate a "credentials.json" file via the Google Cloud console. Run through Step 1 of the [Sheets APIv4 Python Quickstart](https://developers.google.com/sheets/api/quickstart/python) to generate the file and save it in the root of this directory. 

Initialize a python3 virtual environment:
```sh
python3 -m venv [VENV_PATH]
source [VENV_PATH]/bin/activate
pip install -r requirements.txt 
```

### Usage


`spreadsheet.py -c [path-to-config]`


This repo includes a config file that points to the existing Fission+XOrigin mochitest spreadsheet in  `xorigin-and-fission.ini`.


`spreadsheet.py --config xorigin-and-fission.ini`


A daily cronjob could look something like this:

```sh
0 10 * * * [VENV_PATH]/bin/python [REPO_PATH]/spreadsheet.py -c xorigin-and-fission.ini >> /var/log/fission.spreadsheet.log 2>&1
```

### Development

##### Adding a new column to the spreadsheet

* Add the column name in the header row @ spreadsheet.py:MainHeader.fields
* Add the column value @ spreadsheet.py:TestRows.__init__

Both should be added at the exact index you want them to appear in your spreadsheet. 

#### Filtering based on a different skip-if/fail-if annotation

This script grabs test data based on test-info reports generated in TaskCluster CI runs, specifically [test-info-fission and test-info-xorigin](https://searchfox.org/mozilla-central/source/taskcluster/ci/source-test/file-metadata.yml#37,63).

It then filters and merges the tests from both reports based on regex matches (e.g. at the time of writing, we're only interested in 'xorigin && !fission' matches from the xorigin report). To change the filtering, see merge.py:get_full_report().

### Improvements

* Don't need to query both reports for the Fission team's current needs - can just query the xorigin report and filter for tests that are either "xorigin && fission" or "xorigin && !fission"
* This script outputs any changes in tests status (newly failing, newly passing, existing passing). These results could be outputted to #fission slack.
