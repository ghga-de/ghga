# DevOps Production Preparation 1 (Honey Bee)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope
### Outline:

The goal of this epic is to improve the documentation of concepts and procedures in preparation for the product launch.

#### Concepts

The following operational concepts shall be documented:

1. Internal Transport Encryption Concept

   Explains the general framework and technologies used in the context of transport encryption between internal components. Enumerates all pairs of components (or component types) and documents if and if so how the traffic inbetween is encrypted (e.g. service-service, service-kafka, service-mongodb, ingress-service, kafka-kafka, etc.)

1. Vault Configuration and Operation Concept

   Explains how we operate the production Vault instance. Clarifies responsibility boundaries between units ODCF and GHGA.

1. Kubernetes Configuration and Operation Concept

   Key aspects of our Kubernetes setup, clarification of responsibility boundaries between units ODCF and GHGA, authentication and authorization concept.

#### Standard Operating Procedures

The following SOPs shall be documented:

1. Foundational Setup

   Step-by-step instructions starting from an empty OpenStack project with sufficient resources and access to the ODCF / deNBI Cloud Kubermatic System:

   * Installation of Kubernetes
   * Configuration of Kubernetes (authentication according to concept)
   * Installation of foundational services

1. Secure Personal Handling of Secrets

   Instructions for GHGA staff how to handle secrets that they are holding based on their role in GHGA (storage only on institutional devices, password manager instructions (choise of software, configuration, cloud yes / no / which), what to do when a secret is lost / leaked, etc.)

#### Secrets Registry

In addition, a secrets registry shall be designed and integrated into the internal documentation, clarifying key aspects for every secrets that is being generated in the aforementioned processes. Information may include:

- ID
- Decription
- Component
- Security Class
- Holder(s)
- Recovery from Loss
- Recovery from Leak

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
