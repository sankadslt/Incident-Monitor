import threading
from pymongo import MongoClient
from utils.core_utils import ConfigSingleton
from utils.logger import SingletonLogger


class MongoDBConnectionSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDBConnectionSingleton, cls).__new__(cls)
                    cls._instance._initialize_connection()
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def _initialize_connection(self):
        self.logger = SingletonLogger.get_logger("dbLogger")
        try:
            config = ConfigSingleton().get_config()
            mongo_uri = config.get("mongo_uri", "")
            mongo_dbname = config.get("mongo_db", "")

            if not mongo_uri or not mongo_dbname:
                raise ValueError("MongoDB URI or database name missing in configuration.")

            self.logger.info("Connecting to MongoDB with DB: %s", mongo_dbname)
            self.client = MongoClient(mongo_uri)
            self.database = self.client[mongo_dbname]
            self.logger.info("MongoDB connection established successfully.")
        except Exception as err:
            self.logger.error("Error connecting to MongoDB: %s", err)
            self.client = None
            self.database = None

    def get_database(self):
        return self.database

    def close_connection(self):
        if self.client:
            try:
                self.client.close()
                self.logger.info("MongoDB connection closed.")
            except Exception as err:
                self.logger.error("Error closing MongoDB connection: %s", err)
            finally:
                self.client = None
                self.database = None
                MongoDBConnectionSingleton._instance = None

    def __enter__(self):
        return self.get_database()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
