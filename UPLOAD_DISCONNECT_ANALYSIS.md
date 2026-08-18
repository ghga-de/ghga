# "Server disconnected without sending a response" during uploads

## Cause

`httpcore2` rewrote the pool (`httpcore2/_async/connection_pool.py:254-360`). It now
computes `available_connections` once per pass from a snapshot, and **skips
`has_expired()` for "reserved" connections** (already assigned to a request). Old
`httpcore` re-probed every idle socket on every pass, so a server FIN was caught and the
connection evicted before use.

Result: a connection that dies **after assignment, before the request is written** is
never re-checked → request goes out on a dead socket → `RemoteProtocolError`.

Measured, identical server (reaps idle keep-alives) and limits:

```
httpx 0.x :  5/30 failures
httpx2    : 15/30 failures   <-- 3x
```

The connector maximizes the window: `_upload_file_part` calls `next(file_processor)`,
and `process_file` (`core/crypt/encryption.py:103`) is a **synchronous** generator —
64 MiB read + crypt4gh encrypt + checksums. Freezes the event loop for seconds while
pooled connections sit assigned and the server reaps them.

## Why retries don't hide it

1. **`client_num_retries` is attempts, not retries** (`transports/retry.py:46`,
   `stop_after_attempt`). Measured: `1` → 0 retries, `2` → 1 retry.
   `tools/ghga-connector/example_config.yaml:2` ships `2`. Field description is wrong.
2. **Every `except RetryError` in `uploading/api_calls.py` is dead code.**
   `client_reraise_from_retry_error=True` re-raises the original
   `httpx2.RemoteProtocolError`, never `RetryError`. So `_check_for_request_errors`
   never runs and the raw httpcore string reaches the user — the exact reported message.

Aggravating: `core/client.py:50-51` sizes the pool from `max_concurrent_downloads` even
when uploading, and one 5-connection pool is shared by WPS + Upload API + S3.

## Fixes, best first

1. Run encryption off the event loop — `asyncio.to_thread` around `next(file_processor)`.
2. Fix retry counting: bump connector config to ~5, correct/rename the field.
3. Fix the dead `except RetryError` — also catch `httpx2.RequestError`.
4. Lower `keepalive_expiry` (~2s) in the `httpx2.Limits`.
5. Size the pool from `max_concurrent_uploads` on the upload path; account for 3 origins.

## Caveat

Retries masked every stale connection on loopback; exhaustion was not reproduced there.
Items 1 explains the frequency increase (confirmed); 2 and 3 explain why it reaches the
user (confirmed).
