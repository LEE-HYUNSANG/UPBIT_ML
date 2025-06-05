# Log Directory Structure

All log files are stored under the `logs/` folder. During development the
following subdirectories are used:

```
logs/
  debug/
  info/
  warning/
  error/
  critical/
  f1/
  f2/
  f3/
  f4/
  f5/
  f6/
  etc/
```

Each functional module writes its logs to the matching `f1`–`f6` directory.
General application logs such as `web.log` or `events.jsonl` live under
`logs/etc`. Level specific directories (`debug`, `info`, `warning`, `error`,
`critical`) are reserved for future use.

Run `python logs/relog.py` to remove all existing logs and recreate the directory
structure. This helps review fresh logs after updates.
