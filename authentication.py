#!/usr/bin/env python
# vim:se sts=4 sw=4 et fenc=utf-8 ft=python:
import os.path
import pickle
import socket

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CREDS_JSON = os.path.join(BASE_DIR, 'credentials.json')
CREDS_PICKLE = os.path.join(BASE_DIR, 'credentials.pickle')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def auth():
    creds = None
    socket.setdefaulttimeout(300) # 5 minutes
    if os.path.exists(CREDS_PICKLE):
        with open(CREDS_PICKLE, 'rb') as fh:
            creds = pickle.load(fh)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not (creds and creds.valid):
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDS_JSON, SCOPES)
        creds = flow.run_local_server(port=0)
        #creds = flow.run_console()

    with open(CREDS_PICKLE, 'wb') as fh:
        pickle.dump(creds, fh)

    return creds
