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

* TBD

## Future work

* Provide administrator access via outside authentication systems, such as KBase and JGI auth.
