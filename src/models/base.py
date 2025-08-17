"""Base models and mixins for the AI therapist application."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class BaseEntity(TimestampMixin):
    """Base entity with ID and timestamps."""
    id: str = Field(default_factory=lambda: str(uuid4()))


class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None
    error_code: Optional[str] = None


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel):
    """Standard paginated response format."""
    items: list
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool
