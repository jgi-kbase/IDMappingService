from jgikbase.idmapping.builder import IDMappingBuilder, IDMappingBuildException
from unittest.mock import create_autospec, Mock
from jgikbase.idmapping.cli import IDMappingCLI
from jgikbase.idmapping.core.user_handler import LocalUserHandler
from jgikbase.idmapping.core.user import Username
from pathlib import Path
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct

# TODO CLI at some point, test usage and invalid args. Since argparse calls exit() when this
# happens, it'll need exec() tests, or futzing with argparse.


def test_init_fail_None_input():
    b = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    fail_init(None, [], out, err, TypeError('builder cannot be None'))
    fail_init(b, None, out, err, TypeError('args cannot be None'))
    fail_init(b, ['-h', None], out, err, TypeError('None item in args'))
    fail_init(b, [], None, err, TypeError('stdout cannot be None'))
    fail_init(b, [], out, None, TypeError('stderr cannot be None'))


def fail_init(builder, args, out, err, expected):
    with raises(Exception) as got:
        IDMappingCLI(builder, args, out, err)
    assert_exception_correct(got.value, expected)


def test_no_input():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    assert IDMappingCLI(builder, [], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (('One of --list-users or --user must be specified.\n',), {})]


def test_fail_build():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.side_effect = IDMappingBuildException(
        "I'm sorry, something just fell out of my ear")

    assert IDMappingCLI(builder, ['--list-users'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (("Error: I'm sorry, something just fell out of my ear\n",), {})]


def test_fail_build_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.side_effect = IDMappingBuildException(
        "I'm sorry, something just fell out of my ear")

    assert IDMappingCLI(builder, ['--list-users', '--verbose'], out, err).execute() == 1
    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == ((
        "Error: I'm sorry, something just fell out of my ear\n",), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert "IDMappingBuildException: I'm sorry" in err.write.call_args_list[1][0][0]


def test_list_users():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.return_value = {Username('c'): False, Username('b'): True, Username('a'): False}

    assert IDMappingCLI(builder, ['--list-users'], out, err).execute() == 0

    assert builder.build_local_user_handler.call_args_list == [((Path('./deploy.cfg'),), {})]
    assert luh.get_users.call_args_list == [((), {})]

    assert out.write.call_args_list == [(('* indicates an administrator:\n',), {}),
                                        (('a\n',), {}),
                                        (('b *\n',), {}),
                                        (('c\n',), {})]
    assert err.write.call_args_list == []


def test_fail_list_users():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.side_effect = OSError('this is improbable')

    assert IDMappingCLI(builder, ['--list-users'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [(('Error: this is improbable\n',), {})]


def test_fail_list_users_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.side_effect = OSError('this is improbable')

    assert IDMappingCLI(builder, ['--list-users', '--verbose'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == (('Error: this is improbable\n',), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert 'OSError: this is improbable' in err.write.call_args_list[1][0][0]
