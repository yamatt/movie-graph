"""
Build a compact IMDb database with only popular titles and actors.
"""

import sqlite3
import os
from tqdm import tqdm

from .logger import log
from .schema import SCHEMA_SQL, INDEXES_SQL, TYPE_MAP, CREW_CATEGORIES
from .stats import report_stats


class CompactDatabase:
    """Creates a compact SQLite database with filtered IMDb data."""

    def __init__(self, source_db_path, target_db_path, min_votes=5000):
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.min_votes = min_votes

    def build(self):
        """Build the compact database."""
        log.info(
            "building_compact_database",
            source=self.source_db_path,
            target=self.target_db_path,
        )

        # Remove target if exists
        if os.path.exists(self.target_db_path):
            os.remove(self.target_db_path)

        source_conn = sqlite3.connect(self.source_db_path)
        target_conn = sqlite3.connect(self.target_db_path)

        try:
            self._create_schema(target_conn)
            self._copy_filtered_titles(source_conn, target_conn)
            self._copy_filtered_people(source_conn, target_conn)
            self._copy_crew(source_conn, target_conn)
            self._copy_episode_crew(source_conn, target_conn)
            self._create_indexes(target_conn)
            self._vacuum(target_conn)

            target_conn.commit()
            log.info("compact_database_complete", path=self.target_db_path)
            report_stats(target_conn, self.target_db_path)

        finally:
            source_conn.close()
            target_conn.close()

    def _create_schema(self, conn):
        """Create the target database schema."""
        log.info("creating_schema")
        # Optimize for HTTP VFS (sql.js-httpvfs)
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA page_size = 32768")  # 32KB pages for fewer HTTP requests
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def _copy_filtered_titles(self, source_conn, target_conn):
        """Copy only popular titles (movies and TV shows)."""
        log.info("copying_filtered_titles")

        # Select popular titles: movies and TV shows with significant vote counts
        # We don't filter by rating to include all widely-watched content,
        # even if it has mixed reviews, as it may have important actor crossovers
        query = """
            SELECT t.title_id, t.original_title, t.type, t.premiered
            FROM titles t
            JOIN ratings r ON t.title_id = r.title_id
            WHERE t.type IN ('movie', 'tvSeries', 'tvMiniSeries')
              AND r.votes >= ?
        """

        cursor = source_conn.execute(query, (self.min_votes,))

        insert_query = """
            INSERT INTO titles (title_id, original_title, type, premiered)
            VALUES (?, ?, ?, ?)
        """

        rows = cursor.fetchall()
        log.info("copying_titles", count=len(rows))

        for row in tqdm(
            rows,
            desc="Copying titles",
            mininterval=0,
            miniters=max(1, len(rows) // 100),
        ):
            title_id, original_title, type_str, premiered = row
            type_int = TYPE_MAP.get(type_str, 1)  # Default to movie if unknown
            target_conn.execute(
                insert_query, (title_id, original_title, type_int, premiered)
            )

        target_conn.commit()

    def _copy_filtered_people(self, source_conn, target_conn):
        """Copy only people who worked on popular titles and meet minimum credit requirements."""
        log.info("copying_filtered_people")

        # Get all title IDs from target
        title_ids = [
            row[0]
            for row in target_conn.execute("SELECT title_id FROM titles").fetchall()
        ]

        if not title_ids:
            log.warning("no_titles_to_copy_people_for")
            return

        # Process in batches due to SQLite parameter limits
        batch_size = 999
        all_people = []
        people_ids_seen = set()

        num_batches = (len(title_ids) + batch_size - 1) // batch_size
        for i in tqdm(
            range(0, len(title_ids), batch_size),
            desc="Finding people",
            mininterval=0,
            miniters=max(1, num_batches // 100),
        ):
            batch = title_ids[i : i + batch_size]
            placeholders = ",".join("?" * len(batch))

            query = f"""
                SELECT DISTINCT p.person_id, p.name
                FROM people p
                JOIN crew c ON p.person_id = c.person_id
                WHERE c.title_id IN ({placeholders})
                  AND c.category IN {CREW_CATEGORIES}
            """

            cursor = source_conn.execute(query, batch)
            for row in cursor:
                if row[0] not in people_ids_seen:
                    people_ids_seen.add(row[0])
                    all_people.append(row)

        log.info("copying_people", count=len(all_people))

        insert_query = """
            INSERT INTO people (person_id, name)
            VALUES (?, ?)
        """

        for row in tqdm(
            all_people,
            desc="Copying people",
            mininterval=0,
            miniters=max(1, len(all_people) // 100),
        ):
            target_conn.execute(insert_query, row)

        target_conn.commit()

    def _copy_crew(self, source_conn, target_conn):
        """Copy crew relationships for filtered titles and people."""
        log.info("copying_crew")

        # Get valid IDs from target
        title_ids = [
            row[0]
            for row in target_conn.execute("SELECT title_id FROM titles").fetchall()
        ]
        person_ids = [
            row[0]
            for row in target_conn.execute("SELECT person_id FROM people").fetchall()
        ]

        if not title_ids or not person_ids:
            log.warning("no_titles_or_people_to_copy_crew_for")
            return

        # For large datasets, we'll process in batches
        batch_size = 500
        total_copied = 0
        seen_combinations = set()  # Track unique (title_id, person_id, category) tuples

        num_batches = (len(title_ids) + batch_size - 1) // batch_size
        for i in tqdm(
            range(0, len(title_ids), batch_size),
            desc="Copying crew",
            mininterval=0,
            miniters=max(1, num_batches // 100),
        ):
            title_batch = title_ids[i : i + batch_size]
            title_placeholders = ",".join("?" * len(title_batch))

            # Use DISTINCT to deduplicate at the SQL level
            query = f"""
                SELECT DISTINCT title_id, person_id, category
                FROM crew
                WHERE title_id IN ({title_placeholders})
                  AND category IN {CREW_CATEGORIES}
            """

            cursor = source_conn.execute(query, title_batch)

            insert_query = """
                INSERT INTO crew (title_id, person_id, category)
                VALUES (?, ?, ?)
            """

            # Filter to only include people we have and avoid duplicates
            person_id_set = set(person_ids)
            for row in cursor:
                if row[1] in person_id_set:
                    title_id, person_id, category = row

                    # Normalize 'actress' to 'actor' for simpler queries
                    if category == "actress":
                        category = "actor"

                    # Create a tuple to track this combination
                    combo = (title_id, person_id, category)
                    if combo not in seen_combinations:
                        seen_combinations.add(combo)
                        target_conn.execute(
                            insert_query, (title_id, person_id, category)
                        )
                        total_copied += 1

        target_conn.commit()
        log.info("crew_copied", count=total_copied, deduplicated=True)

    def _copy_episode_crew(self, source_conn, target_conn):
        """Copy crew from TV episodes without adding the episodes themselves."""
        log.info("copying_episode_crew")

        has_episodes = source_conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='episodes'"
        ).fetchone()
        if not has_episodes:
            log.info("episodes_table_missing")
            return

        # Get TV series IDs from target
        tv_series = target_conn.execute(
            "SELECT title_id FROM titles WHERE type IN (2, 3)"
        ).fetchall()

        if not tv_series:
            log.info("no_tv_series_for_episode_crew")
            return

        tv_series_ids = [row[0] for row in tv_series]
        batch_size = 999
        all_crew_from_episodes = []
        seen = set()

        # Find all episode crew for these TV series
        num_batches = (len(tv_series_ids) + batch_size - 1) // batch_size
        for i in tqdm(
            range(0, len(tv_series_ids), batch_size),
            desc="Finding episode crew",
            mininterval=0,
            miniters=max(1, num_batches // 100),
        ):
            batch = tv_series_ids[i : i + batch_size]
            placeholders = ",".join("?" * len(batch))

            query = f"""
                SELECT DISTINCT e.show_title_id, c.person_id, c.category
                FROM episodes e
                JOIN crew c ON e.episode_title_id = c.title_id
                WHERE e.show_title_id IN ({placeholders})
                  AND c.category IN {CREW_CATEGORIES}
            """

            cursor = source_conn.execute(query, batch)
            for row in cursor:
                combo = (row[0], row[1], row[2])
                if combo not in seen:
                    seen.add(combo)
                    all_crew_from_episodes.append(row)

        log.info("found_episode_crew", count=len(all_crew_from_episodes))

        if not all_crew_from_episodes:
            return

        # Get existing people IDs and filtered title IDs
        existing_people = set(
            row[0]
            for row in target_conn.execute("SELECT person_id FROM people").fetchall()
        )
        title_ids = [
            row[0]
            for row in target_conn.execute("SELECT title_id FROM titles").fetchall()
        ]

        # Collect new people we need to add
        new_people = set()
        for show_id, person_id, category in all_crew_from_episodes:
            if person_id not in existing_people:
                new_people.add(person_id)

        # Add new people
        if new_people:
            new_people_list = list(new_people)
            people_data = []

            num_batches = (len(new_people_list) + batch_size - 1) // batch_size
            for i in tqdm(
                range(0, len(new_people_list), batch_size),
                desc="Fetching episode people",
                mininterval=0,
                miniters=max(1, num_batches // 100),
            ):
                batch = new_people_list[i : i + batch_size]
                placeholders = ",".join("?" * len(batch))

                query = f"SELECT person_id, name FROM people WHERE person_id IN ({placeholders})"
                cursor = source_conn.execute(query, batch)
                people_data.extend(cursor.fetchall())

            log.info("adding_episode_people", count=len(people_data))
            insert_query = "INSERT INTO people (person_id, name) VALUES (?, ?)"
            for row in tqdm(
                people_data,
                desc="Copying episode people",
                mininterval=0,
                miniters=max(1, len(people_data) // 100),
            ):
                target_conn.execute(insert_query, row)

            existing_people.update(new_people)

        # Add crew relationships (normalize actress to actor)
        log.info("adding_episode_crew_relationships")
        existing_crew = set(
            tuple(row)
            for row in target_conn.execute(
                "SELECT title_id, person_id, category FROM crew"
            ).fetchall()
        )

        insert_query = (
            "INSERT INTO crew (title_id, person_id, category) VALUES (?, ?, ?)"
        )
        added_count = 0

        for show_id, person_id, category in tqdm(
            all_crew_from_episodes,
            desc="Adding episode crew",
            mininterval=0,
            miniters=max(1, len(all_crew_from_episodes) // 100),
        ):
            # Only add if person exists in our database
            if person_id in existing_people:
                # Normalize actress to actor
                if category == "actress":
                    category = "actor"

                combo = (show_id, person_id, category)
                if combo not in existing_crew:
                    existing_crew.add(combo)
                    target_conn.execute(insert_query, combo)
                    added_count += 1

        target_conn.commit()
        log.info("episode_crew_added", count=added_count)

    def _create_indexes(self, conn):
        """Create indexes for better query performance."""
        log.info("creating_indexes")
        conn.executescript(INDEXES_SQL)
        conn.commit()

    def _vacuum(self, conn):
        """Optimize database for size and HTTP VFS access."""
        log.info("optimizing_database")
        conn.execute("ANALYZE")
        conn.execute("VACUUM")  # Reorganizes database with new page_size
        conn.commit()
        log.info("database_optimized_for_http_vfs")
