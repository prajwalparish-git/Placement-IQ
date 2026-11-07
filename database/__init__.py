"""Telemetry layer: one schema on PostgreSQL, with an automatic SQLite fallback.

`connection` picks the backend and fails over; `models` holds the tables; `crud` saves and
fetches records and aggregates analytics. Nothing in piq imports this package yet: the app's
own data stays in piq/db.py and data/placementiq.db.
"""
