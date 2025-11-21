/**
 * Interface for the search results
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface SearchResults {
  facets: Facet[];
  count: number;
  hits: Hit[];
}

export interface Facet {
  key: string;
  name: string;
  options: FacetOption[];
}

interface FacetOption {
  value: string;
  count: number;
}

export interface Hit {
  id_: string;
  content: HitContent;
}

interface HitContent {
  ega_accession?: string;
  title: string;
}

export const emptySearchResults: SearchResults = {
  facets: [],
  count: 0,
  hits: [],
};
