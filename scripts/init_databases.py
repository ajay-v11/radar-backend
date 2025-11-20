#!/usr/bin/env python3
"""
Database initialization script.

Run this script to test connections and initialize ChromaDB collections.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import (
    test_connections,
    initialize_chroma_collections,
    close_connections
)
from utils.cache import get_cache_stats
from utils.vector_store import get_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and test database connections."""
    
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)
    print()
    
    # Test connections
    print("Testing database connections...")
    status = test_connections()
    
    print("\n📊 Connection Status:")
    print("-" * 60)
    
    # ChromaDB status
    if status["chromadb"]["connected"]:
        print("✅ ChromaDB: Connected")
    else:
        print(f"❌ ChromaDB: Failed - {status['chromadb']['error']}")
        print("   Make sure ChromaDB is running: docker-compose up -d")
    
    # Redis status
    if status["redis"]["connected"]:
        print("✅ Redis: Connected")
    else:
        print(f"❌ Redis: Failed - {status['redis']['error']}")
        print("   Make sure Redis is running: docker-compose up -d")
    
    print()
    
    # If both connected, initialize collections
    if status["chromadb"]["connected"] and status["redis"]["connected"]:
        print("Initializing ChromaDB collections...")
        try:
            companies_col, competitors_col = initialize_chroma_collections()
            print(f"✅ Initialized collection: {companies_col.name}")
            print(f"✅ Initialized collection: {competitors_col.name}")
            print()
            
            # Get vector store stats
            print("📈 Vector Store Statistics:")
            print("-" * 60)
            vector_store = get_vector_store()
            stats = vector_store.get_collection_stats()
            print(f"Companies stored: {stats.get('companies_count', 0)}")
            print(f"Competitors stored: {stats.get('competitors_count', 0)}")
            print()
            
            # Get cache stats
            print("💾 Redis Cache Statistics:")
            print("-" * 60)
            cache_stats = get_cache_stats()
            if cache_stats:
                print(f"Total keys: {cache_stats.get('total_keys', 0)}")
                print(f"Cache hits: {cache_stats.get('hits', 0)}")
                print(f"Cache misses: {cache_stats.get('misses', 0)}")
                print(f"Hit rate: {cache_stats.get('hit_rate', 0):.2f}%")
                print(f"Memory used: {cache_stats.get('memory_used', 'unknown')}")
            print()
            
            print("=" * 60)
            print("✅ All databases initialized successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error initializing collections: {e}")
            sys.exit(1)
    else:
        print("=" * 60)
        print("❌ Cannot initialize - fix connection errors first")
        print("=" * 60)
        sys.exit(1)
    
    # Cleanup
    close_connections()


if __name__ == "__main__":
    main()
