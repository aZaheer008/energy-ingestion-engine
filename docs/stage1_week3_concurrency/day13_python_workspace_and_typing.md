# Day 13 - Python Workspace and Typing

## Lesson

This step introduces the Python side of the compute grid with explicit contracts for market data and calculation results. Defining the expected shapes and types up front makes it easier to keep incoming data and later processing code consistent.

## What we added to the code

- **Python dependencies:** `requirements.txt` lists NumPy and pandas for numerical work, plus mypy for static type checking.
- **Domain contracts:** `domain_contracts.py` defines allowed market operators and time-of-use blocks, a typed dictionary shape for nodal price ticks, and frozen dataclasses for historical node vectors and compute results. The result model includes rolling volatility, maximum price spike, mean price, and the process ID associated with the calculation.

## Practical note

Run mypy through the Python environment, rather than `npx`: `python -m mypy src/domain_contracts.py`. The initial contract file passes this check in the package's virtual environment.

## Interview takeaway

I would explain that shared typed contracts make data boundaries clearer before implementing the computation. These definitions prepare the compute package for numerical and concurrent processing; they describe the expected data but do not, by themselves, implement concurrency.
