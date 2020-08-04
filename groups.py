import re

not_fission_re = re.compile(r'(?<!!)fission')
debug_re = re.compile(r'fission && \(?debug')
opt_re = re.compile(r'fission && !debug')
xorigin_re = re.compile(r'xorigin && fission')


def match(condition, debug):
    if not condition:
        return False
    if debug:
        return not opt_re.search(condition) and (debug_re.search(condition) or
                                                 not_fission_re.search(condition))
    else:
        return not debug_re.search(condition) and (opt_re.search(condition) or
                                                 not_fission_re.search(condition))


def get_status(test, debug):
    if match(test.get('skip-if'), debug):
        return 'skipped'
    if match(test.get('fail-if'), debug):
        return 'fails'
    return 'passes'


class Test(object):

    bug_id = ''
    module_owner = ''
    assignee = ''
    manager = ''
    xorigin_only = ''
    fission_target = ''
    comment = ''

    def __init__(self, group, data=None):
        self.group = group
        if not data:
            return
        self.name = data.get('test', '')
        self.opt_status = get_status(data, False)
        self.debug_status = get_status(data, True)
        self.comment = data.get('comment', '')
        self.xorigin_only = self.is_xorigin_only(data)

    def is_xorigin_only(self, data):
        if (self.opt_status != 'passes' or self.debug_status != 'passes')\
            and (xorigin_re.search(data.get('skip-if', '')) or
                 xorigin_re.search(data.get('fail-if', ''))):
            return "Y"
        return self.xorigin_only

    @classmethod
    def from_csv_row(cls, group, row):
        test = cls(group)
        labels = ['bug_id', 'name', 'opt_status', 'debug_status', 
                  'module_owner', 'assignee', 'manager', 'xorigin_only', 
                  'fission_target', 'comment']
        for i, attr in enumerate(row):
            setattr(test, labels[i], row[i])
        return test

    def __repr__(self):
        return self.name

class Group(object):

    def __init__(self, group, raw_tests):
        self.group = group
        self.tests = {}
        for t in raw_tests:
            test = Test(group, t)
            self.tests[test.name] = test

    @classmethod
    def from_csv_spreadsheet(cls, csv_result):
        # expects raw read of a spreadsheet
        groups = {}
        current_group = None
        for row in csv_result[1:]:
            if len(row) == 1:
                current_group = Group(row[0], [])
                groups[current_group.group] = current_group
                continue
            test = Test.from_csv_row(current_group.group, row)
            current_group.tests[test.name] = test
        groups[current_group.group] = current_group
        return groups

    def __repr__(self):
        return "{}({})".format(self.group, len(self.tests))
