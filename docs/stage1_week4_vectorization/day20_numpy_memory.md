# Day 20 - NumPy Memory and Array Views

## Lesson

NumPy arrays store typed values in memory and expose metadata such as shape, item size, strides, and C-contiguity. Understanding how an array is laid out helps explain how slices access the original data and when an operation creates a separate array.

## What we added to the code

The memory demo creates a small synthetic price matrix and prints its layout metadata. It then shows that a regular slice is a view: changing the slice also changes the original matrix. Calling `.copy()` makes an independent subset instead. Finally, it applies one loss factor per node to all time intervals using broadcasting with `newaxis`, without writing an explicit Python loop.

## Practical note

Views can save memory, but changing one also changes its source. Use `.copy()` when the subset must be safely modified in isolation. Broadcasting avoids manually repeating the multiplier vector, although the resulting adjusted-price expression creates an output array. Contiguous storage and vectorized operations can help performance, but actual cache and SIMD behavior depends on the operation, array layout, and NumPy build.

## Interview takeaway

I would check whether an array operation returns a view or a copy before mutating data, and use broadcasting to apply per-node or per-interval factors cleanly. I would also inspect dtype, shape, strides, and contiguity when memory use or performance matters, then benchmark the real workload rather than assume a particular speedup.

## A question : when does array handling allocate memory?

Basic slicing, such as selecting a row range, usually returns a view that refers to the original buffer through its shape and strides. It avoids copying the selected values, but changes through the view can affect the source array. Fancy indexing and boolean masks generally create a new array containing copied values, which uses additional memory.

Repeated allocations in a hot loop can add memory-management and allocator overhead, increasing latency variability. In CPython, many objects are reclaimed promptly through reference counting, so it is not accurate to say every NumPy allocation triggers garbage collection. The practical concern is repeated allocation and copying, especially for large arrays.

For predictable workloads, allocate reusable output buffers once and pass them through NumPy operations that support an `out=` parameter. This can avoid some temporary arrays, but not every operation supports `out=`, and reuse requires compatible shape and dtype. Measure the actual loop before optimizing.
