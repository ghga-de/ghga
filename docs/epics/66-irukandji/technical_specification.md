# Schemapack (Irukandji)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).

## Scope

### Outline:
This epic aims to make datapack navigation independent of its corresponding schemapack. Currently, since the relation class is not explicitly provided in the datapack, resolving target classes requires referring back to the schemapack. This epic introduces changes to eliminate this dependency, allowing the datapack to be self-contained for navigation.

Additionally, this epic introduces configurable embedding depth in datapack denormalization. This ensures more control over how deeply related entities are embedded, enabling partial embedding instead of always including all related data at the highest level.

### Included/Required:

#### Example datapacks/schemapacks

Update all examples so that the datapack also contains the targetClass, targetResources, rootResource and rootClass if it is specified in schemapack. 

#### Datapack specification

1. The datapack specification will check that the elements—rootResource, rootClass, targetResources, and targetClass—exist within the datapack
   1. The functionality of `unknown_root_resource.py` will be incorporated into the datapack specification.
   2. The functionality of `target_id.py` will also be integrated into the datapack specification.
   3. Checks for the existence of rootClass, targetResources, rootResource, and targetClass will be implemented.

2. The above-mentioned checks to ensure that a datapack conforms to its specifications will utilize Pydantic validators.

#### Validation Plugins

1. The following validators will remain unchanged:
   1. `content_schema.py`
   2. `missing_class.py`
   3. `missing_origin.py`
   4. `missing_relations.py`
   5. `missing_target.py`
   6. `multiple_target.py`
   7. `one_to_many_overlap.py`
   8. `unknown_class.py`
   9. `unknown_relations.py`
2.  The following validators are obsolete and can be deleted:
    1. `unknown_root_resource.py`, since the functionality is shifted to datapack specification. 
    2. `target_id.py`, since the functionality is shifted to datapack specification. 

3. If schemapack has a root class defined, `expected_root` plugin checks that the datapack has a root resource. 
   1. Extend `expected_root.py`, so that it checks if the datapack also has a root class. 
4. If schemapack does not have a root class, `unexpected_root` checks that datapack does not have a root resource. 
   1. Extend it, so that it checks that datapack does not have a root class defined either. 



#### Embedded Profiles

The denormalization process currently embeds all related entities into a single JSON output at the highest level. A configurable denormalization depth to allow more control over how deeply related entities are embedded will be implemented.

For example, given that an experiment has relations to sample, sample has relations to files, the current implementation of denormalization embeds everything into the experiment including the complete information of the files referred by the samples. However, implementing an embedding depth will enable the denormalization of the experiment that embed samples but will keep the referred file information unchanged/not embedded. 

The new implementation will allow the embedding until a given depth. The current denormalize is a recursive function which will be converted to depth-limited recursion. The function will take an integer depth parameter that controls how many levels of references should be expanded.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
