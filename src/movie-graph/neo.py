from functools import cached_property
import os

from neo4j import GraphDatabase

class Neo4J:
    @classmethod
    def from_env(cls):
        return cls(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
        )
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password

    @cached_property
    def driver(self):
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()
