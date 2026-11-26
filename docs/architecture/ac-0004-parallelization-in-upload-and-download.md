---
status: current
date: 2024-01-19
amended: 2024-01-22
tags: [backend]
related: [AC-0001]
---

# AC-0004 — Parallelization in upload and download

## Introduction

Parallel downloading and uploading are common techniques used to speed up file transfers over the internet.
When transferring large files, downloading or uploading the file in its entirety can be time-consuming and inefficient.
To improve the transfer speed, the file can be split into smaller parts, which can be downloaded or uploaded in parallel.
By using multiple connections, it's possible to fully utilize the available network bandwidth and significantly reduce the time required to transfer the file.

However, parallel downloading and uploading can be challenging to implement correctly, especially when working with large files.
Some of the challenges include:

- Ensuring that all parts of the file are downloaded or uploaded correctly and that there are no missing or corrupted parts.
- Coordinating the parallel downloads or uploads to avoid conflicts or race conditions.
- Handling errors and retries in case of network or server issues.

Our S3 Implementations do not care in which order file parts are uploaded.
The only thing we need to take care of is sending the file part with the correct signed URL we got from the UCS.
For the download, this is even easier, as the DCS only sends pre-signed URLs, while the Connector decides which part to download through the use of range-headers.

Errors and retries are already handled via the Connector, while corrupted and missing parts will be caught by the IRS.
There is currently no functionality planned to resume stopped uploads/downloads, however, failed parts can and will be replaced under our current infrastructure.

To address the challenge of coordination, there are several techniques and tools available for parallel downloading and uploading in Python.
In the following, the most common techniques are discussed and examples of how to implement them using popular Python libraries such as `requests`, `asyncio`, `queue`, and `concurrent.futures` are provided.

## Parallelization

There are several techniques and tools available for parallelizing file transfers in Python.
Here are some of the most common approaches:

1\.
Thread-based parallelism: Use the threading module to create multiple threads that can run in parallel.
Each thread can be responsible for downloading or uploading a portion of the file.
This approach is useful when the file transfer involves CPU-bound tasks, such as processing the data being transferred.
However, it's important to be careful when using threads, as they can introduce race conditions and other synchronization issues.

2\.
Process-based parallelism: Use the multiprocessing module to create multiple processes that can run in parallel.
Each process can be responsible for downloading or uploading a portion of the file.
This approach is useful when the file transfer involves CPU-bound tasks and can be especially helpful when working with large files.
However, it can be more memory-intensive than thread-based parallelism.

3\.
Async-based parallelism: Use asynchronous programming techniques, such as coroutines and event loops.
We can use libraries such as asyncio or curio to create asynchronous programs that can handle many I/O-bound tasks in parallel.
This approach is useful when the file transfer involves I/O-bound tasks, such as reading from or writing to a network socket.
Async-based parallelism can be more memory-efficient than thread-based or process-based parallelism, and can often achieve better performance for I/O-bound tasks.

4\.
Batch-based parallelism: Use batch-based parallelism to split the file into multiple parts and transfer them independently.
For example, splitting the file into 10 MB parts and transferring each part separately.
This approach can work well when the file is too large to fit into memory, and can be useful for slow or unreliable network connections.
However, it can be less efficient than other approaches, as each part needs to be transferred independently and checked for errors.

5\.
High-level Interface (Process- or Thread- based): Use the concurrent.futures module, which provides a high-level interface for parallelism.
This module allows for the creation of pools of threads or processes, and submit tasks to those pools.
Each task can be responsible for downloading or uploading a portion of the file.
This approach can be useful by providing an easy-to-use interface for parallelism, and don't need fine-grained control over the parallelism.

Out of these possibilities, we rule out batch-based parallelism, because we don't want to externalize the process of uploading, but instead stay with python.

## Upload

In our specific use case, the remaining four use cases could be applied as follows:

- **Threads**: Use the `threading` module to create a pool of worker threads, each responsible for calling the `upload_part()` function with a specific part number:

  ```python
  import threading


  def upload_in_threads(parts):
      threads = []
      for part in parts:
          thread = threading.Thread(target=upload_part, args=(part,))
          thread.start()
          threads.append(thread)

      for thread in threads:
          thread.join()
  ```

- **Multiprocessing**: Use the `multiprocessing` module to create a pool of worker processes, each responsible for calling the `upload_part()` function with a specific part number:

  ```python
  import multiprocessing


  def upload_in_processes(parts):
      with multiprocessing.Pool() as pool:
          pool.map(upload_part, parts)
  ```

- **Asyncio**: Use the `asyncio` module to perform asynchronous uploads of file parts.
  In this approach, you would use `asyncio` to call the `upload_part()` function for each part asynchronously:

  ```python
  import asyncio


  async def upload_in_asyncio(parts):
      tasks = []
      for part in parts:
          tasks.append(asyncio.create_task(upload_part(part)))

      await asyncio.gather(*tasks)
  ```

- **Concurrent.futures**: Use the `concurrent.futures` module to perform parallel uploads of file parts using the `ThreadPoolExecutor` or `ProcessPoolExecutor` classes:

  ```python
  import concurrent.futures


  def upload_with_threadpool(parts):
      with concurrent.futures.ThreadPoolExecutor() as executor:
          futures = []
          for part in parts:
              future = executor.submit(upload_part, part)
              futures.append(future)

          for future in concurrent.futures.as_completed(futures):
              result = future.result()
  ```

### Conclusion

Something to take into consideration when doing this would be that we would want to set the number of possible parallel downloads to a sensible limit.
For using only processes, asyncio or threads, we would have to build this logic by ourselves, while with the concurrent.futures module we can use pre-existing functionality.
It is not clear if processes or threads would be the better choice.
As we expect the I/O to be the bottleneck, it's unlikely that we'll benefit much from using a `ProcessPoolExecutor` since the overhead of interprocess communication can slow things down.
Therefore, using a `ThreadPoolExecutor` is likely the better choice since it can make the most efficient use of your available CPU cores while minimizing the overhead.
However, in this scenario we can easily swap threads for processes and benchmark both.
For now, we will stick with threads.

A Code snippet showing this functionality:

```python
import concurrent.futures


def upload_parts(upload_part, parts, max_workers=None):
    """
    Uploads a list of file parts using a ThreadPoolExecutor.

    Args:
        upload_part: A Callable to upload a file part
        parts (list): A list of file parts to upload.
        max_workers (int, optional): The maximum number of worker threads to use. Defaults to None.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for part in parts:
            future = executor.submit(upload_part, part)
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
```

## Download

Downloading in parallel can in theory use the same techniques as upload, but as an additional problem, we need to figure out how to write to file without causing race conditions or issues with file locking.

- Use separate temporary files:

  Each download thread or process could write to its own temporary file, and then the main thread could merge the temporary files into the final file in the correct order.
  This avoids the need for synchronization between the download threads and ensures that the file writes are sequential.

- Use a shared memory buffer:

  Each download thread could write its data to a separate buffer in shared memory, using a mechanism such as the multiprocessing module in Python.
  Then, the main thread could merge the buffers into the final file in the correct order.
  This approach avoids the need for file I/O synchronization but requires careful management of the buffer sizes and offsets to avoid data corruption or loss.

- Use a queue:

  Each download thread could write its data to a separate queue, using a mechanism such as the queue module in Python.
  Then, the main thread could read the data from the queues in the correct order and write it to the final file.
  This approach provides a simple way to sequence the downloads, but may not scale well for large files or high download rates.

Although at first glance all three approaches seem applicable, separate temp files require additional coordination and clean up and, therefore, are not favorable.
The shared memory buffer raises additional concerns because problems would arise if the file is bigger than the available ram.
Therefore, using a queue would be the only viable option, coupling with a ThreadPoolExecutor for ease of use and using similar technology to upload.

Here would be an example code snippet:

```python
import requests
import queue
import concurrent.futures

DOWNLOAD_URL = "https://example.com/large_file"
MAX_CONCURRENT_DOWNLOADS = 4
MAX_QUEUE_SIZE = 10
PART_SIZE = 1024 * 1024 * 10  # 10MB

def download_part(part_range, queue):
    """
    Downloads a part of the file defined by the given byte range and adds it to the queue.

    :param part_range: A tuple representing the byte range of the part to download.
    :param queue: A queue object to add the downloaded part to.
    :raises: requests.exceptions.RequestException if the request fails.
    """
    headers = {"Range": f"bytes={part_range[0]}-{part_range[1]}"}
    response = requests.get(DOWNLOAD_URL, headers=headers, stream=True)

    # Make sure the response is a part
    if response.status == 206:
            queue.put((part_range[0], response.content))
            part_range[0] += len(part)
        response.close()
    else:
        response.close()
        raise requests.exceptions.RequestException(f"Failed to download part {part_range[0]}-{part_range[1]}")

def download_file(max_concurrent_downloads, max_queue_size, part_size):
    """
    Downloads a file from the given URL using multiple threads and saves it to a file.

    :param max_concurrent_downloads: Maximum number of parallel downloads.
    :param max_queue_size: Maximum size of the queue.
    :param part_size: Size of each part to download.
    """
    # Get the total size of the file
    with requests.head(DOWNLOAD_URL) as head_response:
        total_size = int(head_response.headers.get("Content-Length", 0))

    # Split the file into parts based on the part size
    parts = [(i * part_size, min((i + 1) * part_size - 1, total_size - 1)) for i in range(total_size // part_size + 1)]

    # Create a queue object to store downloaded parts
    queue = queue.Queue(maxsize=max_queue_size)

    # Download the parts using a thread pool executor
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_downloads) as executor:
        futures = []
        for part in parts:
            future = executor.submit(download_part, part, queue)
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            result = future.result()

    # Write the downloaded parts to a file
    with open("output_file", "wb") as f:
        downloaded_size = 0
        while downloaded_size < total_size:
            start, part = queue.get()
            f.seek(start)
            f.write(part)
            downloaded_size += len(part)
            queue.task_done()
```
