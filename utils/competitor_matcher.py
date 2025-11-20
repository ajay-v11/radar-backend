"""
Semantic competitor matching using embeddings.

This module provides RAG-based competitor detection in AI model responses
using ChromaDB for vector similarity search.
"""

from typing import List, Dict, Optional, Tuple
import logging
from openai import OpenAI

from config.settings import settings
from config.database import get_chroma_client, initialize_chroma_collections

logger = logging.getLogger(__name__)


class CompetitorMatcher:
    """
    Semantic competitor matching using vector embeddings.
    """
    
    def __init__(self):
        """Initialize ChromaDB and OpenAI client."""
        self.chroma_client = get_chroma_client()
        _, self.competitors_collection = initialize_chroma_collections()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.similarity_threshold = 0.70  # Lowered for better recall
    
    def store_competitors(
        self,
        company_name: str,
        competitors: List[str],
        industry: str,
        descriptions: Optional[Dict[str, str]] = None,
        metadata_extra: Optional[Dict[str, Dict[str, str]]] = None
    ) -> bool:
        """
        Store competitors with rich embeddings for semantic search.
        
        Args:
            company_name: Main company name
            competitors: List of competitor names
            industry: Industry category
            descriptions: Optional dict mapping competitor names to descriptions
            metadata_extra: Optional dict with additional metadata per competitor
                           e.g., {"Nike": {"products": "shoes, apparel", "positioning": "premium"}}
            
        Returns:
            bool: True if stored successfully
        """
        if not competitors:
            return True
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for competitor in competitors:
                # Build rich embedding document with structured context
                doc_parts = [competitor]
                
                # Add description if available
                description = descriptions.get(competitor, "") if descriptions else ""
                if description:
                    doc_parts.append(description)
                
                # Add extra metadata for richer embeddings
                if metadata_extra and competitor in metadata_extra:
                    extra = metadata_extra[competitor]
                    if extra.get("products"):
                        doc_parts.append(f"Products: {extra['products']}")
                    if extra.get("positioning"):
                        doc_parts.append(f"Known for: {extra['positioning']}")
                    if extra.get("keywords"):
                        doc_parts.append(f"Keywords: {extra['keywords']}")
                
                # Create focused embedding document
                document = " - ".join(doc_parts)
                
                doc_id = f"comp_{company_name.lower().replace(' ', '_')}_{competitor.lower().replace(' ', '_')}"
                
                # Store structured metadata separately
                metadata = {
                    "company_name": company_name,
                    "competitor_name": competitor,
                    "industry": industry,
                    "description": description,
                    **(metadata_extra.get(competitor, {}) if metadata_extra else {})
                }
                
                documents.append(document)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            # Store with embeddings
            self.competitors_collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Stored {len(competitors)} competitors for {company_name} with rich embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error storing competitors: {e}")
            return False
    
    def find_competitor_mentions(
        self,
        company_name: str,
        text: str,
        top_k: int = 5
    ) -> List[Dict[str, any]]:
        """
        Find competitor mentions in text using semantic search.
        
        Args:
            company_name: Company whose competitors to search for
            text: Text to search (AI model response)
            top_k: Number of top matches to return
            
        Returns:
            List of matches with competitor name, similarity score, and context
        """
        try:
            # Query ChromaDB with the text
            results = self.competitors_collection.query(
                query_texts=[text[:1000]],  # Limit text length
                n_results=top_k,
                where={"company_name": company_name}
            )
            
            matches = []
            if results and results["metadatas"]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    # Calculate similarity (ChromaDB returns distances, convert to similarity)
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    # Only include if above threshold
                    if similarity >= self.similarity_threshold:
                        matches.append({
                            "competitor_name": metadata["competitor_name"],
                            "similarity": similarity,
                            "industry": metadata.get("industry"),
                            "matched": True
                        })
            
            return matches
            
        except Exception as e:
            logger.error(f"Error finding competitor mentions: {e}")
            return []
    
    def batch_find_mentions(
        self,
        company_name: str,
        texts: List[str]
    ) -> Dict[int, List[Dict]]:
        """
        Find competitor mentions across multiple texts.
        
        Args:
            company_name: Company whose competitors to search for
            texts: List of texts to search
            
        Returns:
            Dict mapping text index to list of matches
        """
        results = {}
        for i, text in enumerate(texts):
            matches = self.find_competitor_mentions(company_name, text)
            if matches:
                results[i] = matches
        
        return results
    
    def get_competitors_for_company(self, company_name: str) -> List[str]:
        """
        Get all stored competitors for a company.
        
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
    
    def analyze_response_for_mentions(
        self,
        company_name: str,
        response: str,
        competitors: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Analyze a single response for competitor mentions.
        Combines exact string matching with semantic search for best accuracy.
        
        Args:
            company_name: Company name
            response: AI model response text
            competitors: List of known competitors
            
        Returns:
            Tuple of (has_mention, list_of_mentioned_competitors)
        """
        mentioned = []
        mentioned_set = set()  # Track unique mentions
        
        # 1. Exact string matching (fast, high precision)
        response_lower = response.lower()
        for competitor in competitors:
            if competitor.lower() in response_lower:
                if competitor not in mentioned_set:
                    mentioned.append(competitor)
                    mentioned_set.add(competitor)
        
        # 2. Semantic matching (catches variations, good recall)
        try:
            semantic_matches = self.find_competitor_mentions(company_name, response)
            for match in semantic_matches:
                comp_name = match["competitor_name"]
                if comp_name not in mentioned_set:
                    mentioned.append(comp_name)
                    mentioned_set.add(comp_name)
        except Exception as e:
            logger.debug(f"Semantic matching failed: {e}")
        
        return len(mentioned) > 0, mentioned


# Singleton instance
_competitor_matcher_instance: Optional[CompetitorMatcher] = None


def get_competitor_matcher() -> CompetitorMatcher:
    """
    Get or create the singleton CompetitorMatcher instance.
    
    Returns:
        CompetitorMatcher: The global CompetitorMatcher instance
    """
    global _competitor_matcher_instance
    if _competitor_matcher_instance is None:
        _competitor_matcher_instance = CompetitorMatcher()
    return _competitor_matcher_instance
