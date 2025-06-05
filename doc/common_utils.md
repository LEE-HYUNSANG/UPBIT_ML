# Common Utility Functions

The `common_utils.py` module consolidates helper functions used across the
F2--F4 packages.

## Functions

| Function | Description |
| --- | --- |
| `load_json(path, default=None)` | Load JSON from *path* and return *default* on failure. |
| `save_json(path, data)` | Write *data* as JSON to *path*, creating directories as needed. |
| `now_kst()` | Return the current KST timestamp as an ISO string. |
| `now()` | Return the current epoch time as a float. |

