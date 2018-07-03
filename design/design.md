# ID Mapping Service Design Document

## Service purpose

Provide a means for, given a data or object ID in a namespace, mapping that ID to an ID in a
different namespace for the equivalent data or object.

For example, the `NCBI Refseq` ID `GCF_001598195.1` maps to the `KBase CI` ID `15792/22/3`,
so the service would allow mapping the ID `GCF_001598195.1` in the namespace `NCBI Refseq`
to the ID `15792/22/3` in the namespace `KBase CI`, and vice versa.


## Prior work

Surprisingly, a Google search didn't turn up any obviously useful implementations that could be
reused. There are other ID mapping services available but they're source specific:

* [UniProt](https://www.uniprot.org/mapping/)
* [PATRIC](https://docs.patricbrc.org/user_guide/genome_feature_data_and_tools/id_mapping_tool.html)

## Definitions

* NID - Namespaced ID. A combination of an ID and the namespace it resides in. For example
  (`NCBI Refseq`, `GCF_001598195.1`).
* PNID - Primary Namespaced ID. This is used to determine who can create and delete a mapping (see
  below).
* DAL - Data Abstraction Layer.
* CLI - Command Line Interface.
* CSL - Comma Separated List.

## MVP Service Requirements

### Mappings

* A mapping is a tuple of (NID 1, NID 2). One of the NIDs is designated as the PNID by the 
  creator of the mapping (see below).
* All mappings are publicly readable.
* It is possible that an NID may map to multiple data in another namespace, so
  it is expected there may exist multiple tuples containing a particular NID.
* Therefore, the only uniqueness constraint in the system is that each tuple is unique - e.g.
  there are no duplicate records.
* The service must allow ID lookups based on either NID of the tuple.
* The service must return all NIDs associated with the lookup NID unless filters are specified.
  * The service must allow filtering results by namespace.
* Arbitrary key-value metadata, not to exceed 1KB serialized as a JSON map,
  may be attached to each NID in a tuple upon creation of the tuple. This may be useful for
  providing information about the targets of the NID.
  * For example, NCBI IDs map to both a Genome and Assembly object in KBase, and the metadata
   may be used by an application to select which object to retrieve.
  * This metadata is not searchable.
* Mappings may be deleted.

### Namespaces

* All namespaces are publicly readable.
* Once created, a namespace may not be deleted.
* Every namespace has one or more administrators.
* A namespace may be publicly mappable. At creation a namespace is not publicly mappable but
  this property may be changed by namespace administrators at will.
* It is expected that fewer than 1000 namespaces exist in the system, although there is no hard
  limit.

### Creating and deleting mappings
* To create a mapping including a namespace that is not publicly mappable, a user must be an
  administrator of that namespace.
* When creating a mapping, the user must specify which NID is the PNID, and the user must be
  an administrator for the namespace in the NID.
* To delete a mapping, the user must be an administrator of the namespace in which the PNID
  exists.

Less abstractly, the PNID can be thought of as the user's 'home' namespace, and the other NID
as the 'target' namespace. Typically the target will be a public repository of data, like NCBI,
and the home will be a system associated with the user, like KBase. The user would often have
administration rights on the home system, but not on the target, but the target would typically
be publicly mappable such that the user can create a mapping from their system to the public
system.

### Administration

* One or more general administrators can create namespaces and add and
  remove namespace administrators. The general administrators do not have any other privileges for
  the namespaces, but can always add themselves to a namespace.

## Design

* HTTP / REST-ish interface
  * Try to avoid MIME encoding if at all possible
* Mappings are stored in MongoDB (with a DAL so alternative storage systems can be swapped in
  via implementing the DAL interface)
* Administration of namespace creation and administrator assignment is done via a CLI that
  interfaces with the DAL directly
  * Practically this means anyone with MongoDB credentials for and network access to the database
    is a general administrator
  * The CLI allows for creating user accounts associated with a token which can be provided to
    the user out of band. The token is hashed and stored in the database. Any token expiration
    policies are handled manually via the CLI. A user account is an arbitrary name matching the
    regex `$[a-z][a-z0-9]+^` and an associated token.
  * The CLI allows for associating user accounts to namespaces in a many-to-many relationship.

### Constraints

* A namespace matches the regex `$[a-zA-Z0-9_]+^`
* IDs are unconstrained other than they cannot be whitespace-only.
  * As such, IDs must be URL-encoded when appearing in a URL if they contain any url-unsafe
    characters.

### API

`[Auth source]` defines the source of authentication information and currently exists to
provide for the possibility of alternative authentication sources in the future. In the first
iteration of the service the only authentication source will be `Local`.

#### List namespaces

```
GET /api/v1/namespace/

RETURNS:
[{"namespace": <namespace1>,
  "publicly_mappable": <boolean1>
  },
  ...
  {"namespace": <namespaceN>,
  "publicly_mappable": <booleanN>
  }
 }
]
```

#### Show namespace

```
GET /api/v1/namespace/<namespace>

RETURNS:
{"namespace": <namespace>,
 "publicly_mappable": <boolean>
 }
```

#### Create a mapping

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<primary namespace>/map/<primary ID>/<target namespace>/<target ID>
{"pnid_meta": {"key1": "value1",
               ...
               "keyN": "valueN"},
 "other_meta": {"key", "value"}
 }
 
RETURNS:
{"pnid": {"namespace": <primary namespace>,
          "id": <primary ID>,
          "meta": {...}
          },
 "other": {"namespace": <target namespace>,
           "id": <target ID>,
           "meta": {...}
           }
 }
```

Both meta keys, as well as the PUT body in its entirety, are optional.

#### List mappings

```
GET /api/v1/namespace/<namespace>/map/<ID>/[?namespace_filter=<namespace CSL>]

RETURNS:
[{"namespace": <namespace1>,
  "id: <id1>,
  "meta": {...},
  "is_primary": <boolean1>
  },
  ...
 {"namespace": <namespaceN>,
  "id: <idN>,
  "meta": {...},
  "is_primary": <booleanN>
  }
 } 
]
```

#### Delete a mapping

```
HEADERS:
Authorization: [Auth source] <token>

DELETE /api/v1/namespace/<namespace>/map/<primary ID>/<target namespace>/<target ID>
```

#### Alter namespace

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>/set/?publicly_mappable=<true or false>

RETURNS:
{"namespace": <namespace>,
 "publicly_mappable": <boolean>
 }
```

## Future work

* Bulk mapping creation and search endpoints.
* Provide administrator access via outside authentication systems, such as KBase and JGI auth.

