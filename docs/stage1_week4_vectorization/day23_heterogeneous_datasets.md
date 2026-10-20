# Day 23 - Cleaning and Aligning Time-Series Data

## Lesson

Market data feeds can arrive with missing intervals or different reporting schedules. Before comparing or aggregating them, timestamps need a clear timezone convention and each series needs to be aligned to the intended time grid. Resampling can add missing intervals, while forward-fill can carry the last known value into a gap when that is appropriate for the data.

## What we added to the code

The Polars demo creates a small synthetic nodal price series with a missing five-minute tick. It sorts the data by timestamp, uses `upsample` to build a regular five-minute grid per node, and forward-fills the missing LMP value. The resulting frame shows the aligned timestamps and filled prices.

## Practical note

The example uses naive datetimes and does not convert timestamps to UTC, resolve daylight-saving-time ambiguity, or merge multiple feeds with an as-of join. Its November 1 timestamp is only illustrative; it does not test a timezone-aware DST transition. In a real pipeline, parse timestamps with an explicit timezone, normalize them consistently—often to UTC—and define how missing values should be handled for each field. Forward-fill is not always valid for prices or other market data, and imputed values should be identifiable where downstream analysis requires it.

## Interview takeaway

I would first standardize timestamp interpretation, then align feeds using the correct interval and join semantics. Resampling plus forward-fill can be useful for suitable fields, and an as-of join can match observations with nearby timestamps, but both require explicit rules for tolerances, duplicates, gaps, and data provenance. I would validate those choices against the market's source data and downstream use.
