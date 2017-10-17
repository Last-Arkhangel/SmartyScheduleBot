import core


class Cache:

    @classmethod
    def create_cache_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS cache(
                          key TEXT PRIMARY KEY NOT NULL,
                          data TEXT DEFAULT CURRENT_TIMESTAMP,
                          create_time TEXT,
                          requests INTEGER DEFAULT 0) 
                          WITHOUT ROWID"""

        return core.DBManager.execute_query(query)

    @classmethod
    def get_from_cache(cls, key):

        query = "SELECT * FROM cache WHERE key=?"

        r = core.DBManager.execute_query(query, (key,))
        if r:
            cls.recount_requests_to_cache(key)

        return r

    @classmethod
    def recount_requests_to_cache(cls, key):

        query = "UPDATE cache SET requests=requests+1 WHERE key=?"
        return core.DBManager.execute_query(query, (key,))

    @classmethod
    def put_in_cache(cls, key, data):

        query = "INSERT or IGNORE INTO cache (key, data, create_time) VALUES (?, ?, CURRENT_TIMESTAMP)"
        return core.DBManager.execute_query(query, (key, data))

    @classmethod
    def get_keys(cls):

        query = "SELECT key FROM cache"
        return core.DBManager.execute_query(query, )

    @classmethod
    def clear_cache(cls):

        query = "DELETE FROM cache"
        return core.DBManager.execute_query(query, )

