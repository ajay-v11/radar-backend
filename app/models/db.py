from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    """Job type enum"""
    COMPANY_ANALYSIS = "company_analysis"
    VISIBILITY_ANALYSIS = "visibility_analysis"


class User(SQLModel, table=True):
    """User model for authentication and quota management"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    google_id: str = Field(unique=True, index=True, nullable=False)
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    quota_limit: int = Field(default=10)  # Default 10 analyses per user
    quota_used: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    jobs: List["Job"] = Relationship(back_populates="user")


class Job(SQLModel, table=True):
    """Job model for tracking analysis jobs"""
    __tablename__ = "jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    idempotency_key: str = Field(unique=True, index=True, nullable=False)
    type: JobType = Field(nullable=False, index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    
    # Job parameters (stored as JSON)
    params: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    # Job results (stored as JSON)
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Error information
    error: Optional[str] = None
    
    # Queue management
    queue_position: Optional[int] = None
    
    # Thread ID for SSE streaming
    thread_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="jobs")
    events: List["JobEvent"] = Relationship(back_populates="job", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class JobEvent(SQLModel, table=True):
    """Job event model for tracking job progress"""
    __tablename__ = "job_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True, nullable=False)
    step: str = Field(nullable=False)  # e.g., "scraping", "analysis", "query_generation"
    status: str = Field(nullable=False)  # e.g., "started", "completed", "failed"
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    job: Optional[Job] = Relationship(back_populates="events")


class RateLimit(SQLModel, table=True):
    """Rate limit tracking (optional - for advanced rate limiting)"""
    __tablename__ = "rate_limits"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    endpoint: str = Field(index=True, nullable=False)
    count: int = Field(default=0)
    window_start: datetime = Field(default_factory=datetime.utcnow, index=True)
