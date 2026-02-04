import os
from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


class Database:
    def __init__(self):
        self.pool = None

    @asynccontextmanager
    async def get_pool(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(DATABASE_URL)
        yield self.pool


db = Database()
