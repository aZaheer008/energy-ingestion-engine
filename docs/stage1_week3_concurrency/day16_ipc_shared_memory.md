# Day 16 - Shared Memory for Process Communication

## Lesson

Separate processes do not normally share Python objects directly. For large numeric arrays, `multiprocessing.shared_memory` can provide a common memory buffer that each process can access through its own NumPy array view. This can avoid copying the full array between processes, though process startup and sending task metadata still have costs.

## What we added to the code

The shared-memory demo places a five-value `float64` price vector in a shared memory block. Worker processes attach to that block and update their assigned value in place using a simple adjustment formula. A multiprocessing lock protects the update section, and the main process displays the results before closing and unlinking the shared block.

## Practical note

This is a small demonstration rather than a performance benchmark: a five-value array is too small to show meaningful transfer savings. The lock also serializes the protected updates, so synchronization strategy should match the actual shared-write pattern. In production, use shared memory only when its setup and coordination costs are justified, and ensure the block is closed and unlinked even if a worker fails.

## How the lock works in this example

The lock provides mutual exclusion: only one worker at a time can enter the `with lock` block. A worker that reaches the block while another holds the lock waits until it is released. This prevents simultaneous access to the protected operation, but it does not guarantee a particular wait order or rule out starvation on every operating system. Keeping a critical section short helps limit waiting and latency.

In this demo, each worker updates a different array index, so the writes do not overlap. The shared lock therefore serializes updates that could otherwise happen independently; for this specific layout, it can be removed if each task is guaranteed to own a unique index. If workers need to update the same value or shared counter, synchronization is necessary. Do expensive calculations in private memory, then hold a lock only around the brief shared update.

## Interview takeaway

I would consider shared memory when processes need access to large numeric buffers and copying them through queues would be costly. I would keep task messages small, define clear ownership or synchronization for writes, and benchmark end-to-end performance against simpler approaches before adding this complexity.
