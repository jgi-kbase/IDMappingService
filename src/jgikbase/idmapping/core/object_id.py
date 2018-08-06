"""
Classes for specifying a unique ID for some data object. An object id consists of an ID and the
namespace in which that ID resides. For instance, a namespace might be 'NCBI_Refseq' and the
ID might be 'GCF_001598195.1'. The ID is expected to be unique and immutable within a particular
namespace.
"""
from jgikbase.idmapping.core.util import check_string, not_none, no_Nones_in_iterable
from jgikbase.idmapping.core.user import User
from typing import Set

# may want to consider a superclass for simple IDs that does checking & implements hash & eq


class NamespaceID:
    """
    An ID for a namespace, for example 'NCBI_Refseq'.

    :ivar id: the namespace ID.
    """

    __slots__ = ['id']

    def __init__(self, id_: str) -> None:
        '''
        Create a namespace ID.

        :param id_: A string identifier for a namespace, consisting of the characters a-zA-Z_0-9
            and no longer than 256 characters.
        :raises MissingParameterError: if the id is None or whitespace only.
        :raises IllegalParameterError: if the id does not match the requirements.
        '''
        check_string(id_, 'namespace id', 'a-zA-Z0-9_', 256)
        self.id = id_

    def __eq__(self, other):
        if type(other) is type(self):
            return other.id == self.id
        return False

    def __hash__(self):
        return hash((self.id,))


class Namespace:
    """
    A namespace.

    :ivar namespace_id: the namespace's ID.
    :ivar is_publicly_mappable: whether the namespace is publicly mappable or not.
    :ivar authed_users: users that are authorized to administer the namespace.
    """

    # TODO NS add user def/updatable attributes: free text desc, source (kbase/jgi), env (ci), db.

    def __init__(
            self,
            namespace_id: NamespaceID,
            is_publicly_mappable: bool,
            authed_users: Set[User]=None
            ) -> None:
        '''
        Create a namespace.

        :param namespace_id: the ID of the namespace.
        :param is_publicly_mappable: whether the namespace is publicly mappable or not.
        :param authed_users: users that are authorized to administer the namespace.
        :raises TypeError: if namespace_id is None or authed_users contains None
        '''
        not_none(namespace_id, 'namespace_id')
        self.namespace_id = namespace_id
        self.is_publicly_mappable = is_publicly_mappable
        self.authed_users = frozenset(authed_users) if authed_users else frozenset()
        no_Nones_in_iterable(self.authed_users, 'authed_users')

    def without_users(self):
        '''
        Returns a copy of this namespace with an empty authed_users field.
        '''
        return Namespace(self.namespace_id, self.is_publicly_mappable, None)

    def __eq__(self, other):
        if type(self) is type(other):
            return (self.namespace_id == other.namespace_id and
                    self.is_publicly_mappable == other.is_publicly_mappable and
                    self.authed_users == other.authed_users)
        return False

    def __hash__(self):
        return hash((self.namespace_id, self.is_publicly_mappable, self.authed_users))


class ObjectID:
    '''
    An object ID consisting of a namespace ID and the ID of the data object within the namespace.

    :ivar namespace_id: The ID of the namespace.
    :ivar id: The ID of the data object.
    '''

    __slots__ = ['namespace_id', 'id']

    def __init__(self, namespace_id: NamespaceID, data_id: str) -> None:
        """
        Create a new object ID.

        :param namespace_id: The ID of the namespace in which the data ID resides.
        :param data_id: The ID of the data unit, no more than 1000 characters.
        :raises TypeError: if the namespace ID is None.
        :raises MissingParameterError: if the data ID is None or whitespace only.
        :raises IllegalParameterError: if the data ID does not meet the requirements.
        """
        not_none(namespace_id, 'namespace_id')
        check_string(data_id, 'data id', max_len=1000)  # should maybe check for control chars
        self.namespace_id = namespace_id
        self.id = data_id

    def __eq__(self, other):
        if type(other) is type(self):
            return other.namespace_id == self.namespace_id and other.id == self.id
        return False

    def __hash__(self):
        return hash((self.namespace_id, self.id))
