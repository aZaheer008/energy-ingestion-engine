# Day 19 - Vectorizing Financial Calculations

## Lesson

When the same calculation needs to run across many price points, a Python loop adds interpreter overhead for every element. NumPy vector operations express the calculation over whole arrays and run the element-wise work in optimized native code, which can be much faster for large datasets.

## What we added to the code

The benchmark generates 100,000 synthetic power and gas prices, then calculates spark spread as power price minus gas price times a heat rate. It compares a Python-loop implementation with a NumPy array expression, checks that both produce matching results, and prints their elapsed times and measured speedup.

## Practical note

The loop version includes an inner loop that repeats the same gas-cost calculation ten times, so this is an illustrative comparison rather than a balanced benchmark of two equally optimized implementations. The timing and speedup depend on the machine, NumPy build, and dataset size. Vectorization avoids Python-level iteration, but it does not guarantee a particular SIMD instruction path or a fixed latency improvement.

## Interview takeaway

I would replace element-by-element Python work with array operations when the calculation applies uniformly across numeric data. I would verify numerical equivalence and benchmark representative inputs, while accounting for allocation and memory costs as well as execution time.
