"""
ChromaDB vector store utilities for company embeddings and semantic search.
"""

from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from config.database import get_chroma_client, initialize_chroma_collections
from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Wrapper for ChromaDB operations on company and competitor data.
    """
    
    def __init__(self):
        """Initialize ChromaDB collections."""
        self.client = get_chroma_client()
        self.companies_collection, self.competitors_collection = initialize_chroma_collections()
    
    def store_company(
        self,
        company_name: str,
        company_url: str,
        scraped_content: str,
        industry: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store company information with embeddings.
        
        Args:
            company_name: Company name
            company_url: Company website URL
            scraped_content: Scraped website content for embedding
            industry: Detected industry
            description: Company description
            metadata: Additional metadata to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            # Prepare document (truncate to avoid token limits)
            document = scraped_content[:2000] if scraped_content else description or ""
            
            # Prepare metadata
            meta = {
                "company_name": company_name,
                "company_url": company_url,
                "industry": industry,
                "description": description or "",
                "stored_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Generate unique ID
            doc_id = f"company_{company_name.lower().replace(' ', '_')}"
            
            # Store in ChromaDB
            self.companies_collection.upsert(
                documents=[document],
                metadatas=[meta],
                ids=[doc_id]
            )
            
            logger.info(f"Stored company in vector store: {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing company in vector store: {e}")
            return False
    
    def find_similar_companies(
        self,
        query_text: str,
        industry: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find companies similar to the query text.
        
        Args:
            query_text: Text to search for (e.g., scraped content)
            industry: Filter by industry (optional)
            n_results: Number of results to return
            
        Returns:
            List of similar companies with metadata
        """
        try:
            # Build where filter for industry
            where_filter = {"industry": industry} if industry else None
            
            # Query ChromaDB
            results = self.companies_collection.query(
                query_texts=[query_text[:2000]],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            similar_companies = []
            if results and results["metadatas"]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    similar_companies.append({
                        "company_name": metadata.get("company_name"),
                        "company_url": metadata.get("company_url"),
                        "industry": metadata.get("industry"),
                        "description": metadata.get("description"),
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    })
            
            logger.info(f"Found {len(similar_companies)} similar companies")
            return similar_companies
            
        except Exception as e:
            logger.error(f"Error finding similar companies: {e}")
            return []
    
    def get_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by name.
        
        Args:
            company_name: Company name to retrieve
            
        Returns:
            Company data or None if not found
        """
        try:
            doc_id = f"company_{company_name.lower().replace(' ', '_')}"
            
            result = self.companies_collection.get(
                ids=[doc_id],
                include=["metadatas", "documents"]
            )
            
            if result and result["metadatas"]:
                return {
                    "metadata": result["metadatas"][0],
                    "content": result["documents"][0] if result.get("documents") else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting company: {e}")
            return None
    
    def store_competitors(
        self,
        company_name: str,
        competitors: List[str],
        industry: str
    ) -> bool:
        """
        Store competitor relationships.
        
        Args:
            company_name: Main company name
            competitors: List of competitor names
            industry: Industry category
            
        Returns:
            bool: True if stored successfully
        """
        try:
            # Store each competitor
            for competitor in competitors:
                doc_id = f"competitor_{company_name.lower().replace(' ', '_')}_{competitor.lower().replace(' ', '_')}"
                
                metadata = {
                    "company_name": company_name,
                    "competitor_name": competitor,
                    "industry": industry,
                    "stored_at": datetime.now().isoformat()
                }
                
                # Use competitor name as document for embedding
                self.competitors_collection.upsert(
                    documents=[competitor],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
            
            logger.info(f"Stored {len(competitors)} competitors for {company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing competitors: {e}")
            return False
    
    def get_competitors(self, company_name: str) -> List[str]:
        """
        Get competitors for a company.
        
        Args:
            company_name: Company name
            
        Returns:
            List of competitor names
        """
        try:
            results = self.competitors_collection.get(
                where={"company_name": company_name},
                include=["metadatas"]
            )
            
            if results and results["metadatas"]:
                return [meta["competitor_name"] for meta in results["metadatas"]]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting competitors: {e}")
            return []
    
    def find_companies_by_industry(self, industry: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all companies in a specific industry.
        
        Args:
            industry: Industry category
            limit: Maximum number of results
            
        Returns:
            List of companies in the industry
        """
        try:
            results = self.companies_collection.get(
                where={"industry": industry},
                limit=limit,
                include=["metadatas"]
            )
            
            companies = []
            if results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    companies.append({
                        "company_name": metadata.get("company_name"),
                        "company_url": metadata.get("company_url"),
                        "industry": metadata.get("industry"),
                        "description": metadata.get("description")
                    })
            
            return companies
            
        except Exception as e:
            logger.error(f"Error finding companies by industry: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored data.
        
        Returns:
            dict: Statistics including counts and collection info
        """
        try:
            companies_count = self.companies_collection.count()
            competitors_count = self.competitors_collection.count()
            
            return {
                "companies_count": companies_count,
                "competitors_count": competitors_count,
                "collections": {
                    "companies": settings.CHROMA_COLLECTION_COMPANIES,
                    "competitors": settings.CHROMA_COLLECTION_COMPETITORS
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the singleton VectorStore instance.
    
    Returns:
        VectorStore: The global VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
