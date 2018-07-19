from jgikbase.idmapping.util.util import not_none, check_string
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pytest import fail
from jgikbase.idmapping.util import util


def test_not_none_pass():
    not_none(4, 'integer')
    not_none('four', 'text')


def test_not_none_fail():
    try:
        not_none(None, 'my name')
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, ValueError('my name cannot be None'))


def test_check_string_pass():
    check_string('mystring', 'myname')
    check_string('foo', 'bar', max_len=3)
    check_string('foo', 'bar', legal_characters='fo')
    check_string('foo', 'bar', 'fo', 3)


def test_check_string_fail():
    fail_check_string(None, 'foo', None, None, ValueError('foo cannot be None'))
    fail_check_string('   \t   \n   ', 'foo', None, None,
                      ValueError('foo cannot be whitespace only'))
    fail_check_string('bar', 'foo', None, 2, ValueError('foo bar exceeds maximum length of 2'))
    fail_check_string('b_ar&_1', 'foo', 'a-z_', None,
                      ValueError('Illegal character in foo b_ar&_1: &'))

    # this is reaching into the implementation which is very naughty but I don't see a good way
    # to check the cache is actually working otherwise
    assert util._REGEX_CACHE['a-z_'].pattern == '[^a-z_]'

    # test with cache
    fail_check_string('b_ar&_1', 'foo', 'a-z_', None,
                      ValueError('Illegal character in foo b_ar&_1: &'))


def fail_check_string(string, name, illegal_characters, max_len, expected):
    try:
        check_string(string, name, illegal_characters, max_len)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
