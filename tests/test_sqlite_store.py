from pathlib import Path

from fastapi_insights.backends.sqlite import SQLiteMetricsStore


def test_sqlite_store_records_and_reads_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    store = SQLiteMetricsStore(str(db_path))

    store.record_request_metrics("/users", 0.12, 200, "GET")
    store.record_request_metrics("/users", 0.33, 500, "POST")

    metrics = store.get_metrics(0, 9_999_999_999, bucket_size=300)
    assert metrics["top_routes"]["/users"] == 2
    assert metrics["top_error_prone_requests"]["/users"] == 1
    assert metrics["requests_per_method"] == {"GET": 1, "POST": 1}
    assert metrics["meta"]["bucket_size_secs"] == 300


def test_sqlite_cleanup_respects_ttl(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    store = SQLiteMetricsStore(str(db_path), ttl_seconds=1)
    cursor = store.conn.cursor()
    cursor.execute(
        """
        INSERT INTO request_metrics (bucket_size, bucket_ts, path, data)
        VALUES (?, ?, ?, ?)
        """,
        (
            300,
            1,
            "/stale",
            '{"latencies":[],"count":1,"errors":0,"status_codes":{"2XX":1},"methods":{"GET":1},"rw_count":{"read":1,"write":0}}',
        ),
    )
    cursor.execute(
        """
        INSERT INTO system_metrics (bucket_size, bucket_ts, key, data)
        VALUES (?, ?, ?, ?)
        """,
        (300, 1, "cpu_percent", '{"timestamp":1,"min":1.0,"max":1.0,"avg":1.0}'),
    )
    store.conn.commit()

    store._cleanup_expired_ttl()

    request_rows = store.conn.execute("SELECT COUNT(*) FROM request_metrics").fetchone()
    system_rows = store.conn.execute("SELECT COUNT(*) FROM system_metrics").fetchone()
    assert request_rows == (0,)
    assert system_rows == (0,)
