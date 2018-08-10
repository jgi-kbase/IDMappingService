from jgikbase.idmapping.builder import IDMappingBuilder
from flask.app import Flask
from flask import request
from jgikbase.idmapping.core.errors import NoTokenError, AuthenticationError,\
    ErrorType, IllegalParameterError, IDMappingError, NoDataException, UnauthorizedError,\
    MissingParameterError
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.object_id import NamespaceID, ObjectID
from http.client import responses  # @UnresolvedImport dunno why pydev cries here, it's stdlib
import flask
from typing import List, Tuple, Optional, Set, Dict
import traceback
from werkzeug.exceptions import MethodNotAllowed, NotFound
from operator import itemgetter
import json
from json.decoder import JSONDecodeError

# TODO LOG all calls & errors
# TODO ROOT with gitcommit, version, servertime
# TODO CODE try getting rid of src dir and see what happens

# Set up a blueprint later if necessary
# Not sure what's worth doing here for documentation. Swagger at some point ideally.

# The bulk methods are currently implemented soley in the API layer. This keeps things simple
# and required less work. Push the bulk implementation further down in the stack as necessitated
# by peformance needs.

# NOTE 1: I *&*_&*& hate flask. If you do `request.headers.get()`, it parses the data and, if
#         the content-type header says form data, will set request.data to None
#         (which means request.get_data() is also None). So you can't get the data if you
#         don't care about the content type, which you don't if the client is curl, which
#         always sets content-type to form data if you use --data. That means you always
#         have to set content-type manually from curl, even if the service only accepts json.
#         Stupid.
#
#         What's even better is that I can't figure out how to replicate this behavior in
#         the unit tests.

_APP = 'ID_MAPPER'

_TRUE = 'true'
_FALSE = 'false'


def _format_error(err: Exception, httpcode: int, errtype: ErrorType=None, errprefix: str=''):
    traceback.print_exc()  # TODO LOG remove when logging works
    errjson = {'httpcode': httpcode,
               'httpstatus': responses[httpcode],
               'message': errprefix + str(err)}
    if errtype:
        errjson['appcode'] = errtype.error_code
        errjson['apperror'] = errtype.error_type
    return (flask.jsonify({'error': errjson}), httpcode)
    # TODO LOG log error
    # TODO ERR call id, time


def _get_auth(request, required=True) -> Tuple[Optional[AuthsourceID], Optional[Token]]:
    """
    :returns None if required is False and there is no authorization header.
    :raises NoTokenError: if required is True and there's no authorization header.
    :raises InvalidTokenError: if the authorization header is malformed.
    :raises IllegalParameterError: if the authsource is illegal.
    """
    auth = request.headers.get('Authorization')
    if not auth:
        if required:
            raise NoTokenError()
        return (None, None)
    auth = auth.strip().split()
    if len(auth) != 2:
        raise IllegalParameterError('Expected authsource and token in header.')
    return AuthsourceID(auth[0]), Token(auth[1])


def _users_to_jsonable(users: List[User]) -> List[str]:
    return sorted([u.authsource_id.id + '/' + u.username.name for u in users])


def _objids_to_jsonable(oids: Set[ObjectID]):
    return sorted([{'ns': o.namespace_id.id, 'id': o.id} for o in oids],
                  key=itemgetter('ns', 'id'))


def _get_object_id_dict_from_json(request) -> Dict[str, str]:
    # flask has a built in get_json() method but the errors it throws suck.
    ids = json.loads(request.data)
    if not isinstance(ids, dict):
        raise IllegalParameterError('Expected JSON mapping in request body')
    if not ids:
        raise MissingParameterError('No ids supplied')
    for id_ in ids:
        # json keys must be strings
        if not id_.strip():
            raise MissingParameterError('whitespace only key in input JSON')
        val = ids[id_]
        if not isinstance(val, str):
            raise IllegalParameterError('value for key {} in input JSON is not string: {}'.format(
                id_, val))
        if not val.strip():
            raise MissingParameterError('value for key {} in input JSON is whitespace only'.format(
                id_))
    return ids


def _get_object_id_list_from_json(request) -> List[str]:
    # flask has a built in get_json() method but the errors it throws suck.
    body = json.loads(request.data)
    if not isinstance(body, dict):
        raise IllegalParameterError('Expected JSON mapping in request body')
    ids = body.get('ids')
    if not isinstance(ids, list):
        raise IllegalParameterError('Expected list at /ids in request body')
    if not ids:
        raise MissingParameterError('No ids supplied')
    for id_ in ids:
        if not id_ or not id_.strip():
            raise MissingParameterError('null or whitespace-only id in list')
    return ids


def create_app(builder: IDMappingBuilder=IDMappingBuilder()):
    """ Create the flask app. """
    app = Flask(__name__)
    app.url_map.strict_slashes = False  # otherwise GET /loc/ won't match GET /loc
    app.config[_APP] = builder.build_id_mapping_system()

    ##########
    # Endpoints
    ##########

    @app.route('/api/v1/namespace/<namespace>', methods=['PUT', 'POST'])
    def create_namespace(namespace):
        """ Create a namespace. """
        authsource, token = _get_auth(request)
        app.config[_APP].create_namespace(authsource, token, NamespaceID(namespace))
        return ('', 204)

    @app.route('/api/v1/namespace/<namespace>/user/<authsource>/<user>', methods=['PUT'])
    def add_user_to_namespace(namespace, authsource, user):
        """ Add a user to a namespace. """
        admin_authsource, token = _get_auth(request)
        app.config[_APP].add_user_to_namespace(admin_authsource, token, NamespaceID(namespace),
                                               User(AuthsourceID(authsource), Username(user)))
        return ('', 204)

    @app.route('/api/v1/namespace/<namespace>/user/<authsource>/<user>', methods=['DELETE'])
    def remove_user_from_namespace(namespace, authsource, user):
        """
        Remove a user from a namespace. Removing a non-existant user throws an error.
        """
        admin_authsource, token = _get_auth(request)
        app.config[_APP].remove_user_from_namespace(
            admin_authsource, token, NamespaceID(namespace),
            User(AuthsourceID(authsource), Username(user)))
        return ('', 204)

    @app.route('/api/v1/namespace/<namespace>/set', methods=['PUT'])
    def set_namespace_params(namespace):
        """ Change settings on a namespace. """
        authsource, token = _get_auth(request)
        pubmap = request.args.get('publicly_mappable')
        if pubmap:  # expand later if more settings are allowed
            if pubmap not in [_TRUE, _FALSE]:
                raise IllegalParameterError(
                    "Expected value of 'true' or 'false' for publicly_mappable")
            app.config[_APP].set_namespace_publicly_mappable(
                authsource, token, NamespaceID(namespace), pubmap == _TRUE)
        return ('', 204)

    @app.route('/api/v1/namespace/<namespace>', methods=['GET'])
    def get_namespace(namespace):
        """ Get a namespace. """
        authsource, token = _get_auth(request, False)
        ns = app.config[_APP].get_namespace(NamespaceID(namespace), authsource, token)
        return flask.jsonify({'namespace': ns.namespace_id.id,
                              'publicly_mappable': ns.is_publicly_mappable,
                              'users': _users_to_jsonable(ns.authed_users)})

    @app.route('/api/v1/namespace', methods=['GET'])
    def get_namespaces():
        """ Get all namespaces. """
        public, private = app.config[_APP].get_namespaces()
        return flask.jsonify({'publicly_mappable': sorted([ns.id for ns in public]),
                              'privately_mappable': sorted([ns.id for ns in private])})

    @app.route('/api/v1/mapping/<admin_ns>/<other_ns>', methods=['PUT', 'POST'])
    def create_mapping(admin_ns, other_ns):
        """ Create a mapping. """
        request.get_data()  # see note 1) above
        authsource, token = _get_auth(request)
        ids = _get_object_id_dict_from_json(request)
        if len(ids) > 10000:
            raise IllegalParameterError('A maximum of 10000 ids are allowed')
        for id_ in ids:
            app.config[_APP].create_mapping(authsource, token,
                                            ObjectID(NamespaceID(admin_ns), id_.strip()),
                                            ObjectID(NamespaceID(other_ns), ids[id_].strip()))
        return ('', 204)

    @app.route('/api/v1/mapping/<admin_ns>/<other_ns>', methods=['DELETE'])
    def remove_mapping(admin_ns, other_ns):
        """ Remove a mapping. """
        request.get_data()  # see note 1) above
        authsource, token = _get_auth(request)
        ids = _get_object_id_dict_from_json(request)
        if len(ids) > 10000:
            raise IllegalParameterError('A maximum of 10000 ids are allowed')
        for id_ in ids:
            app.config[_APP].remove_mapping(authsource, token,
                                            ObjectID(NamespaceID(admin_ns), id_.strip()),
                                            ObjectID(NamespaceID(other_ns), ids[id_].strip()))
        return ('', 204)

    @app.route('/api/v1/mapping/<ns>/', methods=['GET'])
    def get_mappings(ns):
        """ Find mappings. """
        request.get_data()  # see note 1) above
        ns_filter = request.args.get('namespace_filter')
        separate = request.args.get('separate')
        if ns_filter and ns_filter.strip():
            ns_filter = [NamespaceID(n.strip()) for n in ns_filter.split(',')]
        else:
            ns_filter = []
        ids = _get_object_id_list_from_json(request)
        if len(ids) > 1000:
            raise IllegalParameterError('A maximum of 1000 ids are allowed')
        ret = {}
        for id_ in ids:
            id_ = id_.strip()
            a, o = app.config[_APP].get_mappings(ObjectID(NamespaceID(ns), id_), ns_filter)
            if separate is not None:  # empty string if in query with no value
                ret[id_] = {'admin': _objids_to_jsonable(a), 'other': _objids_to_jsonable(o)}
            else:
                a.update(o)
                ret[id_] = {'mappings': _objids_to_jsonable(a)}
        return flask.jsonify(ret)

    ##################################
    # error handlers
    ##################################

    @app.errorhandler(IDMappingError)
    def general_app_errors(err):
        """ Handle general application errors. These are user-caused and always map to 400. """
        return _format_error(err, 400, err.error_type)

    @app.errorhandler(JSONDecodeError)
    def json_errors(err):
        """ Handle invalid input JSON. """
        return _format_error(err, 400, errprefix='Input JSON decode error: ')

    @app.errorhandler(AuthenticationError)
    def authentication_errors(err):
        """ Handle authentication errors. """
        return _format_error(err, 401, err.error_type)

    @app.errorhandler(UnauthorizedError)
    def authorization_errors(err):
        """ Handle authorization errors. """
        return _format_error(err, 403, err.error_type)

    @app.errorhandler(NoDataException)
    def no_data_errors(err):
        """ Handle requests for data, such as namespaces, that don't exist. """
        return _format_error(err, 404, err.error_type)

    @app.errorhandler(NotFound)
    def not_found_errors(err):
        """ Handle plain old not found errors thrown by Flask. """
        return _format_error(err, 404)

    @app.errorhandler(MethodNotAllowed)
    def method_not_allowed(err):
        """ Handle invalid method requests. """
        return _format_error(err, 405)

    @app.errorhandler(Exception)
    def all_errors(err):
        """ Catch-all error handler of last resort """
        return _format_error(err, 500)

    return app
