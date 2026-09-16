# UCS Upload Permission Guardrails (Pistol Shrimp)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
The Upload Controller Service (UCS) currently has verification and auth mechanisms at the start and end of the upload lifecycle through Work Order Tokens (WOTs) and checksum verification, but the window between those two points needs more control. For example, with the current implementation, a caller with a valid WOT can declare any number of arbitrarily large files, abandon multipart uploads indefinitely, and spam the presigned URL endpoint. This epic addresses those problems by adding a layered set of guardrails to UCS and supporting infrastructure.


### Included/Required:
- **Upload Box size limits:** Data stewards will specify a maximum size in bytes when creating a new Research Data Upload Box. The box size will determine how many bytes may be uploaded across all files in their *unencrypted* state in the box. Because submitters must declare their total data size during contract negotiation with data stewards, a per-box aggregate cap is always enforceable — this is domain knowledge not currently codified anywhere in the backend. When a submitter requests to create a new FileUpload, look at in-progress (`state="init"`) uploads for the FileUploadBox and reject the request if the assigned box limit would be exceeded. When considering file sizes, it is the `decrypted_size` that counts, rather than the `encrypted_size`.
- **Concurrent uploads cap per box:** Similar to the box limit, this would count the number of in-progress uploads and reject any requests to create new FileUploads if a configured limit would be crossed. Note that while box size limits are specific to the box, the concurrent uploads per box cap applies uniformly to all boxes. This concurrent upload cap would prevent the style of abuse where thousands of uploads are opened simultaneously, but it does not prevent the scenario where many very small uploads are created and completed in rapid succession. Note that as it's currently implemented, the GHGA Connector only uploads files in sequence anyway, meaning this limit won't be hit unless the Connector is modified.
- **Stale upload TTL with automated abort:** Track activity for each upload via a KV store entry (key = `file_id`, value = timestamp of last activity), set on `FileUpload` creation and refreshed on every presigned URL issuance. This can be performed as a [FastAPI BackgroundTask](https://fastapi.tiangolo.com/reference/background/) so the response isn't blocked. Implement a periodic cleanup job that aborts S3 multipart uploads and marks `FileUpload` records as `cancelled` for those whose KV store entry has expired. Make this functionality accessible through a new entrypoint command. In case of confusion, the reason for this TTL check is to catch orphaned or abandoned multipart uploads and abort them. There is a TTL or expiry parameter assigned to the presigned upload URLs, but the URL lifespan should be considered shorter than the multipart upload lifespan. After all, a new URL has to be issued for each file part. Therefore, we can't use the URL TTL as a reference for this kind of cleanup operation.

### Optional:
- **Rate limiting on presigned URL issuance:** Apply a per-file-upload token bucket to the `GET .../parts/{part_no}` endpoint to cap the rate at which the user can request presigned URLs for a given multipart upload (which is 1:1 with `FileUpload`). The token bucket can be held in-memory or backed by `hexkit`'s KV store / MongoDB provider.
- **Verify part sizes retrospectively:** Call the S3 list_parts function for the previous part (`n-1`) when a URL is requested. If the part size exceeds the expected part size by some allowable buffer, UCS aborts the upload immediately. UCS then responds to the HTTP request with an error indicating the upload has been aborted (`state="cancelled"`). The GHGA Connector won't make subsequent requests and will display an appropriate message to the user.
  - This requires a modification to hexkit and adds up to one call for every presigned URL request. This would address the scenario where presigned URLs are used to upload large data quantities for every part, in excess of the actual data amount. Without this, the fallback is to reject the upload at completion time or clean up the stagnant multipart upload if the user intentionally abandons it.

### Not included:
- **Frontend or Data Portal changes.**

## User Journeys

No new user-facing flows are introduced. All changes should be transparent to submitters using the official version of the GHGA Connector. Requests that violate the new limits receive explicit error responses with descriptive messages.

## API Definitions:

### RESTful/Synchronous:

No new endpoints will be added. The following existing endpoints will gain new validation behavior and may return new error responses:

**`POST /boxes/{box_id}/uploads`** -> Initiate a multipart upload for a new `FileUpload`:
- Will return `400 Bad Request` (`PartCountLimitExceededError`) if the computed part count exceeds the S3 hard limit of 10,000 parts.
- Will return `507 Insufficient Storage` (`BoxSizeLimitExceededError`) if adding this file's `decrypted_size` to the aggregate `decrypted_size` of all in-progress (`state="init"`) uploads for the box would exceed the box's assigned cap.
- Will return `429 Too Many Requests` (`TooManyConcurrentUploadsError`) if the number of in-progress uploads for the box is already at the configured limit.

**`GET /boxes/{box_id}/uploads/{file_id}/parts/{part_no}`** -> Get a presigned URL for a part:
- Will update the FileUpload's last-activity timestamp on every successful response
- *(optional)* Will return `429 Too Many Requests` (`PartUrlRateLimitError`) if the per-file token bucket is exhausted. In this case, the `retry-after` header should be used.
- *(optional)* Will call `S3ClientPort.list_parts()` for part `n-1` when `part_no > 1`; if the previous part's size exceeds the expected part size, will abort the multipart upload, mark the `FileUpload` as `cancelled`, and return an upload-cancelled error to the caller

### Payload Schemas for Events:

The library version of `FileUploadBox` and `ResearchDataUploadBox` in `ghga-event-schemas` must be updated with the new `max_total_bytes` field. Otherwise, no new event schemas will be required and no changes to the library version of the `FileUpload` model will be needed. Upload activity will be tracked in the KV store (see below), not in the outbox-published document.

### Configuration:

The following new config fields will be added to UCS config. All will have safe defaults:

```python
# Concurrent `FileUpload` cap
max_concurrent_uploads_per_box: int = 5        # This is a global limit for all boxes

# Stale multipart upload TTL
multipart_upload_ttl_hours: int = 72             # Multipart uploads idle beyond this are aborted
cleanup_interval_minutes: int = 60             # How often the cleanup job runs

# Presigned URL rate limiting (optional)
part_url_refill_interval_ms: int = 0           # 0 = no rate limiting
max_url_buildup: int = 10                      # Token bucket initial/max tokens
```

## Additional Implementation Details:

### UCS and RS — New upload validation

In `UploadController.initiate_file_upload()` (`core/controller.py`), after the box is validated and before `S3ClientPort.init_multipart_upload()` is called, the following checks will be added:

1. **Part count cap:** Will raise `PartCountLimitExceededError` if part count exceeds 10,000.
2. **Box aggregate size cap:** Will sum `decrypted_size` across all `state="init"` FileUploads for the box (a single `find_all` query, analogous to `_update_box_stats()`). If the sum plus the new file's `decrypted_size` would exceed `box.max_total_bytes`, will raise `BoxSizeLimitExceededError`.
3. **Concurrent upload cap:** Will count the `state="init"` FileUploads already fetched for the box aggregate check. If the count is already at `config.max_concurrent_uploads_per_box` (when > 0), will raise `TooManyConcurrentUploadsError`.

The following new error classes will be defined on `UploadControllerPort`:
- `PartCountLimitExceededError`: maps to 400 in HTTP error translation layer
- `BoxSizeLimitExceededError`: maps to 507 in HTTP error translation layer
- `TooManyConcurrentUploadsError`: maps to 429 in HTTP error translation layer

#### Work to be performed:
- [ ] Add `max_total_bytes` to `FileUploadBox` and `ResearchDataUploadBox` schemas in `ghga-event-schemas`.
- [ ] Update RS with the new schema and modify tests/ensure new field is passed to UCS
- [ ] Add `max_concurrent_uploads_per_box` to `Config`
- [ ] Add new error definitions to `UploadControllerPort`
- [ ] Add validation logic in `UploadController.initiate_file_upload()`
- [ ] Map new errors to HTTP responses in the FastAPI adapter
- [ ] Add tests covering:
  - Part count and box size: values within limits (no error), values at exactly the limit (no error), values one byte/one part over the limit (error raised), box aggregate cap exceeded (error raised)
  - Concurrent cap: at-limit rejection, below-limit success, limit set to 0 (disabled)

---

### UCS — Stale Upload TTL and cleanup job

#### Upload activity tracking

Upload activity for each `FileUpload` will be tracked in a separate collection which almost acts as a KV store so we don't issue a new `FileUpload` outbox event with unchanged data every time UCS issues a presigned URL. Right now, there is no KV Store provider in hexkit that accepts datetime values as-is, and there is no KV Store protocol method which would allow us to fetch all entries older than a certain date, so one will be implemented in the UCS using a normal DAO. The "store" will use the UUID4 file IDs as keys and UTC datetimes representing the last UCS-based activity of the `FileUpload` as values. Entries will be created when `UploadController.initiate_file_upload()` creates the `FileUpload` record, and updated each time a presigned URL is successfully issued via `UploadController.get_part_upload_url()`. Entries will be deleted when the `FileUpload.state` is set to `inbox`.

During upload creation (i.e. the initialization step), no activity timestamp should exist yet. However, if one does, UCS will log a warning but overwrite the existing value. Since UUID4s have a negligible collision probability, this is most likely to crop up during testing. This scenario should not cause the service to crash because the timestamp only represents the time of the last UCS activity concerning the upload, which isn't critical information *per se*. If this happened in production, reasons to crash the service would occur somewhere else in the chain of execution.

During URL issuance, activity timestamps should exist for each request. In the case that the timestamp unexpectedly does not exist, UCS will log a warning and create it. This same stance is also taken when trying to delete the timestamp upon upload completion.

#### Cleanup job

A new entrypoint function `run_cleanup_job()` will be added to `main.py` (alongside the existing `run_rest_api()` and `run_event_consumer()` entrypoints). This function will run a loop that:
1. Sleeps for `config.cleanup_interval_minutes` minutes.
2. Calls `UploadController.cleanup_stale_uploads()`.
3. Repeats.

_Alternatively, this can be run as a one-off job scheduled as a cron job._

For each configured `inbox` bucket (i.e. each data hub), do the following:
- Fetch all `state="init"` FileUploads from the DB.
- Build a list of upload IDs for FileUploads whose last activity timestamp is older than the configured cutoff.
- Extend the list with any uploads where an activity timestamp is missing but `FileUpload.initiated` is older than the configured cutoff (no parts complete, presumed stale).
- Get all ongoing uploads from the bucket.
- Extend the list with any upload IDs that don't correspond to any `FileUpload.object_id` from the first DB fetch.
- Abort all the uploads in the list.

#### Work to be performed:
- [ ] Add `multipart_upload_ttl_hours` and `cleanup_interval_minutes` to `Config`
- [ ] Update `UploadController.initiate_file_upload()` to write the activity entry on `FileUpload` creation
- [ ] Update `UploadController.get_part_upload_url()` to refresh the activity entry on each call
- [ ] Add `cleanup_stale_uploads()` to `UploadControllerPort` and `UploadController`
- [ ] Add `run_cleanup_job()` entrypoint to `main.py`

---

### UCS — Rate limiting on presigned URL issuance (Optional)

If implemented, a per-file-upload token bucket will be applied in `UploadController.get_part_upload_url()` before the S3 presign call. Each bucket will start at `config.max_url_buildup` tokens. Once the count falls below maximum it will be incremented once every `config.part_url_refill_interval_ms` milliseconds until it reaches the maximum again. On each URL request, one token will be consumed; if the bucket is empty, `PartUrlRateLimitError` will be raised. If `config.part_url_refill_interval_ms == 0`, the feature will be disabled entirely, letting URLs be requested as fast as infra allows.

A new error class will be defined: `PartUrlRateLimitError`, translated in the HTTP response as `429 Too Many Requests` with the `retry-after` set to `config.part_url_refill_interval_ms` * 1000.

`hexkit`'s `KeyValueStoreProtocol` (with the MongoDB provider) will be used to persist token bucket state keyed by `file_id`. `KeyValueStoreProtocol` will already be a required UCS dependency (added for the stale upload TTL feature), so no additional wiring will be needed. Token bucket state will survive restarts and will be correctly shared across all UCS replicas.

#### Work to be performed (optional):
- [ ] Add `part_url_refill_interval_ms` and `max_url_buildup` to `Config`
- [ ] Add `PartUrlRateLimitError` to `UploadControllerPort`
- [ ] Implement token bucket logic in `KeyValueStoreProtocol` with per-`file_id` keying
- [ ] Apply the rate limit check in `get_part_upload_url()`; evict/expire stale bucket entries for terminal-state uploads
- [ ] Map to HTTP 429 in the FastAPI adapter
- [ ] Add tests for: below-limit success, burst allowance, sustained rate enforcement, limit disabled when config is 0

---

### UCS — Verify part sizes retrospectively (Optional)

> **Prerequisite:** This feature requires `hexkit`'s `ObjectStorageProtocol` to expose a `list_parts()` method.

One weakness of enabling S3 multipart uploads through the use of presigned URLs is that there's not a lot of support for preventing abuse of those URLs. The chief concern is that a user uploads too much data for each part than expected or agreed upon. S3's presigned POST feature lets the server specify headers like `Content-Length-Range` among other things, which would perfectly solve this problem *except* that multipart uploads [only work with presigned PUTs](https://advancedweb.hu/differences-between-put-and-post-s3-signed-urls/), which don't grant the option to specify any such headers. This problem of URL abuse can be addressed in one of two ways: do nothing - rely on periodic cleanup of stale multipart uploads and accept that a user could upload the max amount of data allowed by S3 and let it sit there temporarily; examine uploaded parts throughout the upload process and shut it down if abuse is detected. Another option might be to try to hack together a solution that forces presigned URLs with content length headers, but I'm not sure that this is possible.

If opted for, a retrospective size check will be added in `UploadController.get_part_upload_url()` before the S3 presign call. When `part_no > 1`, `S3ClientPort.list_parts()` will be called to retrieve the metadata for part `n-1`. If the returned part size exceeds `FileUpload.part_size`, the multipart upload will be immediately aborted via `S3ClientPort.abort_multipart_upload()`, the `FileUpload` will be marked `cancelled`, and an upload-cancelled error will be raised with the user receiving a 400 Bad Request status code. Subsequent requests for this upload will also fail with the cancelled-state error via the normal state check.

This will add at most one additional S3 API call per presigned URL request (skipped for the first part). The fallback of detecting the oversize at completion time is already implemented, but would leave uploaded parts from abandoned uploads in S3 until the cleanup job runs.

#### Work to be performed if implemented:
- [ ] Add `list_parts()` to `hexkit`'s `ObjectStorageProtocol` and S3 provider, and then use it in the UCS's `S3ClientPort`
- [ ] Implement retrospective size check in `UploadController.get_part_upload_url()` for `part_no > 1`
- [ ] Abort multipart upload and mark `FileUpload` as `cancelled` on oversized part detection
- [ ] Add tests for:
  - part within expected size (no abort)
  - part exceeding expected size (abort + cancel + error returned)
  - first-part request (no list_parts call)
  - tolerance for transient `list_parts` failure


## Human Resource/Time Estimation:

Number of sprints required: 1-2

Number of developers required: 1
