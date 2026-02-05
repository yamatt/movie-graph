"""
Database schema definitions for the compact IMDb database.
"""

SCHEMA_SQL = """
    PRAGMA page_size = 4096;
    PRAGMA auto_vacuum = FULL;
    PRAGMA journal_mode = DELETE;

    CREATE TABLE IF NOT EXISTS titles (
        title_id TEXT PRIMARY KEY,
        original_title TEXT NOT NULL,
        type INTEGER NOT NULL CHECK(type IN (1, 2, 3)),  -- 1=movie, 2=tvSeries, 3=tvMiniSeries
        premiered INTEGER
    ) WITHOUT ROWID;

    CREATE TABLE IF NOT EXISTS people (
        person_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    ) WITHOUT ROWID;

    CREATE TABLE IF NOT EXISTS crew (
        title_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        category TEXT NOT NULL,
        PRIMARY KEY (title_id, person_id, category),
        FOREIGN KEY (title_id) REFERENCES titles(title_id),
        FOREIGN KEY (person_id) REFERENCES people(person_id)
    ) WITHOUT ROWID;
"""

INDEXES_SQL = """
    CREATE INDEX IF NOT EXISTS idx_titles_type ON titles(type);
    CREATE INDEX IF NOT EXISTS idx_titles_premiered ON titles(premiered);

    CREATE INDEX IF NOT EXISTS idx_crew_title_id ON crew(title_id);
    CREATE INDEX IF NOT EXISTS idx_crew_person_id ON crew(person_id);

    CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
"""

# Type mapping for title types
TYPE_MAP = {"movie": 1, "tvSeries": 2, "tvMiniSeries": 3}

# Categories of crew we're interested in
CREW_CATEGORIES = ("actor", "actress", "director", "writer", "producer")
