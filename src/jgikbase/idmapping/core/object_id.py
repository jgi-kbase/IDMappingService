"""
Classes for specifying a unique ID for some data object. An object id consists of an ID and the
namespace in which that ID resides. For instance, a namespace might be 'NCBI Refseq' and the
ID might be 'GCF_001598195.1'. The ID is expected to be unique and immutable within a particular
namespace.
"""

# TODO NOW


class NamespaceID:
    """
    An ID for a namespace, for example 'NCBI Refseq'.
    """

    def __init__(self, params):
        """
        Constructor
        """


class Namespace:
    """
    A namespace. Consists of an ID, whether the namespace is publicly mappable, users that have
    permissions to administer the namespace, and other properties.
    """

    def __init__(self, params):
        """
        Constructor
        """


class ObjectID:
    '''
    An object ID consisting of a namespace ID and the ID of the data object within the namespace.
    '''

    def __init__(self, params):
        '''
        Constructor
        '''
