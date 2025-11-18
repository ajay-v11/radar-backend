"""
RAG Store for in-memory data storage.

This module provides an in-memory storage system for company profiles,
competitor data, and query templates. For V1, we use Python dictionaries
without external database dependencies.
"""

from typing import Dict, List, Optional
from models.schemas import CompanyProfile, CompetitorProfile


class RAGStore:
    """
    In-memory storage for company profiles, competitors, and query templates.
    
    This class provides a simple dictionary-based storage system for V1.
    Future versions can replace this with persistent storage (PostgreSQL, ChromaDB).
    """
    
    def __init__(self):
        """Initialize empty storage dictionaries."""
        self.companies: Dict[str, CompanyProfile] = {}
        self.competitors: Dict[str, List[CompetitorProfile]] = {}
        self.query_templates: Dict[str, List[str]] = {}
        self.initialize_templates()
    
    def store_company(self, profile: CompanyProfile) -> None:
        """
        Store or update a company profile.
        
        Args:
            profile: CompanyProfile object to store
        """
        self.companies[profile.name] = profile
    
    def get_company(self, name: str) -> Optional[CompanyProfile]:
        """
        Retrieve a company profile by name.
        
        Args:
            name: Company name to look up
            
        Returns:
            CompanyProfile if found, None otherwise
        """
        return self.companies.get(name)
    
    def store_competitors(self, company_name: str, competitors: List[CompetitorProfile]) -> None:
        """
        Store a list of competitors for a company.
        
        Args:
            company_name: Name of the company
            competitors: List of CompetitorProfile objects
        """
        self.competitors[company_name] = competitors
    
    def get_competitors(self, company_name: str) -> List[CompetitorProfile]:
        """
        Retrieve competitors for a company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            List of CompetitorProfile objects, empty list if none found
        """
        return self.competitors.get(company_name, [])
    
    def get_query_templates(self, industry: str) -> List[str]:
        """
        Retrieve query templates for a specific industry.
        
        Args:
            industry: Industry category (e.g., 'technology', 'retail')
            
        Returns:
            List of query template strings, empty list if industry not found
        """
        return self.query_templates.get(industry, [])
    
    def initialize_templates(self) -> None:
        """
        Load default query templates for all supported industries.
        
        Each industry has 25+ templates to ensure 20 unique queries can be generated.
        Templates use placeholders that can be customized with company-specific information.
        """
        self.query_templates = {
            "technology": [
                "What are the best software companies in 2024?",
                "Recommend top cloud computing providers",
                "Which companies offer the best SaaS solutions?",
                "Compare leading technology companies",
                "What are the most innovative tech startups?",
                "Best enterprise software solutions",
                "Top cybersecurity companies to consider",
                "Recommend AI and machine learning platforms",
                "Which companies provide the best developer tools?",
                "Leading data analytics software providers",
                "Best project management software companies",
                "Top CRM software solutions",
                "Recommend collaboration tools for remote teams",
                "Which companies offer the best API platforms?",
                "Leading cloud storage providers",
                "Best DevOps and CI/CD tools",
                "Top companies for business intelligence software",
                "Recommend e-commerce platform providers",
                "Which companies have the best mobile app development tools?",
                "Leading companies in automation software",
                "Best companies for database management systems",
                "Top IT infrastructure providers",
                "Recommend companies for network security solutions",
                "Which companies offer the best IoT platforms?",
                "Leading companies in quantum computing",
                "Best companies for blockchain technology solutions",
            ],
            "retail": [
                "What are the best online shopping platforms?",
                "Recommend top e-commerce retailers",
                "Which companies offer the best retail experience?",
                "Compare leading retail brands",
                "What are the most popular online stores?",
                "Best fashion retailers online",
                "Top home goods and furniture stores",
                "Recommend electronics retailers",
                "Which companies have the best customer service in retail?",
                "Leading grocery delivery services",
                "Best luxury retail brands",
                "Top discount retailers and marketplaces",
                "Recommend sustainable and eco-friendly retailers",
                "Which companies offer the best return policies?",
                "Leading retailers for sports and outdoor gear",
                "Best beauty and cosmetics retailers",
                "Top retailers for home improvement",
                "Recommend pet supply retailers",
                "Which companies have the best loyalty programs?",
                "Leading retailers for books and media",
                "Best retailers for baby and kids products",
                "Top automotive parts retailers",
                "Recommend office supply retailers",
                "Which companies offer same-day delivery?",
                "Leading retailers with subscription services",
                "Best retailers for seasonal and holiday shopping",
            ],
            "healthcare": [
                "What are the best healthcare providers?",
                "Recommend top telemedicine platforms",
                "Which companies offer the best health insurance?",
                "Compare leading healthcare technology companies",
                "What are the most innovative digital health startups?",
                "Best medical device companies",
                "Top pharmaceutical companies",
                "Recommend mental health and wellness platforms",
                "Which companies provide the best patient care?",
                "Leading companies in medical diagnostics",
                "Best health monitoring and wearable device companies",
                "Top companies for electronic health records",
                "Recommend companies for clinical trial management",
                "Which companies offer the best healthcare analytics?",
                "Leading companies in personalized medicine",
                "Best companies for medical imaging technology",
                "Top biotechnology companies",
                "Recommend companies for healthcare data security",
                "Which companies have the best patient engagement platforms?",
                "Leading companies in remote patient monitoring",
                "Best companies for healthcare AI solutions",
                "Top companies for medical research and development",
                "Recommend companies for hospital management systems",
                "Which companies offer the best pharmacy services?",
                "Leading companies in preventive healthcare",
                "Best companies for healthcare workforce management",
            ],
            "finance": [
                "What are the best financial services companies?",
                "Recommend top fintech startups",
                "Which companies offer the best banking services?",
                "Compare leading investment platforms",
                "What are the most trusted financial advisors?",
                "Best companies for personal finance management",
                "Top payment processing companies",
                "Recommend cryptocurrency and blockchain finance companies",
                "Which companies provide the best lending services?",
                "Leading companies in wealth management",
                "Best companies for business accounting software",
                "Top insurance companies",
                "Recommend companies for retirement planning",
                "Which companies offer the best credit cards?",
                "Leading companies in peer-to-peer lending",
                "Best companies for international money transfers",
                "Top companies for financial analytics",
                "Recommend companies for tax preparation services",
                "Which companies have the best mobile banking apps?",
                "Leading companies in robo-advisory services",
                "Best companies for small business loans",
                "Top companies for fraud detection and prevention",
                "Recommend companies for expense management",
                "Which companies offer the best trading platforms?",
                "Leading companies in regulatory compliance technology",
                "Best companies for financial education and literacy",
            ],
            "food_services": [
                "What are the best meal kit delivery services?",
                "Recommend top food delivery platforms",
                "Which companies offer healthy meal subscriptions?",
                "Compare leading meal prep services",
                "What are the most popular restaurant chains?",
                "Best companies for organic and sustainable food delivery",
                "Top grocery delivery services",
                "Recommend companies for diet-specific meal plans",
                "Which companies provide the best catering services?",
                "Leading companies in plant-based meal delivery",
                "Best companies for family meal kits",
                "Top companies for quick and easy dinner solutions",
                "Recommend companies for gourmet meal delivery",
                "Which companies offer the best value for meal kits?",
                "Leading companies in ready-to-eat meal delivery",
                "Best companies for international cuisine delivery",
                "Top companies for breakfast and brunch delivery",
                "Recommend companies for office lunch catering",
                "Which companies have the best variety in meal options?",
                "Leading companies in farm-to-table delivery",
                "Best companies for portion-controlled meals",
                "Top companies for specialty diet meals (keto, paleo, vegan)",
                "Recommend companies for meal planning and recipes",
                "Which companies offer the most flexible subscription plans?",
                "Leading companies in sustainable packaging for food delivery",
                "Best companies for fresh ingredient delivery",
            ],
            "other": [
                "What are the best companies in this industry?",
                "Recommend top service providers",
                "Which companies offer the best solutions?",
                "Compare leading companies",
                "What are the most innovative companies?",
                "Best companies for quality products",
                "Top companies with excellent customer service",
                "Recommend companies with competitive pricing",
                "Which companies have the best reputation?",
                "Leading companies in the market",
                "Best companies for reliability",
                "Top companies with sustainable practices",
                "Recommend companies with innovative approaches",
                "Which companies offer the best value?",
                "Leading companies with strong brand recognition",
                "Best companies for customer satisfaction",
                "Top companies with industry expertise",
                "Recommend companies with proven track records",
                "Which companies are market leaders?",
                "Leading companies with cutting-edge solutions",
                "Best companies for long-term partnerships",
                "Top companies with comprehensive offerings",
                "Recommend companies with excellent reviews",
                "Which companies have the best industry ratings?",
                "Leading companies with award-winning services",
                "Best companies for professional services",
            ],
        }


# Singleton instance for global access
_rag_store_instance: Optional[RAGStore] = None


def get_rag_store() -> RAGStore:
    """
    Get or create the singleton RAGStore instance.
    
    Returns:
        RAGStore: The global RAGStore instance
    """
    global _rag_store_instance
    if _rag_store_instance is None:
        _rag_store_instance = RAGStore()
    return _rag_store_instance
