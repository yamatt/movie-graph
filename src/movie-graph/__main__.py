from .neo4j import Neo4J
from .sqlite import SQLite
from .process import Process

import click


@click.command()
@click.argument("sqlite_file_path", default="imdb.db")
def convert(sqlite_file_path="imdb.db"):
    sqlite = SQLite(sqlite_file_path)
    neo4j = Neo4J.from_env()

    process = Process(sqlite, neo4j)
    process.run()


if __name__ == "__main__":
    convert()
