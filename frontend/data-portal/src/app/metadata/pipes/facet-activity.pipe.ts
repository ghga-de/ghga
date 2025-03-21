/**
 * This pipe takes the overall state of all facets that are offered as filters in the ui and checks if the provided facet is set or not
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { FacetFilterSetting } from '../models/facet-filter';

/**
 * This pipe can be used to check if the current facet filter list contains a specific filter..
 */
@Pipe({
  name: 'facetActivity',
})
export class FacetActivityPipe implements PipeTransform {
  /**
   * The transform method checks if the facetInQuestion is selected or not in the current facet state.
   * @param facetInQuestion the facet we want to check for being selected or not
   * @param currentFacetStates the state of all facets in the current ui
   * @returns the year as a string
   */
  transform(facetInQuestion: string, currentFacetStates: FacetFilterSetting): boolean {
    const facetDetails = facetInQuestion.split('#');
    if (facetDetails.length != 2) {
      return false;
    }
    const facetName = facetDetails[0];
    const facetOption = facetDetails[1];

    if (currentFacetStates[facetName] && currentFacetStates[facetName].length > 0) {
      return currentFacetStates[facetName].indexOf(facetOption) != -1;
    }
    return false;
  }
}
