# Kafka cascades map

[kafka-cascade-map.html](kafka-cascade-map.html) draws every Kafka event cascade in GHGA as a tree per entrypoint: pick the call that publishes first, and the page unfolds which service reacts to which event, and what each one does.
It covers 23 topics and 22 entrypoints, and lists each topic with its producer and its subscribers.

The page is generated in part. [kafka-cascades.yaml](kafka-cascades.yaml) holds the topology; `just kafka-map` writes it into the page's marked data block, which no one edits by hand.
The page's stylesheet and its d3 drawing code are hand-written, and `just kafka-map` leaves them alone.

The topology is read out of the code by a person, so it drifts as the services change.
This page says where each part of it comes from, so the next reader can check it and correct it.

## Opening the page

Open the file in a browser; it is one self-contained page and needs no server.
VS Code has no HTML preview of its own, so from the dev container serve the directory instead and open the forwarded link:

```shell
python3 -m http.server 8000 --directory docs/architecture
```

Microsoft's Live Preview extension (`ms-vscode.live-server`) adds a "Show Preview" entry to the editor's context menu, which renders the page in a tab.
Either way the page needs network access: it loads d3 from cdnjs and its fonts from Google.

## Changing the map

1. Edit `kafka-cascades.yaml`.
   Its header comment describes every field; the `fragments` block holds the sub-cascades that several flows share.
2. Set `updated` to the day you checked the topology.
   The page's header counts and its date both come from the source, so neither can disagree with it.
3. Run `just kafka-map`.
   It validates the source, writes the data block and reports that it changed the page; stage the result.
4. Open the page and click through the flows you touched.

The validation rejects an unknown or missing field, an event class that is not `plain`, `outbox`, `persisted` or `http`, a duplicate flow id, a `use` of an unknown fragment or with the wrong argument, and a service name that either no node uses or no `services` entry defines.
The pre-commit hook runs the same script, so a stale page or an edit inside the markers fails the commit.

## Where the topology comes from

| Part of the map | Read from |
|---|---|
| Topics, event types, and which service produces or subscribes | `deploy/charts/<service>/values.yaml`, the `_topics` block: `topic.value` is the topic, `type.value` the event type, and `kafkaUser.operations` the ACL — `Write` for a producer, `Read` for a subscriber |
| The publish mechanism of each edge | the hexkit provider the service wires in its `inject.py`: `KafkaEventPublisher` is plain, `MongoKafkaDaoPublisherFactory` is outbox, `PersistentKafkaPublisher` is persisted |
| What a subscriber does with an event | `services/<service>/src/<pkg>/adapters/inbound/event_sub.py`, and the core method it calls |
| Which event a service publishes, and when | `services/<service>/src/<pkg>/adapters/outbound/event_pub.py`, or the outbox DAO the service registers in `inject.py` |
| The entrypoints | the HTTP route or CLI command that publishes first; the page's `target` field names it |
| The DLQ and retry edges | hexkit, `providers/akafka/provider/eventsub.py` — the behaviour is the same for every service, so the map draws it as one entrypoint rather than from every node |

The conventions behind the names are in [ADR-0010](../adrs/adr-0010-naming-mongo-and-kafka.md), and the DLQ design in [ADR-0009](../adrs/adr-0009-kafka-dead-letter-queues.md). [metadata-and-file-journeys.md](metadata-and-file-journeys.md) describes the same flows as prose, and is the better read for why a step exists.

## Checking it against the code

```shell
just kafka-map --topics
```

This prints every topic the charts declare, with the charts that write and read it, and then names the topics only one of the two sides has.
Read it, do not trust it: a chart may grant a service an ACL it never uses, and the map names the service that acts rather than every one entitled to.
A topic in the charts and not in the map is the signal worth chasing, since it is usually a cascade nobody has drawn yet.

For the flows themselves there is no such shortcut.
Take one entrypoint, follow it through the `event_sub.py` of each service it reaches, and compare it with the tree the page draws.

## What the map leaves out

The page's own "What this draws, and what it leaves out" section lists the exclusions and the reason for each: the routes that publish no event, the datasteward-kit commands that write only to a file-system event store or to S3, and the state-management-service, which can publish anything to any topic and is a test fixture ([ADR-0030](../adrs/adr-0030-state-management-service-testbed-only.md)).
Keep that section current when you change what the map covers; it is part of the hand-written markup, not of the generated block.
