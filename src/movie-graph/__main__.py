from neo import Neo4J
from sqlite import SQLite


SQLITE = SQLite.from_env()
NEO4J = Neo4J.from_env()

# Function to create nodes and relationships in Neo4J
def populate_neo4j(tx, actors, tv_shows, movies, relationships):
    # Create nodes
    for actor in actors:
        tx.run("MERGE (a:Actor {name: $name})", name=actor)
    for show in tv_shows:
        tx.run("MERGE (t:TVShow {title: $title})", title=show)
    for movie in movies:
        tx.run("MERGE (m:Movie {title: $title})", title=movie)

    # Create relationships
    for actor, title, kind in relationships:
        if kind == "movie":
            tx.run("""
                MATCH (a:Actor {name: $actor}), (m:Movie {title: $title})
                MERGE (a)-[:ACTED_IN]->(m)
            """, actor=actor, title=title)
        elif kind == "tv_show":
            tx.run("""
                MATCH (a:Actor {name: $actor}), (t:TVShow {title: $title})
                MERGE (a)-[:ACTED_IN]->(t)
            """, actor=actor, title=title)

# Retrieve data from SQLite
def get_data_from_sqlite():
    cursor = sqlite_conn.cursor()

    # Query actors, TV shows, and movies
    cursor.execute("SELECT DISTINCT name FROM actors")
    actors = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT title FROM tv_shows")
    tv_shows = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT title FROM movies")
    movies = [row[0] for row in cursor.fetchall()]

    # Query relationships (actor -> tv_show/movie)
    cursor.execute("""
        SELECT a.name, t.title, 'tv_show' AS kind
        FROM actors a
        JOIN acted_in ai ON a.id = ai.actor_id
        JOIN tv_shows t ON ai.tv_show_id = t.id
        UNION ALL
        SELECT a.name, m.title, 'movie' AS kind
        FROM actors a
        JOIN acted_in ai ON a.id = ai.actor_id
        JOIN movies m ON ai.movie_id = m.id
    """)
    relationships = cursor.fetchall()

    return actors, tv_shows, movies, relationships

def get_args(args=None):
    parser = argparse.ArgumentParser(description="Syncronise movie graph with data from SQLite")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands.", required=True)

    sync_parser = subparsers.add_parser("sync", help="Sync from SQLite to Neo4J.")
    sync_parser.add_argument("--batch-size", type=int, default=100, help="Number of records to process in each batch.")

    return parser.parse_args(args)

if __name__ == "__main__":
    args = get_args()

    with NEO4J.driver.session() as session:

        actors, tv_shows, movies, relationships = SQLITE.get_data()
        session.write_transaction(populate_neo4j, actors, tv_shows, movies, relationships)

    SQLITE.close()
    NEO4J.close()

