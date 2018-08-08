from jgikbase.idmapping.builder import IDMappingBuilder, IDMappingBuildException
from unittest.mock import create_autospec, Mock
from jgikbase.idmapping.cli import IDMappingCLI
from jgikbase.idmapping.core.user_handler import LocalUserHandler
from jgikbase.idmapping.core.user import Username
from pathlib import Path
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.errors import UserExistsError, NoSuchUserError

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
        (('Exactly one of --list-users or --user must be specified.\n',), {})]


def test_too_much_input():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    assert IDMappingCLI(builder, ['--user', 'foo', '--list-users'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (('Exactly one of --list-users or --user must be specified.\n',), {})]


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


def test_alternate_config_location():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.get_users.return_value = {Username('c'): False, Username('b'): True, Username('a'): False}

    assert IDMappingCLI(builder, ['--list-users', '--config', 'someother.cfg'], out, err
                        ).execute() == 0

    assert builder.build_local_user_handler.call_args_list == [((Path('someother.cfg'),), {})]
    assert luh.get_users.call_args_list == [((), {})]

    assert out.write.call_args_list == [(('* indicates an administrator:\n',), {}),
                                        (('a\n',), {}),
                                        (('b *\n',), {}),
                                        (('c\n',), {})]
    assert err.write.call_args_list == []


def test_fail_user_no_op():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    assert IDMappingCLI(builder, ['--user', 'foo'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (('Exactly one of --create, --new-token, or --admin must be specified.\n',), {})]


def test_fail_user_multi_op():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    assert IDMappingCLI(builder, ['--user', 'foo', '--create', '--new-token'], out, err
                        ).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (('Exactly one of --create, --new-token, or --admin must be specified.\n',), {})]


def test_fail_user_illegal_admin_value():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    assert IDMappingCLI(builder, ['--user', 'foo', '--admin', 'fake'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (("--admin must have a value of 'true' or 'false'.\n",), {})]


def test_fail_user_illegal_username():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    assert IDMappingCLI(builder, ['--user', 'fo&o', '--admin', 'true'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [
        (('Error: 30010 Illegal user name: Illegal character in username fo&o: &\n',), {})]


def test_fail_user_illegal_username_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    assert IDMappingCLI(builder, ['--user', 'fo&o', '--admin', 'true', '--verbose'], out, err
                        ).execute() == 1

    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == (
        ('Error: 30010 Illegal user name: Illegal character in username fo&o: &\n',), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert 'IllegalUsernameError: 30010 Illegal user name' in err.write.call_args_list[1][0][0]


def test_user_set_admin():
    check_user_set_admin('true', True)
    check_user_set_admin('false', False)


def check_user_set_admin(adminstr, adminbool):
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh

    assert IDMappingCLI(builder, ['--user', 'foo', '--admin', adminstr], out, err).execute() == 0

    assert builder.build_local_user_handler.call_args_list == [((Path('./deploy.cfg'),), {})]
    assert luh.set_user_as_admin.call_args_list == [((Username('foo'), adminbool), {})]

    assert out.write.call_args_list == [(
        ("Set user foo's admin state to " + adminstr + '.\n',), {})]
    assert err.write.call_args_list == []


def test_user_fail_set_admin():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.set_user_as_admin.side_effect = OSError('this is improbable')

    assert IDMappingCLI(builder, ['--user', 'foo', '--admin', 'true'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [(('Error: this is improbable\n',), {})]


def test_user_fail_set_admin_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.set_user_as_admin.side_effect = OSError('this is improbable')

    assert IDMappingCLI(builder, ['--user', 'foo', '--admin', 'true', '--verbose'], out, err
                        ).execute() == 1

    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == (('Error: this is improbable\n',), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert 'OSError: this is improbable' in err.write.call_args_list[1][0][0]


def test_user_create():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.create_user.return_value = Token('tokenwhee')

    assert IDMappingCLI(builder, ['--user', 'foo', '--create'], out, err).execute() == 0

    assert builder.build_local_user_handler.call_args_list == [((Path('./deploy.cfg'),), {})]
    assert luh.create_user.call_args_list == [((Username('foo'),), {})]

    assert out.write.call_args_list == [(
        ('Created user foo with token:\ntokenwhee\n',), {})]
    assert err.write.call_args_list == []


def test_user_fail_create():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.create_user.side_effect = UserExistsError('foo')

    assert IDMappingCLI(builder, ['--user', 'foo', '--create'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [(('Error: 40000 User already exists: foo\n',), {})]


def test_user_fail_create_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.create_user.side_effect = UserExistsError('foo')

    assert IDMappingCLI(builder, ['--user', 'foo', '--create', '--verbose'], out, err
                        ).execute() == 1

    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == (('Error: 40000 User already exists: foo\n',), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert 'UserExistsError: 40000 User already exists: foo' in err.write.call_args_list[1][0][0]


def test_user_new_token():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.new_token.return_value = Token('tokenwhee')

    assert IDMappingCLI(builder, ['--user', 'foo', '--new-token'], out, err).execute() == 0

    assert builder.build_local_user_handler.call_args_list == [((Path('./deploy.cfg'),), {})]
    assert luh.new_token.call_args_list == [((Username('foo'),), {})]

    assert out.write.call_args_list == [(
        ("Replaced user foo's token with token:\ntokenwhee\n",), {})]
    assert err.write.call_args_list == []


def test_user_fail_new_token():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.new_token.side_effect = NoSuchUserError('foo')

    assert IDMappingCLI(builder, ['--user', 'foo', '--new-token'], out, err).execute() == 1

    assert out.write.call_args_list == []
    assert err.write.call_args_list == [(('Error: 50000 No such user: foo\n',), {})]


def test_user_fail_new_token_verbose():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    luh = create_autospec(LocalUserHandler, spec_set=True, instance=True)
    out = Mock()
    err = Mock()

    builder.build_local_user_handler.return_value = luh
    luh.new_token.side_effect = NoSuchUserError('foo')

    assert IDMappingCLI(builder, ['--user', 'foo', '--new-token', '--verbose'], out, err
                        ).execute() == 1

    assert out.write.call_args_list == []
    assert len(err.write.call_args_list) == 2
    assert err.write.call_args_list[0] == (('Error: 50000 No such user: foo\n',), {})
    assert 'Traceback' in err.write.call_args_list[1][0][0]
    assert 'NoSuchUserError: 50000 No such user: foo' in err.write.call_args_list[1][0][0]
