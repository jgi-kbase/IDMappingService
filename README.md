# Joint JGI / KBASE ID Mapping Service

This repo contains the JGI / KBase ID Mapping Service (IMS). The service provides for mapping
IDs in one namespace (e.g. [NCBI](https://www.ncbi.nlm.nih.gov/)) to another (e.g. JGI).

For example, the `NCBI Refseq` ID `GCF_001598195.1` maps to the `KBase CI` ID `15792/22/3`,
so the service could store the mapping from the ID `GCF_001598195.1` in the namespace
`NCBI Refseq` to the ID `15792/22/3` in the namespace `KBase CI`, and vice versa.

Build status (master):
[![Build Status](https://travis-ci.org/jgi-kbase/IDMappingService.svg?branch=master)](https://travis-ci.org/jgi-kbase/IDMappingService)
[![codecov](https://codecov.io/gh/jgi-kbase/IDMappingService/branch/master/graph/badge.svg)](https://codecov.io/gh/jgi-kbase/IDMappingService)

## Abbreviations:

* IMS - ID Mapping Service
* JGI - Joint Genome Institute
* CLI - Command Line Interface
* CSL - Comma Separated List

## Requirements

* Python 3.6+
* MongoDB 2.6+
* Make
* git

The system is tested on Ubuntu, but should probably work on other operating systems.

## Usage

There are three kinds of users for the service:

* System administrators can create namespaces and add and remove administrators from namespaces.
* Namespace administrators are assigned by system administrators and can change settings and
  create and remove mappings on the namespaces they administrate.
* Standard users can read namespaces and mappings.

All administration activity requires authentication. Reading (most) data does not.

### Authentication

The service supports multiple sources of authentication and is extensible. There are two built in
authentication sources: `local` and `kbase`. The `local` authentication source is the
IMS database itself, where users can be created via a CLI. The `kbase` authentication source
contacts a [KBase](https://kbase.us) authentication server to obtain authentication information.

Authentication sources are used to:

* Get an immutable, permanent user ID given a token
* Verify that user IDs are valid
* Determine whether a user is a system administrator according to the authentication source.
  * This behavior can be enabled or disabled on a per authentication source basis in the
    `deploy.cfg` file.

See the `deploy.cfg.example` file for more information regarding how to configure authentication
sources.

#### Adding new authentication sources

To add a new authentication source:

1. Implement the `jgikbase.idmapping.core.user_lookup.UserLookup` interface.
   1. `get_authsource_id()` must return an `AuthsourceID` with the same value as the name of
      the authsource in the `deploy.cfg` file. Legal authsource IDs consist solely of lowercase
      ASCII letters.
2. Implement a module level function called build_lookup that takes a `Dict[str, str]` of
   configuration parameters and returns a `UserLookup` instance for the authsource.
3. Configure the new authentication source in the `deploy.cfg` file.

See `jgikbase.idmapping.userlookup.kbase_user_lookup` and `deploy.cfg.example` for an
example.

Note that the user ID allowed character list is currently fairly restrictive (lowercase ASCII
letters and numbers) and may need adjustment for new authentication sources.

There exists a **prototype** authentication source implementation for JGI. This authsource should
not be used in production. To configure the JGI authsource, add the following lines to the
service's `deploy.cfg` file, and enable the authsource in the `authentication-enabled` key:

```
auth-source-jgi-factory-module=jgikbase.idmapping.userlookup.jgi_user_lookup_prototype
auth-source-jgi-init-url=https://signon.jgi.doe.gov

```

**WARNINGS:**

* The JGI authsource does not account for the fact that user accounts can be merged. If a user
  account is merged, the user will lose access to any namespaces associated with the no longer
  usable account.
* The JGI authsource uses integer user IDs as immutable IDs, as the user name is mutable. This
  means that JGI users returned in the API are not very readable. Displaying the user name
  as well is potentially difficult as many user names are presumably private email addresses.
* There is currently no way to specify JGI users as system admins.
* The JGI authsource is a prototype only and is undocumented and not automatically tested.
* The JGI authentication service is not accessible by the public.

In summary, more design and implementation is needed before the JGI authsource is ready for
production use, although it is a proof of concept.

### Namespaces and mappings

A namespace is an arbitrary string consisting of the characters a-z, A-Z, 0-9, and _ with a
maximum length of 256 characters. Once created, a namespace cannot be deleted. Namespaces may
have any number of mappings associated with them, limited by the capacity of the database.
It is expected, but not enforced, that the IMS will contain on the order of no more than 1000
namespaces.

A mapping is a tuple of (administrative namespace, administrative ID, namespace, ID) where 
IDs are arbitrary strings with a maximum length of 1000 characters. Administrators are
expected to load namespaces and mappings into the system that have appropriate semantics for their
domain.

Namespaces may be *publicly mappable*, which means that anyone can associate the non-administrative
portion of a mapping with the namespace. To create or delete a mapping, the user must always be an
administrator of the administrative namespace (e.g. the first namespace in the mapping tuple).
If neither namespace is publicly mappable, the user must be an administrator of both namespaces
to create a mapping. To remove a mapping, the user need only be an administrator of the
administrative namespace.

Mappings are public, and anyone can read them. Namespaces are publicly readable except for the
administrator list, which is only readable by system administrators and other namespace
administrators for that namespace.

### Setup

* Install the runtime dependencies
  * `pip install -r requirements.txt`
* Start MongoDB
* From the IDMappingService repo:
	* `make`
	* Copy `deploy.cfg.example` to `deploy.cfg` and fill in the MongoDB parameters

### Adding local users via the CLI

Local user administration is done via the `id_mapper` CLI tool. Execute `id_mapper --help`
to get information about running the CLI. Example usage:

```
IDMappingService$ ./id_mapper --list-users
* indicates an administrator:

IDMappingService$ ./id_mapper --user myname1 --create
Created user myname1 with token:
ZAM0eUgKvWAoPkNHgEPjAckTw3Q=

IDMappingService$ ./id_mapper --user myname2 --create
Created user myname2 with token:
iAChByXJr3Og4gk+Ui/g03aMCLA=

IDMappingService$ ./id_mapper --user myname2 --admin true
Set user myname2's admin state to true.

IDMappingService$ ./id_mapper --user myname2 --new-token
Replaced user myname2's token with token:
FgG4OpIc1/7bx2V3fxUjRK0eV3w=

IDMappingService$ ./id_mapper --list-users
* indicates an administrator:
myname1
myname2 *

IDMappingService$ ./id_mapper --user myname2 --admin false
Set user myname2's admin state to false.

IDMappingService$ ./id_mapper --list-users
* indicates an administrator:
myname1
myname2
```

### Starting the service

```
IDMappingService$ export ID_MAPPING_CONFIG=/<path to repo>/IDMappingService/deploy.cfg

IDMappingService$ export PYTHONPATH=./src

IDMappingService$ gunicorn --worker-class gevent --timeout 300 --workers 17 --bind :5000 app:app
[2018-08-16 12:42:44 -0700] [4957] [INFO] Starting gunicorn 19.9.0
[2018-08-16 12:42:44 -0700] [4957] [INFO] Listening at: http://0.0.0.0:5000 (4957)
*snip*
```

## API

`[Auth source]` defines the source of authentication information, e.g. `local`, `kbase`, etc.

## Root

```
GET /

RETURNS:
{"service": "ID Mapping Service",
 "version": <service version>,
 "gitcommithash": <git commit>,
 "servertime": <ms since epoch>
 }
```

### Create a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>
```

POST is also accepted.

### Add a user to a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>/user/<authsource>/<username>
```

### Remove a user from a namespace

Requires the user to be a system administrator.

```
HEADERS:
Authorization: [Auth source] <token>

DELETE /api/v1/namespace/<namespace>/user/<authsource>/<username>
```

### Alter namespace

Requires the user to be namespace administrator.

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/namespace/<namespace>/set/?publicly_mappable=<true or false>
```


### Show namespace

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
a namespace or system administrator.

### List namespaces

```
GET /api/v1/namespace/

RETURNS:
{"publicly_mappable": [<namespace>, ...],
 "privately_mappable": [<namespace>, ...]
}
```

### Create mappings

```
HEADERS:
Authorization: [Auth source] <token>

PUT /api/v1/mapping/<administrative namespace>/<namespace>/
{<administrative id1>: <id1>,
 ...
 <administrative idN>: <idN>
 }
```

POST is also accepted, although not strictly correct.

A maximum of 10000 ids may be supplied.

### List mappings

```
GET /api/v1/mapping/<namespace>/[?namespace_filter=<namespace CSL>][&separate]
{"ids": [<id1>, ..., <idN>]}

RETURNS:
if not separate:
    {<id1>: {"mappings" [{"ns": <namespace1_1>, "id": <id1_1>},
                          ...
                         {"ns": <namespace1_N>, "id": <id1_N>}
                         ]
             },
     ...
     <idN>: {"mappings" [{"ns": <namespaceN_1>, "id": <idN_1>},
                          ...
                         {"ns": <namespaceN_N>, "id": <idN_N>}
                         ]
             }
     }
else:
    {<id1>: {"admin": [{"ns": <namespace1_1>, "id": <id1_1>},
                        ...
                       {"ns": <namespace1_N>, "id": <id1_N>}
                       ],
             "other": [{"ns": <namespace1_N+1>, "id": <id1_N+1>},
                        ...
                       {"ns": <namespace1_N+M>, "id": <id1_N+M>}
                      ]
             },
      ...
     <idN>: {"admin": [{"ns": <namespaceN_1>, "id": <idN_1>},
                        ...
                       {"ns": <namespaceN_N>, "id": <idN_N>}
                       ],
             "other": [{"ns": <namespaceN_N+1>, "id": <idN_N+1>},
                        ...
                       {"ns": <namespaceN_N+M>, "id": <idN_N+M>}
                      ]
             },
     }
```

A maximum of 1000 ids may be supplied.

The mappings in the `admin` key are mappings where the provided half of the mapping
is the administrative half - e.g. the namespace in the url is the administrative namespace
in the mapping. Mappings in the `other` key denote mappings where the provided half of the
mapping is not the administrative half.

### Delete mappings

```
HEADERS:
Authorization: [Auth source] <token>

DELETE /api/v1/mapping/<administrative namespace>/<namespace>/
{<administrative id1>: <id1>,
 ...
 <administrative idN>: <idN>
 }
```

A maximum of 10000 ids may be supplied.

## Developer notes

### Adding and releasing code

* Adding code
  * All code additions and updates must be made as pull requests directed at the develop branch.
    * All tests must pass and all new code must be covered by tests.
    * All new code must be documented appropriately
      * Sphinx code documentation
      * General documentation if appropriate
      * Release notes
* Releases
  * The master branch is the stable branch. Releases are made from the develop branch to the master
    branch.
  * Update the version as per the semantic version rules in `src/jgikbase/idmapping/service/mapper_service.py`.
  * Tag the version in git and github.

### Running tests

* Copy `test.cfg.example` to `test.cfg` and fill in the values appropriately.
  * If it works as is start buying lottery tickets immediately.
* `make test`

### UI

Most text fields are arbitrary text entered by a data uploader. These fields should be
HTML-escaped prior to display.
  
Use common sense when displaying a field from the server regarding whether the field should be
html escaped or not.
  
### Exception mapping

In `jgikbase.idmapping.core.errors`:  
`IDMappingError` and subclasses other than the below - 400  
`AuthenticationError` and subclasses - 401  
`UnauthorizedError` and subclasses - 403  
`NoDataException` and subclasses - 404  


Other explicitly mapped errors:  
`json.decoder.JSONDecodeError` - 400  
`werkzeug.exceptions.NotFound` - 404  
`werkzeug.exceptions.MethodNotAllowed` - 405  

Anything else is mapped to 500.

## TODO

* travis
  * try mongo 4 - maybe wait for a couple bugfix versions
* integration tests with KBase auth server? - lot of work for little gain
* if performance becomes an issue
  * push the bulk operations further down the stack
  * shard mongo
  * swap the database implementation for something else (Cassandra?)
  * needs some testing / optimization here
* Delete all mappings from one namespace to another