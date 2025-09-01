from functools import cached_property
import sqlite3


class SQLite:
    def __init__(self, db_path):
        self.db_path = db_path

    @cached_property
    def connection(self):
        return self.sqlite3.connect(self.db_path)

    @cached_property
    def cursor(self):
        return self.connection.cursor()
