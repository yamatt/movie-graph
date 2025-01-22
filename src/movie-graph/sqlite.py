from functools import cached_property
import os
import sqlite3

class SQLite:
    @classmethod
    def from_env(cls):
        return cls(os.getenv("SQLITE_DB_PATH"))
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    @cached_property
    def connection(self):
        return sqlite3.connect(self.db_path)

    def close(self):
        self.connection.close()
