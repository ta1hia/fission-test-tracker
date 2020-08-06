import json

from groups import Group, Test


def get_tests_from_spreadsheet(service, spreadsheet_id, sheet_name):
    """Pulls down the latest copy of an existing Google sheet and 
    generates a list of Groups."""
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
    test_map = Group.from_csv_spreadsheet(res['values'])
    return test_map  # Used for generating 'existing_tests'


def get_tests_from_report(report):
    """Loads tests from a json report (ie './mach test-info report ...')"""
    if type(report) is 'str':
        with open(report) as f:
            data = json.load(f)['tests']
    else:
        data = report.get('tests')

    test_map = {}
    for group, subtests in data.items():
        g = Group(group, subtests)
        test_map[group] = g
    return test_map  # Used for generating 'incoming_tests'


def clear_sheet(service, spreadsheet_id, sheet_id):
    """Clears a sheet of its contents and cell formatting"""
    body = {"requests":[{"updateCells":{"range":{"sheetId":sheet_id},"fields":"userEnteredFormat"}},{"unmergeCells":{"range":{"sheetId":sheet_id}}}]}
    # We need to do this to overwrite merged rows for component names 
    # since those component names might be on a different row number 
    # between sheet updates.
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                       body=body).execute()


def merge_tests(existing_tests, incoming_tests):
    """Given two sets of tests, merge the incoming tests into
    the existing tests."""

    # The merge will take the following steps:
    #   - already seen tests will only have "opt/debug_status" updated
    #   - newly failing tests will be added under the appropriate component
    #    - tests that are no longer failing will be marked as "passes" rather 
    #   than be removed from the resulting set
    #   - tests that were already marked as "passes" and still pass in a
    #   subsequent run of the script will be removed from the result set
    

    
    newly_failing, newly_passing, passing_removed = [], [], []
    not_seen_group = set(existing_tests.keys())

    def handle_passing_tests(group_name, not_seen):
        for test_name in list(not_seen): # leftover tests are no longer failing/skipped
            if existing_tests[group_name].tests[test_name].opt_status == 'passes' and \
                    existing_tests[group_name].tests[test_name].debug_status == 'passes':
                existing_tests[group_name].tests.pop(test_name)
                passing_removed.append(test_name)
            else:
                existing_tests[group_name].tests[test_name].opt_status = 'passes'
                existing_tests[group_name].tests[test_name].debug_status = 'passes'
                newly_passing.append(test_name)

    for group_name, incoming_group in incoming_tests.items():
        not_seen_group.discard(group_name)
        if group_name not in existing_tests:
            existing_tests[group_name] = Group(group_name, [])
        not_seen = set(existing_tests[group_name].tests.keys())
        for test_name, new_test in incoming_group.tests.items():
            if new_test.name in not_seen:  # test exists, so update fields
                for attr in ['opt_status', 'debug_status', 'xorig_and_fis', 'xorig_and_not_fis']:
                    setattr(existing_tests[group_name].tests[test_name], attr, getattr(new_test, attr))
                not_seen.discard(test_name)
            else: # new test
                existing_tests[group_name].tests[test_name] = new_test
                newly_failing.append(test_name)

        handle_passing_tests(group_name, not_seen)
        if len(existing_tests[group_name].tests) == 0:
            existing_tests.pop(group_name)

    for group_name in list(not_seen_group):
        handle_passing_tests(group_name, existing_tests[group_name].tests)
        existing_tests.pop(group_name)

    return existing_tests, newly_failing, newly_passing, passing_removed
