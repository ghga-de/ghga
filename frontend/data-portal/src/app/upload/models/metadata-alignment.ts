/**
 * Models and logic for aligning an upload box's files with an uploaded metadata file.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { MappedField } from './mapping';

/** A study as found in an uploaded metadata file (only the shown fields) */
export interface UploadedMetadataStudy {
  /** The study title */
  title: string;
  /** The study description */
  description: string;
}

/** A single file entry collected from an uploaded metadata file */
export interface UploadedMetadataFile {
  /** The file alias */
  alias: string;
  /** The file name */
  name: string;
}

/** The relevant parts extracted from a validated uploaded metadata file */
export interface UploadedMetadata {
  /** The first study in the metadata file */
  study: UploadedMetadataStudy;
  /** All files with `included_in_submission: true` across all `*_files` lists */
  files: UploadedMetadataFile[];
}

/** Result of parsing and validating an uploaded metadata file */
export type MetadataParseResult =
  { ok: true; metadata: UploadedMetadata } | { ok: false; error: string };

/** A box file as far as the alignment check is concerned */
interface AlignmentBoxFile {
  /** Unique identifier for the box file */
  id: string;
  /** The alias (filename) of the box file */
  alias: string;
}

/** The outcome of aligning box files against uploaded metadata files */
export interface MetadataAlignmentResult {
  /** The metadata field that aligned best (the one reported to the user) */
  field: MappedField;
  /** Number of matches when aligning by the file alias */
  aliasMatchCount: number;
  /** Number of matches when aligning by the file name */
  nameMatchCount: number;
  /** Number of matches for the chosen field */
  matchCount: number;
  /** Total number of metadata files */
  totalMetadata: number;
  /** Total number of box files */
  totalBoxFiles: number;
  /** Metadata files that did not match any box file (for the chosen field) */
  unmatchedMetadata: UploadedMetadataFile[];
  /** Box files that were not matched by any metadata file (for the chosen field) */
  unmatchedBoxFiles: AlignmentBoxFile[];
}

/**
 * Validate an entry from a `*_files` list and report problems.
 * @param entry - the raw entry to validate
 * @param key - the name of the list the entry belongs to (for messages)
 * @returns an error message, or `undefined` if the entry is valid
 */
function validateFileEntry(entry: unknown, key: string): string | undefined {
  if (typeof entry !== 'object' || entry === null) {
    return `Each entry in "${key}" must be an object.`;
  }
  const e = entry as Record<string, unknown>;
  if (
    typeof e['alias'] !== 'string' ||
    typeof e['name'] !== 'string' ||
    typeof e['included_in_submission'] !== 'boolean' ||
    !('dataset' in e)
  ) {
    return `Each entry in "${key}" must have a string "alias" and "name", a boolean "included_in_submission", and a "dataset".`;
  }
  return undefined;
}

/**
 * Parse and validate an uploaded metadata file. Validation is lenient: only the
 * properties that are needed are checked for existence, additional properties
 * are allowed. All files with `included_in_submission: true` are collected from
 * every property whose name ends in `_files`.
 * @param data - the parsed JSON value to validate
 * @returns the extracted metadata, or an error message describing the problem
 */
export function parseUploadedMetadata(data: unknown): MetadataParseResult {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    return { ok: false, error: 'The metadata must be a JSON object.' };
  }
  const obj = data as Record<string, unknown>;

  const studies = obj['studies'];
  if (!Array.isArray(studies) || studies.length === 0) {
    return {
      ok: false,
      error: 'The metadata must contain a non-empty "studies" list.',
    };
  }
  for (const study of studies) {
    if (
      typeof study !== 'object' ||
      study === null ||
      typeof (study as Record<string, unknown>)['title'] !== 'string' ||
      typeof (study as Record<string, unknown>)['description'] !== 'string'
    ) {
      return {
        ok: false,
        error: 'Each study must have a "title" and a "description".',
      };
    }
  }
  const firstStudy = studies[0] as Record<string, unknown>;

  const files: UploadedMetadataFile[] = [];
  for (const [key, value] of Object.entries(obj)) {
    if (!key.endsWith('_files')) continue;
    if (!Array.isArray(value)) {
      return { ok: false, error: `The "${key}" property must be a list.` };
    }
    for (const entry of value) {
      const error = validateFileEntry(entry, key);
      if (error) return { ok: false, error };
      const e = entry as Record<string, unknown>;
      if (e['included_in_submission'] === true) {
        files.push({ alias: e['alias'] as string, name: e['name'] as string });
      }
    }
  }

  return {
    ok: true,
    metadata: {
      study: {
        title: firstStudy['title'] as string,
        description: firstStudy['description'] as string,
      },
      files,
    },
  };
}

/**
 * Match metadata files against box files using a single field.
 *
 * This mirrors the matching rule used by the study-based mapping
 * (`computeAutoMappings` in `upload-box-mapping.ts`): a case-sensitive exact
 * match takes priority, otherwise the single case-insensitive match is used if
 * exactly one exists. Box files are never reused. Keep both in sync.
 * @param metaFiles - the metadata files to match
 * @param boxFiles - the box files to match against
 * @param field - which metadata field to compare against the box file alias
 * @returns a map from metadata file index to matched box file id
 */
function matchByField(
  metaFiles: UploadedMetadataFile[],
  boxFiles: AlignmentBoxFile[],
  field: MappedField,
): Map<number, string> {
  const result = new Map<number, string>();
  const usedBoxIds = new Set<string>();

  metaFiles.forEach((meta, index) => {
    const metaValue = meta[field];
    if (!metaValue) return;

    // Case-sensitive exact match
    const exact = boxFiles.find(
      (bf) => bf.alias === metaValue && !usedBoxIds.has(bf.id),
    );
    if (exact) {
      result.set(index, exact.id);
      usedBoxIds.add(exact.id);
      return;
    }

    // Case-insensitive single match
    const lower = metaValue.toLowerCase();
    const caseMatches = boxFiles.filter(
      (bf) => bf.alias.toLowerCase() === lower && !usedBoxIds.has(bf.id),
    );
    if (caseMatches.length === 1) {
      result.set(index, caseMatches[0].id);
      usedBoxIds.add(caseMatches[0].id);
    }
  });

  return result;
}

/**
 * Align box files against uploaded metadata files, trying both the alias and
 * the name field and reporting on whichever yields more matches (a tie is
 * resolved in favor of the alias).
 * @param metaFiles - the metadata files to align
 * @param boxFiles - the box files to align against
 * @returns the alignment result for the better field
 */
export function computeMetadataAlignment(
  metaFiles: UploadedMetadataFile[],
  boxFiles: AlignmentBoxFile[],
): MetadataAlignmentResult {
  const aliasMatches = matchByField(metaFiles, boxFiles, 'alias');
  const nameMatches = matchByField(metaFiles, boxFiles, 'name');

  // Prefer the field with more matches; a tie favors the alias.
  const field: MappedField = nameMatches.size > aliasMatches.size ? 'name' : 'alias';
  const matches = field === 'name' ? nameMatches : aliasMatches;
  const matchedBoxIds = new Set(matches.values());

  return {
    field,
    aliasMatchCount: aliasMatches.size,
    nameMatchCount: nameMatches.size,
    matchCount: matches.size,
    totalMetadata: metaFiles.length,
    totalBoxFiles: boxFiles.length,
    unmatchedMetadata: metaFiles.filter((_, index) => !matches.has(index)),
    unmatchedBoxFiles: boxFiles.filter((bf) => !matchedBoxIds.has(bf.id)),
  };
}
