# Day 14 - Understanding the GIL

## Lesson

In standard GIL-enabled CPython, the Global Interpreter Lock (GIL) allows only one thread at a time to execute Python bytecode within a process. It also helps protect interpreter state, including reference-counted object management.

## Why it matters for compute work

Threads are useful for tasks that spend time waiting on network or disk operations. For CPU-heavy Python work, such as processing large sets of market prices, the GIL generally prevents multiple threads in one process from running Python bytecode in parallel across CPU cores. Adding threads alone may therefore not speed up that work.

## Practical takeaway

For CPU-bound grid analytics that need to use multiple cores, consider multiprocessing: separate processes have separate interpreters and can run in parallel. This adds process and data-transfer overhead, so measure the workload before choosing an approach. Some native libraries release the GIL while doing computation, so their threading behavior can differ from pure Python code.

## Interview takeaway

I would distinguish concurrency from parallel execution: Python threads can help with I/O-bound work, but the GIL limits parallel execution of Python bytecode in a single process. For CPU-bound tasks, I would evaluate process-based parallelism or libraries that perform work in native code, then benchmark the complete pipeline.