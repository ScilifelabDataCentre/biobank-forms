"""General helper functions."""

import datetime

import flask
import pymongo


def get_dbclient(conf) -> pymongo.mongo_client.MongoClient:
    """
    Get the connection to the MongoDB database server.

    Args:
        conf: A mapping with the relevant mongo keys available.

    Returns:
        pymongo.mongo_client.MongoClient: The client connection.
    """
    return pymongo.MongoClient(host=conf['mongo']['host'],
                               port=conf['mongo']['port'],
                               username=conf['mongo']['user'],
                               password=conf['mongo']['password'])


def get_db(dbserver: pymongo.mongo_client.MongoClient, conf) -> pymongo.database.Database:
    """
    Get the connection to the MongoDB database.

    Args:
        dbserver (pymongo.mongo_client.MongoClient): Connection to the database.
        conf: A mapping with the relevant mongo keys available.

    Returns:
        pymongo.database.Database: The database connection.
    """
    return dbserver.get_database(conf['mongo']['db'])


def make_timestamp():
    """
    Generate a timestamp of the current time.

    returns:
        datetime.datetime: The current time.
    """
    return datetime.datetime.now()
