from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str = Field(unique=True, index=True)
    description: Optional[str] = None
    industry: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships can be added here
    # competitors: List["Competitor"] = Relationship(back_populates="company")

class Competitor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
