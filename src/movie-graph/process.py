from .logger import log

from tqdm import tqdm

CREATE_TITLE = """
MERGE (t:Title {tconst: $tconst})
SET t.title = $title, 
    t.titleType = $titleType,
    t.startYear = $startYear,
    t.endYear = $endYear,
    t.runtimeMinutes = $runtimeMinutes,
    t.genres = $genres
"""

CREATE_PERSON = """
MERGE (p:Person {nconst: $nconst})
SET p.name = $name,
    p.birthYear = $birthYear,
    p.deathYear = $deathYear,
    p.primaryProfession = $primaryProfession
"""

ACTED_IN = """
MATCH (t:Title {tconst: $tconst})
MATCH (p:Person {nconst: $nconst})
MERGE (p)-[:ACTED_IN {characters: $characters}]->(t)
"""

DIRECTED = """
MATCH (t:Title {tconst: $tconst})
MATCH (p:Person {nconst: $nconst})
MERGE (p)-[:DIRECTED]->(t)
"""

WROTE = """
MATCH (t:Title {tconst: $tconst})
MATCH (p:Person {nconst: $nconst})
MERGE (p)-[:WROTE]->(t)
"""


class Process:
    def __init__(self, sqlite, neo4j):
        self.sqlite = sqlite
        self.neo4j = neo4j

    def run(self):
        with self.neo4j.session() as session:
            # Import Titles
            for row in tqdm(
                self.sqlite.cursor.execute(
                    "SELECT tconst, primaryTitle, titleType, startYear, endYear, runtimeMinutes, genres FROM title_basics"
                ),
                desc="Importing Titles",
                unit="titles",
            ):
                session.run(
                    CREATE_TITLE,
                    {
                        "tconst": row[0],
                        "title": row[1],
                        "titleType": row[2],
                        "startYear": row[3],
                        "endYear": row[4],
                        "runtimeMinutes": row[5],
                        "genres": row[6],
                    },
                )

            # Import People
            for row in tqdm(
                self.sqlite.cursor.execute(
                    "SELECT nconst, primaryName, birthYear, deathYear, primaryProfession FROM name_basics"
                ),
                desc="Importing People",
                unit="people",
            ):
                session.run(
                    CREATE_PERSON,
                    {
                        "nconst": row[0],
                        "name": row[1],
                        "birthYear": row[2],
                        "deathYear": row[3],
                        "primaryProfession": row[4],
                    },
                )

            # Relationships: ACTED_IN
            for row in tqdm(
                elf.sqlite.cursor.execute(
                    "SELECT tconst, nconst, characters FROM title_principals WHERE category IN ('actor','actress')"
                ),
                desc="Creating ACTED_IN relationships",
                unit="relationships",
            ):
                session.run(
                    ACTED_IN,
                    {
                        "tconst": row[0],
                        "nconst": row[1],
                        "characters": row[2],
                    },
                )

            # Relationships: DIRECTED
            for row in tqdm(
                self.sqlite.cursor.execute(
                    "SELECT tconst, directors FROM title_crew WHERE directors IS NOT NULL"
                ),
                desc="Creating DIRECTED relationships",
                unit="relationships",
            ):
                tconst, directors = row
                for director in directors.split(","):
                    session.run(DIRECTED, {"tconst": tconst, "nconst": director})

            # Relationships: WROTE
            for row in tqdm(
                self.sqlite.cursor.execute(
                    "SELECT tconst, writers FROM title_crew WHERE writers IS NOT NULL"
                ),
                desc="Creating WROTE relationships",
                unit="relationships",
            ):
                tconst, writers = row
                for writer in writers.split(","):
                    session.run(WROTE, {"tconst": tconst, "nconst": writer})
