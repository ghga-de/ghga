---
paths:
  - "services/**/event_sub.py"
  - "services/**/event_pub.py"
  - "services/**/inject.py"
  - "services/**/prepare.py"
  - "services/*/chart-values.yaml"
  - "libs/ghga-event-schemas/src/ghga_event_schemas/configs/**"
  - "libs/metldata/chart-values.yaml"
  - "libs/metldata/src/metldata/**/*event*.py"
---

# Rules for the Kafka topology

The cascades map is read out of the code by a person into [kafka-cascades.yaml](../../docs/architecture/kafka-cascades.yaml), so code that moves an event edge leaves the map wrong until someone edits that file.

- **If the change moves an edge, edit `kafka-cascades.yaml` in the same change and run `just kafka-map`.**
  An edge moves when a topic or event type is added or dropped, a subscriber is added or removed, a publish mechanism changes between plain, outbox and persisted, or a subscriber does something different with an event. [kafka-cascade-map.md](../../docs/architecture/kafka-cascade-map.md) has the steps and says where each part of the topology is read from.
- **If no edge moves, leave the map alone.**
  A rename, a refactor inside a handler, a payload field, a config default, a test and a route that publishes nothing all leave the drawing correct.
