---
paths:
  - "services/**/event_sub.py"
  - "services/**/event_pub.py"
  - "services/**/inject.py"
  - "services/**/prepare.py"
  - "services/*/chart-values.yaml"
  # The four files that pass `dto_to_event`, which is what declares an outbox edge.
  # Named one by one: `services/**/dao.py` matches a DAO module in most services, and a
  # rule that fires on ordinary persistence work is a rule agents learn to skip.
  - "services/ghga-registry-service/src/rs/adapters/outbound/dao.py"
  - "services/ucs/src/ucs/adapters/outbound/dao.py"
  - "services/access-request-service/src/ars/adapters/outbound/daos.py"
  - "services/auth-service/src/auth_service/user_registry/translators/dao.py"
  - "libs/ghga-event-schemas/src/ghga_event_schemas/configs/**"
  - "libs/metldata/chart-values.yaml"
  - "libs/metldata/src/metldata/**/*event*.py"
---

# Rules for the Kafka topology

The cascades map is read out of the code by a person into [kafka-cascades.yaml](../../docs/architecture/kafka-cascades.yaml), so code that moves an event edge leaves the map wrong until someone edits that file.

- **If the change moves an edge, edit `kafka-cascades.yaml` in the same change and run `just kafka-map`.**
  An edge moves when a topic or event type is added, renamed or dropped, a subscriber is added or removed, a publish mechanism changes between plain, outbox and persisted, or a subscriber acts differently on an event.
  A `dto_to_event` that starts or stops returning `None` moves an edge too: the map draws that suppression.
  [AC-0009](../../docs/architecture/ac-0009-kafka-cascade-map.md) has the steps and says where each part of the topology is read from.
- **If no edge moves, leave the map alone.**
  Renaming anything but a topic or an event type, refactoring inside a handler, a payload field, a config default that is not a topic or type name, a test, and a route that publishes nothing all leave the drawing correct.
