# fission test tracker


Scripts for updating Google Spreadsheet reports for Fission mochitests.  

### Set Up

You'll need to create a Google API account and project, enable the Google Sheets API on that project and generate a "credentials.json" file via the Google Cloud console. Run through Step 1 of the [Sheets APIv4 Python Quickstart](https://developers.google.com/sheets/api/quickstart/python) to generate the file and save it in the root of this directory. 

Initialize a python3 virtual environment:
```sh
python3 -m venv /path/to/new/virtual/environment
source /path/to/new/virtual/environment/bin/activate
pip install -r requirements.txt 
```

### Usage

```sh
spreadsheet.py --config [path-to-config]
```
