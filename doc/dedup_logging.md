# Deduplicated Logging

Repeated log messages can quickly bloat the `logs/` directory. The project now
uses a `DedupFilter` to ignore identical lines within a short interval.

`common_utils.setup_logging()` accepts a new `dedup_interval` argument. When
set, each handler drops duplicate records that occur again before the interval
expires. All core modules enable this with a 60 second window.
