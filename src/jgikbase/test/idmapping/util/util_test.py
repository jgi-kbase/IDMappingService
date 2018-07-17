from jgikbase.idmapping.util.util import not_none
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pytest import fail


def test_not_none_obj_pass():
    not_none(4, 'integer')


def test_not_none_string_pass():
    not_none('four', 'text')


def test_not_none_obj_fail():
    fail_not_none(None, 'my name', ValueError('my name cannot be None'))


def test_not_none_str_fail():
    fail_not_none('   \t   \n   ', 'my name',
                  ValueError('my name cannot be None or whitespace only'))


def fail_not_none(obj: object, name: str, expected: Exception):
    try:
        not_none(obj, name)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
