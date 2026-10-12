# Kafka cascades map

[kafka-cascade-map.html](kafka-cascade-map.html) draws every Kafka event cascade in GHGA as a tree per entrypoint: pick the call that publishes first, and the page unfolds which service reacts to which event, and what each one does.
It also lists every topic with its producer and its subscribers; the page's own header carries the counts, which come from the source.

The page is generated in part. [kafka-cascades.yaml](kafka-cascades.yaml) holds the topology; `just kafka-map` writes it into the page's marked data block, which no one edits by hand.
The page's stylesheet and its d3 drawing code are hand-written, and `just kafka-map` leaves them alone.

The topology is read out of the code by a person, so it drifts as the services change.
This page says where each part of it comes from, so the next reader can check it and correct it.

## Opening the page

Open the file in a real browser; it is one self-contained page and needs no server.
From the dev container, serve the directory:

```shell
python3 -m http.server 8000 --directory docs/architecture
```

Then open `http://localhost:8000/kafka-cascade-map.html` in VS Code's integrated browser or in your own; VS Code forwards the port.
The integrated browser runs on the host, so it refuses the container's `file://` path as outside a trusted folder.
Microsoft's Live Preview extension (`ms-vscode.live-server`) shows a blank page in its embedded tab; its "open in external browser" action works.
Either way the page needs network access: it loads d3 from cdnjs and its fonts from Google.
When d3 cannot be fetched the page says so where the diagram would be, and still draws its header, legend and topic table; the fonts need no such guard, since they fall back to the stack beside them.
No formatter or linter covers it: prettier is scoped to `frontend/data-portal`, so `just fmt` leaves `docs/**/*.html` alone.

## Changing the map

1. Edit `kafka-cascades.yaml`.
   Its header comment describes every field; the `fragments` block holds the sub-cascades that several flows share.
2. Set `updated` to the day you checked the topology.
   The page's header counts and its date both come from the source, so neither can disagree with it.
3. Run `just kafka-map`.
   It validates the source, writes the data block and reports that it changed the page; stage the result.
4. Open the page and click through the flows you touched.

The validation rejects an unknown or missing field, an event class that is not `plain`, `outbox`, `persisted` or `http`, a duplicate flow id, a `use` of an unknown fragment or with the wrong argument, and a name that no node uses, or that no `services` or `labels` entry defines.
It also cross-checks the two halves of the source: every topic an edge names has a row in the table and every row is named by some edge, the two agree on the topic's class, and no topic is listed twice.
A topic in angle brackets, such as the replay flow's `<that service's topics>`, stands for a set and is matched against no row.
The pre-commit hook runs the same script, so a stale page or an edit inside the markers fails the commit.

## Where the topology comes from

| Part of the map | Read from |
|---|---|
| Topics, event types, and which service produces or subscribes | the `_topics` block: `topic.value` is the topic, `type.value` the event type, and `kafkaUser.operations` the ACL — `Write` for a producer, `Read` for a subscriber. Read it from the generated `deploy/charts/<service>/values.yaml`; edit it in the member's own `chart-values.yaml`, then run `just charts` |
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
Two differences it reports today are chart bugs rather than map bugs, and are left for a `deploy/` change: `dins` is granted `Write` on `metadata-datasets` though it has no event publisher, and `ns` declares `notifications` with no `kafkaUser` block though it subscribes.

For the flows themselves there is no such shortcut.
Take one entrypoint, follow it through the `event_sub.py` of each service it reaches, and compare it with the tree the page draws.

## What the map leaves out

The page's own "What this draws, and what it leaves out" section lists the exclusions and the reason for each: the routes that publish no event, the datasteward-kit commands that write only to a file-system event store or to S3, and the state-management-service, which can publish anything to any topic and is a test fixture ([ADR-0030](../adrs/adr-0030-state-management-service-testbed-only.md)).
Keep that section current when you change what the map covers; it is part of the hand-written markup, not of the generated block.
