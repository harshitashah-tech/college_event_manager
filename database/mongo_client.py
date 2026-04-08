"""
database/mongo_client.py
------------------------
Singleton MongoDB client used throughout the application.
Raises a clear error if MONGO_URI is missing.
"""

from __future__ import annotations

import streamlit as st
import certifi
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.server_api import ServerApi

from config import MONGO_URI, MONGO_DB_NAME


@st.cache_resource(show_spinner=False)
def get_mongo_client() -> MongoClient:
    """
    Return a cached PyMongo MongoClient instance.

    Uses Streamlit's cache_resource so the connection is reused
    across reruns without reconnecting on every page interaction.

    Raises
    ------
    ValueError
        If MONGO_URI is not set in the environment.
    """
    if not MONGO_URI:
        raise ValueError(
            "MongoDB URI not found. "
            "Please copy .env.example to .env and fill in your MONGO_URI."
        )
    return MongoClient(
        MONGO_URI,
        server_api=ServerApi('1'),
        tlsCAFile=certifi.where()
    )


def get_db() -> Database:
    """Return the application database handle."""
    client = get_mongo_client()
    return client[MONGO_DB_NAME]
