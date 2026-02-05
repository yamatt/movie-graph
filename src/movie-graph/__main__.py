from .compact import CompactDatabase
from .logger import log

import click
import subprocess
import os


@click.command()
@click.option(
    "--source-db",
    default="imdb-full.db",
    help="Path to the full IMDb database (will be created if it doesn't exist)",
)
@click.option(
    "--target-db",
    default="imdb-compact.db",
    help="Path to the compact filtered database to create",
)
@click.option(
    "--cache-dir",
    default="downloads",
    help="Directory to cache IMDb download files",
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Skip downloading and building the source database",
)
@click.option(
    "--min-votes",
    default=40000,
    type=int,
    help="Minimum number of votes for titles to be included (default: 40000)",
)
def build(source_db, target_db, cache_dir, skip_download, min_votes):
    """Build a compact IMDb database with only popular titles and actors."""

    if not skip_download:
        # Download and build the full database with only the tables we need
        log.info("downloading_imdb_data")

        # Remove old source database if it exists
        if os.path.exists(source_db):
            log.info("removing_old_source_database", path=source_db)
            os.remove(source_db)

        # Use imdb-sqlite to download only the tables we need
        # Tables: titles, ratings, people, crew (principals)
        # Note: No AKAs (rely on fuzzy matching) or episodes (too much data)
        cmd = [
            "imdb-sqlite",
            "--db",
            source_db,
            "--cache-dir",
            cache_dir,
            "--only",
            "titles,ratings,people,crew",
        ]

        log.info("running_imdb_sqlite", command=" ".join(cmd))
        subprocess.run(cmd, check=True)

    # Build the compact database
    log.info("building_compact_database")
    compact_db = CompactDatabase(source_db, target_db, min_votes=min_votes)
    compact_db.build()

    log.info("complete", target=target_db)


if __name__ == "__main__":
    build()
