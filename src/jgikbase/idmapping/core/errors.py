"""
Exceptions thrown by the ID mapping system.
"""
from enum import Enum


class ErrorType(Enum):
    """
    The type of an error, consisting of an error code and a brief string describing the type.

    :ivar error_code: an integer error code.
    :ivar error_type: a brief string describing the error type.
    """

    AUTHENTICATION_FAILED =  (10000, "Authentication failed")  # noqa: E222 @IgnorePep8
    """ A general authentication error. """

    NO_TOKEN =               (10010, "No authentication token")  # noqa: E222 @IgnorePep8
    """ No token was provided when required. """

    INVALID_TOKEN =          (10020, "Invalid token")  # noqa: E222 @IgnorePep8
    """ The token provided is not valid. """

    UNAUTHORIZED =           (20000, "Unauthorized")  # noqa: E222 @IgnorePep8
    """ The user is not authorized to perform the requested action. """

    MISSING_PARAMETER =      (30000, "Missing input parameter")  # noqa: E222 @IgnorePep8
    """ A required input parameter was not provided. """

    ILLEGAL_PARAMETER =      (30001, "Illegal input parameter")  # noqa: E222 @IgnorePep8
    """ An input parameter had an illegal value. """

    ILLEGAL_USER_NAME =      (30010, "Illegal user name")  # noqa: E222 @IgnorePep8
    """ The provided user name was not legal. """

    USER_EXISTS =            (40000, "User already exists")  # noqa: E222 @IgnorePep8
    """ The user could not be created because it already exists. """

    NAMESPACE_EXISTS =       (40010, "Namespace already exists")  # noqa: E222 @IgnorePep8
    """ The namespace could not be created because it already exists. """

    NO_SUCH_USER =           (50000, "No such user")  # noqa: E222 @IgnorePep8
    """ The requested user does not exist. """

    NO_SUCH_NAMESPACE =      (50010, "No such namespace")  # noqa: E222 @IgnorePep8
    """ There is no namespace with the specified name. """

    UNSUPPORTED_OP =         (60000, "Unsupported operation")  # noqa: E222 @IgnorePep8
    """ The requested operation is not supported. """

    def __init__(self, error_code, error_type):
        self.error_code = error_code
        self.error_type = error_type


class IDMappingError(Exception):
    """
    The super class of all ID mapping related errors.

    :ivar error_type: the error type of this error.
    :ivar message: the message for this error.
    """

    def __init__(self, error_type: ErrorType, message: str=None) -> None:
        '''
        Create an ID mapping error.

        :param error_type: the error type of this error.
        :param message: an error message.
        :raises TypeError: if error_type is None
        '''
        if not error_type:  # don't use not_none here, causes circular import
            raise TypeError('error_type cannot be None')
        msg = '{} {}'.format(error_type.error_code, error_type.error_type)
        if message and message.strip():
            msg += ': ' + message.strip()
        super().__init__(msg)
        self.error_type = error_type
        self.message = message


class NoDataException(IDMappingError):
    """
    An error thrown when expected data does not exist.
    """

    def __init__(self, error_type: ErrorType, message: str) -> None:
        super().__init__(error_type, message)


class NoSuchUserError(NoDataException):
    """
    An error thrown when a user does not exist.
    """

    def __init__(self, message: str) -> None:
        super().__init__(ErrorType.NO_SUCH_USER, message)


class NamespaceExistsError(IDMappingError):
    """
    An error thrown when a namespace already exists.
    """

    def __init__(self, message: str) -> None:
        super().__init__(ErrorType.NAMESPACE_EXISTS, message)


class UserExistsError(IDMappingError):
    """
    An error thrown when a user already exists and therefore cannot be created.
    """

    def __init__(self, message: str) -> None:
        super().__init__(ErrorType.USER_EXISTS, message)


class AuthenticationError(IDMappingError):
    """
    An error thrown when authentication of a user fails.
    """

    def __init__(self, error_type: ErrorType=ErrorType.AUTHENTICATION_FAILED, message: str=None
                 ) -> None:
        super().__init__(error_type, message)


class InvalidTokenError(AuthenticationError):
    """
    An error thrown when a provided token is invalid.
    """

    def __init__(self, message: str=None) -> None:
        super().__init__(ErrorType.INVALID_TOKEN, message)


class MissingParameterError(IDMappingError):
    """
    An error thrown when a required parameter is missing.
    """

    def __init__(self, message: str=None) -> None:
        super().__init__(ErrorType.MISSING_PARAMETER, message)


class IllegalParameterError(IDMappingError):
    """
    An error thrown when a provided parameter is illegal.
    """

    def __init__(self, message: str=None) -> None:
        super().__init__(ErrorType.ILLEGAL_PARAMETER, message)


class IllegalUsernameError(IDMappingError):
    """
    An error thrown when a provided username is illegal.
    """

    def __init__(self, message: str=None) -> None:
        super().__init__(ErrorType.ILLEGAL_USER_NAME, message)
