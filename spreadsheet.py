#!/usr/bin/env python
# vim:se sts=4 sw=4 et fenc=utf-8 ft=python:
import sys
import json
import time

from configparser import ConfigParser
import googleapiclient.discovery
from authentication import auth  # noqa
from groups import Group, Test
from merge import *
from report import get_report

BATCH_SIZE = 100

COLOURS = {
    "gray": {"red": 0.5, "green": 0.5, "blue": 0.5, "alpha": 0.1},
    "red": {"red": 0.9, "green": 0, "blue": 0, "alpha": 0.1},
    "green": {"red": 0, "green": 0.9, "blue": 0, "alpha": 0.1},
    "blue": {"red": 0, "green": 0, "blue": 0.9, "alpha": 0.1},
}
COLOURS["passes"] = COLOURS["green"]
COLOURS["fails"] = COLOURS["red"]
COLOURS["skipped"] = COLOURS["blue"]


def text_format(bold=False, underline=False):
    return {"textFormat": {"bold":bold,"underline":underline}}


def colour(name):
    return {"backgroundColor":COLOURS[name]}


def borders(top=False, bottom=False, left=False, right=False):
    borders = {}
    if bottom:
        borders["bottom"] = {"style":"SOLID_MEDIUM"}
    return {"borders": borders}


def cell(value, ms_hyperlink=False, bz_hyperlink=False):
    if ms_hyperlink:
        cell = {
            "formulaValue": '=HYPERLINK("https://searchfox.org/mozilla-central/source/{}", "{}")'.format(value, value)
        }
    elif bz_hyperlink:
        cell = {
            "formulaValue": '=HYPERLINK("https://bugzilla.mozilla.org/show_bug.cgi?id={}", "{}")'.format(value, value)
        }
    else:
        cell = {"stringValue":value}
    return {"userEnteredValue": cell}


def row_values(args):
    values = []
    for v in args:
        value = {}
        value.update(cell(v.value, v.ms_hyperlink, v.bz_hyperlink))
        if v.colour or v.formatting:
            formatting =  {}
            if v.colour:
                formatting.update(colour(v.colour))
            if v.formatting:
                formatting.update(text_format(**v.formatting))
            if v.borders:
                formatting.update(borders(**v.borders))
            value["userEnteredFormat"] = formatting
        values.append(value)
    return {"values": values}

def request_update_cells(sheet_id, row_index, rows):
    req = {"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":row_index},"fields":"*"}}
    req["updateCells"]["rows"] = []
    for row in rows:
        req["updateCells"]["rows"].append(row_values(row))
    return req

def request_merge_row(sheet_id, row_index):
    return {"mergeCells":{"range":{"sheetId":sheet_id,"startRowIndex":row_index,"endRowIndex":row_index+1,"startColumnIndex":0},"mergeType":"MERGE_ALL"}}

class Cell:
    def __init__(self, value, colour=None, formatting=None, borders=None, ms_hyperlink=False, bz_hyperlink=False):
        self.value = value
        self.colour = colour
        self.formatting = formatting
        self.borders = borders
        self.ms_hyperlink = ms_hyperlink
        self.bz_hyperlink = bz_hyperlink

class MainHeader:
    fields = [Cell("Bug ID"), Cell("Test"), Cell("Opt Status"), Cell("Debug Status"), Cell("Module Owner"), Cell("Assignee"), Cell("Manager"), Cell("xorigin-only"), Cell("Fission Target"), Cell("Comments")]

    def requests(self, sheet_id, row):
        return [
        request_update_cells(sheet_id, row, [self.fields]),
        ]

class GroupHeader:

    def __init__(self, group):
        self.fields = [Cell(group, colour="gray", formatting={"bold": True}, borders={"bottom":True})]

    def requests(self, sheet_id, row):
        return [
            request_merge_row(sheet_id, row),
            request_update_cells(sheet_id, row, [self.fields]),
        ]

class TestRows:
    def __init__(self, tests):
        self.fields = []
        for test in tests:
            self.fields.append([
                Cell(test.bug_id, bz_hyperlink=True),  # Bug ID
                Cell(test.name, ms_hyperlink=True),  # Test
                Cell(test.opt_status, colour=test.opt_status),  # Opt Status
                Cell(test.debug_status, colour=test.debug_status),  # Debug Status
                Cell(test.module_owner),  # Module Owner
                Cell(test.assignee),  # Assignee
                Cell(test.manager),  # Manager
                Cell(test.xorigin_only),  # xorigin-only
                Cell(test.fission_target),  # Fission Target
                Cell(test.comment),  # Comment
             ])

    def requests(self, sheet_id, row):
        return [
            request_update_cells(sheet_id, row, self.fields),
        ]

def update_spreadsheet(service, incoming_report, spreadsheet_id, sheet_id, sheet_name):

    row = 0
    all_requests = []
    header = MainHeader()
    all_requests.extend(header.requests(sheet_id, row))
    row += 1

    existing_tests = get_tests_from_spreadsheet(service, spreadsheet_id, sheet_name)
    incoming_tests = get_tests_from_report(incoming_report)
    clear_sheet(service, spreadsheet_id, sheet_id)

    tests, newly_failing, newly_passing, passing_removed = merge_tests(existing_tests, incoming_tests)
    for component, group in tests.items():
        all_requests.extend(GroupHeader(component).requests(sheet_id, row))
        row += 1
        all_requests.extend(TestRows(list(group.tests.values())).requests(sheet_id, row))
        row += (len(group.tests))
        if len(all_requests) > BATCH_SIZE:
            r = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,body={"requests": all_requests}).execute()
            all_requests = []
            time.sleep(0.5)

    if all_requests:
            r = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,body={"requests": all_requests}).execute()
            all_requests = []

    return newly_failing, newly_passing, passing_removed


import argparse
import configparser

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', action='store',
                        help='path to configuration file')
    parser.add_argument('-r', '--report', dest='report', action='store',
                        help='path to json report file')
    parser.add_argument('-m', '--mode', dest='mode', action='store',
                        choices=['fisson', 'xorigin'], default='fission',
                        help='report type to pull down (defaults to fission)')
    parser.add_argument('--spreadsheet-id', dest='spreadsheet_id', action='store',
                        help='id of Google spreadsheeet')
    parser.add_argument('--sheet-name', dest='sheet_name', action='store',
                        help='name of Google sheet')
    parser.add_argument('--sheet-id', dest='sheet_id', action='store',
                        help='id of Google sheet within spreadsheet')
    args = parser.parse_args()

    config = None
    if args.config:
        config = configparser.ConfigParser()
        config.read(args.config)
        args.spreadsheet_id = config['DEFAULT']['spreadsheet_id']
        args.sheet_name = config['DEFAULT']['sheet_name']
        args.sheet_id = config['DEFAULT']['sheet_id']
    if not args.report:
        args.report = get_report(args.mode)
    if not (args.sheet_name or args.sheet_id or args.spreadsheet_id):
        print('specify a config file or spreadsheet_id, sheet_id, sheet_name')
        sys.exit()

    service = googleapiclient.discovery.build('sheets', 'v4', credentials=auth())
    newly_failing, newly_passing, passing_removed = \
        update_spreadsheet(service, args.report, args.spreadsheet_id,
                           args.sheet_id, args.sheet_name)

    if newly_failing:
        print("Newly failing tests added: ")
        for test in newly_failing: print(test)
    if newly_passing:
        print("\nNewly passing tests: ")
        for test in newly_passing: print(test)
    if passing_removed:
        print("\nPreviously passing tests removed: ")
        for test in passing_removed: print(test)
