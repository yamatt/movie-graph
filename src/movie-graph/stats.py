"""
Database statistics and reporting utilities.
"""

import os
from .logger import log


def report_stats(conn, db_path):
    """Report statistics about the compact database."""
    cursor = conn.cursor()

    title_count = cursor.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
    people_count = cursor.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    crew_count = cursor.execute("SELECT COUNT(*) FROM crew").fetchone()[0]

    file_size_bytes = os.path.getsize(db_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    log.info(
        "database_statistics",
        titles=title_count,
        people=people_count,
        crew=crew_count,
        size_mb=round(file_size_mb, 2),
    )
