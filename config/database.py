"""
Database connection managers for ChromaDB and Redis.

This module provides singleton instances and connection management
for ChromaDB (vector store) and Redis (cache).
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
import redis
from redis import ConnectionPool
from typing import Optional
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


# Singleton instances
_chroma_client: Optional[chromadb.HttpClient] = None
_redis_client: Optional[redis.Redis] = None
_redis_pool: Optional[ConnectionPool] = None


def get_chroma_client() -> chromadb.HttpClient:
    """
    Get or create ChromaDB client singleton.
    
    Returns:
        chromadb.HttpClient: Connected ChromaDB client
        
    Raises:
        ConnectionError: If unable to connect to ChromaDB
    """
    global _chroma_client
    
    if _chroma_client is None:
        try:
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Test connection
            _chroma_client.heartbeat()
            logger.info(f"Connected to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise ConnectionError(f"ChromaDB connection failed: {e}")
    
    return _chroma_client


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client singleton with connection pooling.
    
    Returns:
        redis.Redis: Connected Redis client
        
    Raises:
        ConnectionError: If unable to connect to Redis
    """
    global _redis_client, _redis_pool
    
    if _redis_client is None:
        try:
            # Create connection pool
            _redis_pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,  # Automatically decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create client from pool
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}")
    
    return _redis_client


def initialize_chroma_collections():
    """
    Initialize ChromaDB collections for companies and competitors.
    Creates collections if they don't exist.
    
    Returns:
        tuple: (companies_collection, competitors_collection)
    """
    client = get_chroma_client()
    
    try:
        # Get or create companies collection
        companies_collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_COMPANIES,
            metadata={
                "description": "Company profiles with website content embeddings",
                "hnsw:space": "cosine"  # Use cosine similarity
            }
        )
        logger.info(f"Initialized collection: {settings.CHROMA_COLLECTION_COMPANIES}")
        
        # Get or create competitors collection
        competitors_collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_COMPETITORS,
            metadata={
                "description": "Competitor information and relationships",
                "hnsw:space": "cosine"
            }
        )
        logger.info(f"Initialized collection: {settings.CHROMA_COLLECTION_COMPETITORS}")
        
        return companies_collection, competitors_collection
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB collections: {e}")
        raise


def test_connections() -> dict:
    """
    Test connections to ChromaDB and Redis.
    
    Returns:
        dict: Status of each connection
    """
    status = {
        "chromadb": {"connected": False, "error": None},
        "redis": {"connected": False, "error": None}
    }
    
    # Test ChromaDB
    try:
        client = get_chroma_client()
        client.heartbeat()
        status["chromadb"]["connected"] = True
    except Exception as e:
        status["chromadb"]["error"] = str(e)
    
    # Test Redis
    try:
        client = get_redis_client()
        client.ping()
        status["redis"]["connected"] = True
    except Exception as e:
        status["redis"]["error"] = str(e)
    
    return status


def close_connections():
    """
    Close all database connections gracefully.
    Call this on application shutdown.
    """
    global _chroma_client, _redis_client, _redis_pool
    
    # Close Redis connection
    if _redis_client is not None:
        try:
            _redis_client.close()
            logger.info("Closed Redis connection")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
    
    # Close Redis connection pool
    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
            logger.info("Closed Redis connection pool")
        except Exception as e:
            logger.error(f"Error closing Redis pool: {e}")
        finally:
            _redis_pool = None
    
    # ChromaDB HTTP client doesn't need explicit closing
    _chroma_client = None
    logger.info("Reset ChromaDB client")
