"""

@author: gaprice@lbl.gov
"""


def assert_exception_correct(got: Exception, expected: Exception):
    assert type(got) == type(expected)
    assert got.args == expected.args
