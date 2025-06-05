# SellQty_5m Zero Handling

The `eval_formula` helper now guards against division by zero when `SellQty_5m`
values are missing or zero. Any occurrence of `SellQty_5m` in a formula is
replaced with an expression that defaults to a tiny epsilon (`1e-8`) when the
actual value is zero. This prevents runtime errors in strategy expressions like
HYUN's buy rule which divide by `SellQty_5m`.
