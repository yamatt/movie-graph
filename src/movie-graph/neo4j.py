from functools import cached_property
import os

from neo4j import GraphDatabase


class Neo4J:
    @classmethod
    def from_env(cls, uri="bolt://localhost:7687"):
        uri = os.getenv("NEO4J_URI", uri)
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]
        return cls(uri, user, password)

    def __init__(self, uri, user, password, database_name="neo4j"):
        self.uri = uri
        self.user = user
        self.password = password
        self.database_name = database_name

    @cached_property
    def driver(self):
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    @cached_property
    def session(self):
        return self.driver.session(database=self.database_name)
