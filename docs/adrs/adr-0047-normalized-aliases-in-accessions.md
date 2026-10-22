---
status: proposed
date: 2026-10-20
tags: [data, backend]
---

# ADR-0047 — Normalized aliases in accessions

## Summary

In the context of **accessions `{study_pid}.{alias}` built from a steward's alias**

facing **free-text aliases with dots, spaces and slashes**

we decided for **one fixed normalization of the alias, refusing blank, non-ASCII and colliding aliases before minting**

and neglected **the raw alias, escaping, a stricter alias syntax and a random block**

to achieve **readable accessions that services can check by pattern**

accepting that **aliases differing only in case or punctuation must be renamed, and that the rule never changes**.

## Details

### Context

The [giraffe epic](../epics/epic-0093-giraffe.md) gives a study the PID `GHGA.YY.XXX.V`, a dataset `{study_pid}.DS.xxx`, and every other entity `{study_pid}.{alias}`.
The alias comes from the steward's spreadsheet and is free text.
Taken as it is, `reads.bam` would add a further dot-separated block, so its accession reads like a dataset PID, and a space or `/` breaks URLs and file names.
WPS, ARS and auth-service validate accessions by pattern, with the types in `ghga_service_commons.utils.accessions`, so the form has to be fixed.
Once minted, an accession is permanent.

### Decision

The alias block of an accession is the alias normalized by `normalize_alias` in metldata's `metadata_utils.py`: stripped, lowercased, and with every character other than `a-z`, `0-9`, `_` and `-` replaced by `-`.
The metadata and the accession map keep the alias as submitted.

Before anything is minted, metldata refuses:

- an alias that is empty or whitespace only, in `MetadataValidator.validate`;
- an alias that is not ASCII, since normalizing would hide its characters;
- two aliases of a submission that are equal once normalized, across all classes;
- a new alias whose accession a dropped alias held, so that an accession never passes to another entity.

The rule is fixed: changing it would give an alias already accessioned a different accession in a later revision.
`FileAccession` in commons accepts exactly this alias block, and changes only together with the rule.

### Consequences

- An alias accession has one lowercase block after the study PID and a dataset PID has two, the fixed `DS` and a random block, so a pattern tells them apart.
- Accessions need no escaping in URLs, file names or object storage keys.
- Aliases such as `Sample 1` and `sample-1` collide, and the steward renames one.
- A rename that changes only case or punctuation is refused once the old alias holds an accession; the steward keeps the old spelling.
- The rule lives in metldata and its pattern in commons, so a reviewer of either checks the other.

### Alternatives

- **The raw alias.**
  Rejected: dots make the blocks ambiguous, and other characters are unsafe in URLs and file names.
- **An escaped alias**, such as percent-encoding.
  Rejected: the accession becomes unreadable, and the encoding still has to be fixed forever.
- **A stricter alias syntax** enforced at submission.
  Rejected: stewards would rewrite existing spreadsheets for a constraint only the accession needs.
- **A random block in place of the alias**, as for datasets.
  Rejected: the accession no longer follows from the alias, so a revision cannot derive it again and has to look it up.
