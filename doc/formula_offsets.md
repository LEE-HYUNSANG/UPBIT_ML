# Formula Offset Support

`eval_formula` now supports indicator and price offsets using the last parameter of a function.
For example, `EMA(20,-1)` references the previous candle's 20 period EMA.
Offsets work for basic OHLCV fields as well, e.g. `Close(-2)`.
When an offset is requested beyond the available data range, the value is treated as zero.

