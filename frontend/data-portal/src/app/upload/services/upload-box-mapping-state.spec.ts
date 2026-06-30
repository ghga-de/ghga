/**
 * Tests for the upload box mapping state service.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  MappingSnapshot,
  UploadBoxMappingStateService,
} from './upload-box-mapping-state';

describe('UploadBoxMappingStateService', () => {
  let service: UploadBoxMappingStateService;

  beforeEach(() => {
    service = new UploadBoxMappingStateService();
  });

  it('should return undefined for boxes without a saved snapshot', () => {
    expect(service.snapshotFor('missing-box')).toBeUndefined();
  });

  it('should save and return a snapshot for the requested box id', () => {
    const snapshot: MappingSnapshot = {
      studyAccession: 'STUDY-001',
      mappedField: 'alias',
      manualMappings: [['meta-1', 'file-1']],
    };

    service.saveSnapshot('box-1', snapshot);

    expect(service.snapshotFor('box-1')).toEqual(snapshot);
  });

  it('should keep snapshots isolated per upload box id', () => {
    const firstSnapshot: MappingSnapshot = {
      studyAccession: 'STUDY-001',
      mappedField: 'alias',
      manualMappings: [['meta-1', 'file-1']],
    };
    const secondSnapshot: MappingSnapshot = {
      studyAccession: 'STUDY-002',
      mappedField: 'name',
      manualMappings: [['meta-2', null]],
    };

    service.saveSnapshot('box-1', firstSnapshot);
    service.saveSnapshot('box-2', secondSnapshot);

    expect(service.snapshotFor('box-1')).toEqual(firstSnapshot);
    expect(service.snapshotFor('box-2')).toEqual(secondSnapshot);
  });

  it('should clear only the requested box snapshot', () => {
    service.saveSnapshot('box-1', {
      studyAccession: 'STUDY-001',
      mappedField: 'alias',
      manualMappings: [['meta-1', 'file-1']],
    });
    service.saveSnapshot('box-2', {
      studyAccession: 'STUDY-002',
      mappedField: 'name',
      manualMappings: [['meta-2', 'file-2']],
    });

    service.clearSnapshot('box-1');

    expect(service.snapshotFor('box-1')).toBeUndefined();
    expect(service.snapshotFor('box-2')).toEqual({
      studyAccession: 'STUDY-002',
      mappedField: 'name',
      manualMappings: [['meta-2', 'file-2']],
    });
  });
});
