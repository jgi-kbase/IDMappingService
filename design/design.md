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

* OID - Object ID. A combination of an ID and the namespace it resides in. For example
  (`NCBI Refseq`, `GCF_001598195.1`).
* AOID - Administrative Object ID. This is used to determine who can create and delete a
  mapping (see below).
* DAL - Data Abstraction Layer.
* CLI - Command Line Interface.
* CSL - Comma Separated List.

## MVP Service Requirements

### Mappings

* A mapping is a tuple of (OID 1, OID 2). One of the OIDs is designated as the AOID by the 
  creator of the mapping (see below).
* All mappings are publicly readable.
* It is possible that an OID may map to multiple data in another namespace, so
  it is expected there may exist multiple tuples containing a particular OID.
* Therefore, the only uniqueness constraint in the system is that each tuple is unique - e.g.
  there are no duplicate records.
  * Note that there may be 2 copies of a particular tuple - one with the AOID in one namespace,
    and the other with the AOID in the other namespace.
* The service must allow ID lookups based on either OID of the tuple.
* The service must return all OIDs associated with the lookup OID unless filters are specified.
  * The service must allow filtering results by namespace.
* Mappings may be deleted.

### Namespaces

* All namespaces are publicly readable.
* Once created, a namespace may not be deleted.
* Every namespace has zero or more administrators.
* A namespace may be publicly mappable. At creation a namespace is not publicly mappable but
  this property may be changed by namespace administrators at will.
* It is expected that fewer than 1000 namespaces exist in the system, although there is no hard
  limit.

### Creating and deleting mappings
* To create a mapping including a namespace that is not publicly mappable, a user must be an
  administrator of that namespace.
* When creating a mapping, the user must specify which OID is the AOID, and the user must be
  an administrator for the namespace in the OID.
* To delete a mapping, the user must be an administrator of the namespace in which the AOID
  exists.

Less abstractly, the AOID can be thought of as the user's 'home' namespace, and the other OID
as the 'target' namespace. Typically the target will be a public repository of data, like NCBI,
and the home will be a system associated with the user, like KBase. The user would often have
administration rights on the home system, but not on the target, but the target would typically
be publicly mappable such that the user can create a mapping from their system to the public
system.

### Administration

* One or more super administrators can add users to the system, generate new tokens for those users,
  and designate those users as system administrators.

* One or more system administrators can create namespaces and add and
  remove namespace administrators. The system administrators do not have any other privileges for
  the namespaces, but can always add themselves to a namespace.

## Design

* HTTP / REST-ish interface
  * Try to avoid MIME encoding if at all possible
* Mappings are stored in MongoDB (with a DAL so alternative storage systems can be swapped in
  via implementing the DAL interface)
* Administration of user creation and administrator assignment is done via a CLI that
  interfaces with the DAL directly
  * Practically this means anyone with MongoDB credentials for and network access to the database
    is a super administrator
  * The CLI allows for creating local user accounts associated with a token which can be provided
    to the user out of band. The token is hashed and stored in the database. Any token expiration
    policies are handled manually via the CLI. A user account is an arbitrary name matching the
    regex `$[a-z][a-z0-9]+^` and an associated token.
  * The CLI allows for making a local user a system administrator or removing that ability.
  * The CLI allows for listing all local users in the system and their administrative ability.

### Constraints

* A namespace matches the regex `$[a-zA-Z0-9_]+^` with a maximum length of 256 characters.
* IDs are unconstrained other than they cannot be whitespace-only and have a maximum length of
  1000 characters.
  * As such, IDs must be URL-encoded when appearing in a URL if they contain any url-unsafe
    characters.

### API

`[Auth source]` defines the source of authentication information and currently exists to
provide for the possibility of alternative authentication sources in the future. In the first
iteration of the service the only authentication source will be `local`.

#### Create a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>
```

POST is also accepted.

#### Add a user to a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>/user/<authsource>/<username>
```

#### Remove a user from a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

DELETE /api/v1/namespace/<namespace>/user/<authsource>/<username>
```

#### Alter namespace

Requires the user to be namespace administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>/set/?publicly_mappable=<true or false>
```


#### Show namespace

```
HEADERS (optional):
Authorization: [Auth source] <token>

GET /api/v1/namespace/<namespace>

RETURNS:
{"namespace": <namespace>,
 "publicly_mappable": <boolean>,
 "users": [<authsource>/<username>, ...]
 }
```

The `users` field is only populated if the `Authorization` header is supplied and the user is
a namespace or general administrator.

#### List namespaces

```
GET /api/v1/namespace/

RETURNS:
{"publicly_mappable": [<namespace>, ...],
 "privately_mappable": [<namespace>, ...]
}
```

#### Create a mapping

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/mapping/<administrative namespace>/<namespace>/
{"admin_id": <administrative id>,
 "other_id": <id>
 }
```

POST is also accepted, although not strictly correct.

#### List mappings

```
GET /api/v1/mapping/<namespace>/[?namespace_filter=<namespace CSL>][?separate]
{"id": <id>}

RETURNS:
if not separate:
    {"mappings": [{"namespace": <namespace1>, "id": <id1>},
                   ...
                  {"namespace": <namespaceN>, "id": <idN>}
                  ]
     }
else:
    {"admin": [{"namespace": <namespace1>, "id": <id1>},
                ...
               {"namespace": <namespaceN>, "id": <idN>}
               ],
     "other": [{"namespace": <namespaceN+1>, "id": <idN+1>},
                ...
               {"namespace": <namespaceN+M>, "id": <idN+M>}
               ]
     }
```

The namespaces in the `admin` key are administrative namespaces; those in the `other` key are
not. Note that a mapping may occur twice in the output - once in the `admin` section and once in
the `other` section.

#### Delete a mapping

```
HEADERS:
Authorization: [Auth source] <token>

DELETE /api/v1/mapping/<administrative namespace>/<namespace>/
{"admin_id": <administrative id>,
 "other_id": <id>
 }
```

## Future work

* Bulk mapping creation and search endpoints.
* Provide administrator access via outside authentication systems, such as KBase and JGI auth.
