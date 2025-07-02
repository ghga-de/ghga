# Epic Docs

Documentation and plans for service development epics.

There are two different types of epics: Exploratory Epics and Implementation Epics.

Please have a look at the templates ([exploratory](./template_exploratory_epic), [implementation](./template_implementation_epic)) and especially the contained technical specifications ([exploratory](./template_exploratory_epic/technical_specification.md), [implementation](./template_implementation_epic/technical_specification.md)).

This repository is part of the [Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).

## The Saga so far

- (0) [Blobfish](./0-blob-fish/technical_specification.md): Basic Metadata Catalog & UI
- (1) [Red-Lipped Batfish](./1-red-lipped-batfish/technical_specification.md): Basic File IO Service
- (2) [Horseshoe Bat](./2-horseshoe-bat/technical_specification.md): Metadata Submission via REST API
- (4) [Star-Nosed Mole](./4-star-nosed-mole/technical_specification.md): Up-/Download Client & Production POC
- (7) [Domestic Quail](./7-domestic-quail/technical_specification.md): Pilot Study for 3-Hex Chassis Lib
- (8) [Carpenter Ant](./8-carpenter-ant/technical_specification.md): GA4GH-oriented Auth Concept
- (9) [Wood Ant](./9-wood-ant/technical_specification.md): Life Science AAI as Identity Provider
- (10) [Carrion Crow](./10-carrion-crow/technical_specification.md): File Tech Stack Exploration
- (11) [Golden Quail](./11-golden_quail/technical_specification.md): Expanding Hexkit to Abstract the Persistence Layer
- (12) [African Bush Elephant](./12-african-bush-elephant/technical_specification.md): Metadata Submission via Data Portal UI
- (13) [Hawaiian Crow](./13-hawaiian-crow/technical_specification.md): S3 File I/O Benchmarking using hexkit and CLI
- (14) [Coral Guard Crab](./14-coral-guard-crab/technical_specification.md): OIDC and API gateway integration
- (15) [Morning Sun Star](./15-morning-sun-star/technical_specification.md): Basic User Registry
- (16) [Cuban Crow](./16-cuban-crow/technical_specification.md): Prototyping Encryption & Decryption Workflow
- (17) [Amitermes](./17-amitermes/technical_specification.md): Hexagonal File Service Refactoring
- (18) [Hooded Crow](./18-hooded-crow/technical_specification.md): File Encryption & Decryption Services
- (19) [Pied Crow](./19-pied-raven/technical_specification.md): File Encryption & Decryption Service Integration
- (20) [Red Knob Sea Star](./20-red-knob-sea-star/technical_specification.md): Claims Repository
- (21) [White Stork](./21-white_stork/technical_specification.md): Synthetic Data Generator
- (22) [Crayfish](./22-crayfish/technical_specification.md): Exploration and conception for the metadata service refactoring
- (23) [Thick Billed Raven](./23-thick-billed-raven/technical_specification.md): Integration of all File Services - Upload Stream
- (24) [Common Raven](./24-common-raven/technical_specification.md): Integration of all File Services - Download Stream
- (25) [Pacific Lamprey](./25-pacific_lamprey/technical_specification.md): Metadata refactoring proof of concept
- (26) [Dracula Ant](./26-dracula-ant/technical_specification.md): Implementation of a Work Package Service for CLI client authentication
- (27) [Paddlefish](./27-paddlefish/technical_specification.md): Implementation of encryption and parallel file part processing in uploads and downloads for ghga-connector
- (28) [Giant Weta](./28-giant_weta/technical_specification.md): Batch Download for the CLI Client
- (29) [Humphead Wrasse](./29-humphead-wrasse/technical_specification.md): Notification Service
- (30) [Purple Frog](./30-purple_frog/technical_specification.md): Integration of Connector (CLI) with the Work Package Service
- (31) [Red Kangaroo](./31-red-kangaroo/technical_specification.md): Angular/Vue for Data Portal
- (32) [Pink Velvet Worm](./32-pink-velvet-worm/technical_specification.md): Reimplementation of metadata search service
- (33) [Green Wrasse](./33-green-wrasse/technical_specification.md): Download Request Management
- (34) [Chinese Pangolin](./34-chinese-pangolin/technical_specification.md): File Deletion and Outbox Cache Strategy
- (35) [Beluga Whale](./35-beluga-whale/technical_specification.md): Archive Testing Framework - Happy Path
- (36) [Axolotl](./36-axolotl/technical_specification.md): Biomedical Metadata Mocking
- (37) [Proboscis Monkey](./37-proboscis-monkey/technical_specification.md): Upload Metadata Ingest and Unique S3 ID for Permanent Storage
- (38) [Tokay Gecko](./38-tokay-gecko/technical_specification.md): Missing Glue Code for Metadata Ingress Inter-service Communication
- (39) [Red-Necked Wallaby](./39-red-necked-wallaby/technical_specification.md): Upload refactoring and cleanup
- (40) [Agile Wallaby](./40-agile-wallaby/technical_specification.md): Prepare for Federated Object Storage
- (41) [Nautilus](./41-nautilus/technical_specification.md): Refactoring Priorities
- (42) [Eurasian Wolf](./42-eurasian_wolf/technical_specification.md): Custom Specification Separating Schema Validation and Schema Linkage
- (43) [Marabou Stork](./43-marabou-stork/technical_specification.md): Correlation ID Implementation
- (44) [Common Wallaroo](./44-common-wallaroo/technical_specification.md): Choose frontend framework and component library
- (45) [Topi Antelope](./45-topi-antelope/technical_specification.md): Structured Logging Tools
- (46) [Sugar Ant](./46-sugar-ant/technical_specification.md): Integrate 2FA and IVA functionality
- (47) [Bluestreak Cleaner Wrasse](./47-bluestreak-cleaner-wrasse/technical_specification.md): Automatically remove stale content from buckets
- (48) [Kori Bustard](./48-kori-bustard/technical_specification.md): Notification Orchestration Service
- (49) [Jackal](./49-jackal/technical_specification.md): Re-Implementation of the Metadata Schema in Schemapack
- (50) [Dhole](./50-dhole/technical_specification.md): Rewriting existing metldata transformations
- (51) [Ethiopian Wolf](./51-ethiopian-wolf/technical_specification.md): Monorepo Setup for Multiple Microservices
- (52) [Hero Shrew](./52-hero-shrew/technical_specification.md): Outbox Pattern Refactoring
- (53) [Honey Bee](./53-honey-bee/technical_specification.md): DevOps Production Preparation 1
- (54) [Peacock Spider](./54-peacock-spider/technical_specification.md): Dataset Information Service
- (55) [Madagascan Sunset Moth](./55-madagascan-sunset-moth/technical_specification.md): Preliminary Storage Selection
- (56) [Sphynx Cat](./56-sphynx-cat/technical_specification.md): Kakfa Dead Letter Queues
- (57) [Monkfish](./57-monkfish/technical_specification.md): State Management Service
- (58) [Poodle Moth](./58-poodle-moth/technical_specification.md): Storing Data as strings vs BSON in MongoDB
- (59) [Bottlenose Dolphin](./59-bottlenose-dolphin/technical_specification.md): Angular implementation plan and migration strategy
- (60) [Hippopotamus](./60-hippopotamus/technical_specification.md): Create baseline for Angular implementation
- (61) [Matamata Turtle](./61-matamata-turtle/technical_specification.md): DLQ Service
- (62) [California Condor](./62-california-condor/technical_specification.md): DB Versioning
- (63) [Thorny Devil](./63-thorny-devil/technical_specification.md): Download Path Service Response Caching
- (64) [Blue Whale](./64-blue-whale/technical_specification.md): Reimplement frontend features in Angular
- (65) [Striped Skunk](./65-striped-skunk/technical_specification.md): Hexkit v4 Rollout
- (66) [Irukandji](./66-irukandji/technical_specification.md): Schemapack
- (67) [Oryx](./67-oryx/technical_specification.md): Kafka Event Config Standardization
- (68) [Gemsbok](./68-gemsbok/technical_specification.md): Persistent Kafka Publisher
- (69) [Common Kingslayer](./69-common-kingslayer/technical_specification.md): Distributed tracing with OpenTelemetry and Jaeger
- (70) [Common Furniture Beetle](./70-common-furniture-beetle/technical_specification.md): Metldata Transformation Finalzation
- (71) [Carpenter Bee](./71-carpenter-bee/technical_specification.md): Metldata Configurable Workflows
- (72) [Pygmy Goat](./72-pygmy-goat/technical_specification.md): Hexkit Documentation
- (73) [Ballan Wrasse](./73-ballan-wrasse/technical_specification.md): Access Request Management Improvements
- (77) [Alpine Longhorn Beetle](./77-alpine-longhorn-beetle/technical_specification.md): Make Metadata Downloadable
- (79) [Miniature Horse](./79-miniature-horse/technical_specification.md): Data Portal Accessibility, Responsiveness, and Semantics Overhaul and SOPs
