from jgikbase.idmapping.builder import IDMappingBuilder
from flask.app import Flask
from flask import request
from jgikbase.idmapping.core.errors import NoTokenError, AuthenticationError,\
    ErrorType, IllegalParameterError, IDMappingError, NoDataException
from jgikbase.idmapping.core.user import AuthsourceID, User
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.object_id import NamespaceID
from http.client import responses  # @UnresolvedImport dunno why pydev cries here, it's stdlib
import flask
from typing import List, Tuple, Optional
import traceback
from werkzeug.exceptions import MethodNotAllowed

# TODO LOG all calls & errors
# TODO ROOT with gitcommit, version, servertime

# Set up a blueprint later if necessary


def _format_error(err: Exception, httpcode: int, errtype: ErrorType=None):
    traceback.print_exc()  # TODO LOG remove when logging works
    errret = {'httpcode': httpcode,
              'httpstatus': responses[httpcode],
              'message': str(err)}
    if errtype:
        errret['appcode'] = errtype.error_code
        errret['apperror'] = errtype.error_type
    return (flask.jsonify({'error': errret}), httpcode)
    # TODO LOG log error
    # TODO ERR call id, time


def _get_auth(request, required=True) -> Optional[Tuple[AuthsourceID, Token]]:
    """
    :returns None if required is False and there is no authorization header.
    :raises NoTokenError: if required is True and there's no authorization header.
    :raises InvalidTokenError: if the authorization header is malformed.
    :raises IllegalParameterError: if the authsource is illegal.
    """
    auth = request.headers.get('Authorization')
    if not auth:
        if required:  # TODO TEST
            raise NoTokenError()
        return None
    auth = auth.strip().split()
    if len(auth) != 2:
        raise IllegalParameterError('Expected authsource and token in header.')
    return AuthsourceID(auth[0]), Token(auth[1])


def _users_to_jsonable(users: List[User]) -> List[str]:
    return sorted([u.authsource_id.id + '/' + u.username.name for u in users])


def create_app(builder: IDMappingBuilder=IDMappingBuilder()):
    """ Create the flask app. """
    app = Flask(__name__)
    app.config['ID_MAPPER'] = builder.build_id_mapping_system()

    @app.route('/api/v1/namespace/<namespace>', methods=['GET'])
    def get_namespace(namespace):
        """ Get a namespace. """
        auth = _get_auth(request, False)
        if auth:
            ns = app.config['ID_MAPPER'].get_namespace(NamespaceID(namespace), auth[0], auth[1])
        else:
            ns = app.config['ID_MAPPER'].get_namespace(NamespaceID(namespace))
        return flask.jsonify({'namespace': ns.namespace_id.id,
                              'publicly_mappable': ns.is_publicly_mappable,
                              'users': _users_to_jsonable(ns.authed_users)})

    @app.errorhandler(IDMappingError)
    def general_app_error(err):
        """ Handle general application errors. These are user-caused and always map to 400. """
        return _format_error(err, 400, err.error_type)

    @app.errorhandler(AuthenticationError)
    def auth_errors(err):
        """ Handle authentication errors. """
        return _format_error(err, 401, err.error_type)

    # TODO ERR Unauthorized

    @app.errorhandler(NoDataException)
    def no_data_error(err):
        """ Handle requests for data, such as namespaces, that don't exist. """
        return _format_error(err, 404, err.error_type)

    @app.errorhandler(MethodNotAllowed)
    def method_not_alllowed(err):
        """ Handle invalid method requests. """
        return _format_error(err, 405)

    @app.errorhandler(Exception)
    def all_errors(err):
        """ Catch-all error handler of last resort """
        return _format_error(err, 500)

    return app
