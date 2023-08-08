# Missing Glue Code for Metadata Ingress Inter-service Communication (Tokay Gecko)
**Epic Type:** Implementation Epic

## Scope

This epic aims to fill in the missing parts in inter-service communication along the preliminary upload/ingress path provided for 1.0.

### Outline:

#### Metldata Service:

- Implement publisher for deletion and population events
- Needs to track current artifact resources in own DB and compute change sets for incoming artifacts
- Needs to upsert new/changed artifact resources
- Transforms embedded dataset resource information into form accepted by WPS for outgoing event

#### MASS:

- Add event subscriber for deletion and population events
- Add functionality to populate entities
- Add functionality to delete entities
- embedded_dataset artifact as input in form of MASS models.Resource
- Kafka Key Name: dataset_ebmedded_{id}

#### WPS:

- Receive event conforming to MetadataDatasetOverview from Metldata Service
- Adjust event subscriber config for population events (if needed)
- Kafka Key Name: dataset_embedded_{id}

#### Auth Service Claims Repository

- Add event subscriber to delete controlled access grant claims for a specific dataset

#### Sequence Diagram for Proposed Interactions

```mermaid
sequenceDiagram
  participant Kit as Datasteward Kit
  participant API as Metldata Service
  participant MASS
  participant claims as Claims Repository
  participant WPS

  Kit ->> API: Load artifacts from all submissions
  API ->> API: Query DB for existing artifact resources
  API ->> API: Compute the set of new, changed and unchanged artifact resources

  loop Each deleted embedded dataset resource
  API -->> MASS: Send deletion event for resource
  end

  loop Each deleted embedded dataset resource
  API -->> claims: Send deletion event for resource
  end

  API ->> API: Upsert new and changed resources, delete deleted resources

  loop Each new/changed embedded dataset resource
  API -->> MASS: Inform about resource upsert
  end

  loop Each new/changed embedded dataset resource
  API -->> WPS: Inform about resource upsert
  end
```

Kafka topic has to be the same for deletion and creation (where applicable) to guarantee order for events with same key - use type to distinguish.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
