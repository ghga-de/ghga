/**
 * Interface for the global metadata summary
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface GlobalSummary {
  Dataset: { count: number };
  ExperimentMethod: ExperimentMethodStats;
  Individual: IndividualStats;
  AnalysisMethodSupportingFile: FileStats;
  ExperimentMethodSupportingFile: FileStats;
  IndividualSupportingFile: FileStats;
  ProcessDataFile: FileStats;
  ResearchDataFile: FileStats;
}

interface ExperimentMethodStats {
  count: number;
  stats?: { instrument_model: ValueCount[] };
}

interface IndividualStats {
  count: number;
  stats?: { sex: ValueCount[] };
}

export interface FileStats {
  count: number;
  stats?: { format: ValueCount[] };
}

export interface ValueCount {
  value: string;
  count: number;
}

export interface BaseGlobalSummary {
  resource_stats: GlobalSummary;
}

export const emptyGlobalSummary: GlobalSummary = {
  Dataset: { count: 0 },
  ExperimentMethod: { count: 0 },
  Individual: { count: 0 },
  AnalysisMethodSupportingFile: { count: 0 },
  ExperimentMethodSupportingFile: { count: 0 },
  IndividualSupportingFile: { count: 0 },
  ProcessDataFile: { count: 0 },
  ResearchDataFile: { count: 0 },
};
