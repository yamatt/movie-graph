from .logger import log

from tqdm import tqdm


class Process:
    def __init__(self, sqlite, neo4j):
        self.sqlite = sqlite
        self.neo4j = neo4j

    def sqlite_execute(self, query, params=None):
        for row in tqdm(self.sqlite.cursor.execute(query, params or {})):
            yield row

    # ---- Processing methods ----
    def process_titles(self, neo4j_session):
        NEO4J_QUERY = """
        MERGE (t:Title {tconst: $tconst})
        SET t.title = $title,
            t.titleType = $titleType,
            t.startYear = $startYear,
            t.endYear = $endYear,
            t.runtimeMinutes = $runtimeMinutes,
            t.genres = $genres,
            t.averageRating = $averageRating,
            t.numVotes = $numVotes
        """
        SQLITE_QUERY = """
            SELECT t.title_id, t.original_title, t.type, t.premiered, t.ended,
                   t.runtime_minutes, t.genres,
                   r.rating, r.votes
            FROM titles t
            LEFT JOIN ratings r ON t.title_id = r.title_id
        """
        for row in self.sqlite_execute(SQLITE_QUERY):
            neo4j_session.run(
                NEO4J_QUERY,
                {
                    "tconst": row[0],
                    "title": row[1],
                    "titleType": row[2],
                    "startYear": row[3],
                    "endYear": row[4],
                    "runtimeMinutes": row[5],
                    "genres": row[6],
                    "averageRating": row[7],
                    "numVotes": row[8],
                },
            )

    def process_episodes(self, neo4j_session):
        NEO4J_QUERY = """
        MATCH (e:Title {tconst: $episodeId})
        MATCH (s:Title {tconst: $parentId})
        MERGE (e)-[r:EPISODE_OF]->(s)
        SET r.seasonNumber = $seasonNumber,
            r.episodeNumber = $episodeNumber
        """
        SQLITE_QUERY = "SELECT id, parent_id, season, episode FROM episodes"
        for row in self.sqlite_execute(SQLITE_QUERY):
            neo4j_session.run(
                NEO4J_QUERY,
                {
                    "episodeId": row[0],
                    "parentId": row[1],
                    "seasonNumber": row[2],
                    "episodeNumber": row[3],
                },
            )

    def process_akas(self, neo4j_session):
        NEO4J_QUERY = """
        MATCH (t:Title {tconst: $tconst})
        MERGE (a:Name {name: $alias})
        MERGE (a)-[:ALIAS_OF]->(t)
        SET a.region = $region,
            a.language = $language,
            a.isOriginalTitle = $isOriginalTitle
        """
        SQLITE_QUERY = "SELECT title_id, title, region, language, is_original FROM akas"
        for row in self.sqlite_execute(SQLITE_QUERY):
            neo4j_session.run(
                NEO4J_QUERY,
                {
                    "tconst": row[0],
                    "alias": row[1],
                    "region": row[2],
                    "language": row[3],
                    "isOriginalTitle": row[4],
                },
            )

    def process_people(self, neo4j_session):
        NEO4J_QUERY = """
        MERGE (p:Person {nconst: $nconst})
        SET p.name = $name,
            p.birthYear = $birthYear,
            p.deathYear = $deathYear,
            p.primaryProfession = $primaryProfession
        """
        SQLITE_QUERY = (
            "SELECT id, name, birth_year, death_year, primary_profession FROM people"
        )
        for row in self.sqlite_execute(SQLITE_QUERY):
            neo4j_session.run(
                NEO4J_QUERY,
                {
                    "nconst": row[0],
                    "name": row[1],
                    "birthYear": row[2],
                    "deathYear": row[3],
                    "primaryProfession": row[4],
                },
            )

    def process_crew(self, neo4j_session):
        NEO4J_ACTED_QUERY = """
        MATCH (p:Person {nconst: $nconst})
        MATCH (t:Title {tconst: $tconst})
        MERGE (p)-[:ACTED_IN]->(t)
        """
        NEOJ4_CREW_QUERY = """
        MATCH (p:Person {nconst: $nconst})
        MATCH (t:Title {tconst: $tconst})
        MERGE (p)-[:WORKED_ON]->(t)
        SET r.role = $role
        """
        SQLITE_QUERY = "SELECT title_id, person_id, category FROM crew"
        for row in self.sqlite_execute(SQLITE_QUERY):
            title_id, person_id, category = row
            if category == "actor" or category == "actress":
                neo4j_session.run(
                    NEO4J_ACTED_QUERY, {"tconst": title_id, "nconst": person_id}
                )
            else:
                neo4j_session.run(
                    NEOJ4_CREW_QUERY,
                    {"tconst": title_id, "nconst": person_id, "role": category},
                )

    def run(self):
        with self.neo4j.session as session:
            self.process_titles(session)
            self.process_people(session)
            self.process_akas(session)
            self.process_episodes(session)
            self.process_crew(session)
