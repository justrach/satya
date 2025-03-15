from satya import Model, Field
from typing import List, Optional, Literal
from datetime import datetime

class Address(Model):
    """User address information"""
    street: str = Field(min_length=1, description="Street address")
    city: str = Field(min_length=1, description="City name")
    state: str = Field(min_length=1, description="State or province")
    country: str = Field(min_length=2, description="Country name")
    postal_code: str = Field(pattern=r"^\d{5}(-\d{4})?$", description="Postal/ZIP code")

class Subscription(Model):
    """User subscription details"""
    plan: str = Field(enum=["free", "basic", "premium"], description="Subscription plan type")
    status: str = Field(enum=["active", "expired", "cancelled"], description="Current subscription status")
    start_date: datetime = Field(description="When the subscription started")
    end_date: Optional[datetime] = Field(required=False, description="When the subscription ends/ended")

class UserProfile(Model):
    user_id: str = Field(pattern=r"^usr_[a-zA-Z0-9]+$", description="Unique user ID")
    username: str = Field(min_length=3, max_length=50, description="Username")
    email: str = Field(email=True, description="Email address")
    full_name: str = Field(min_length=1, description="Full name")
    age: int = Field(ge=13, le=120, description="User age")
    address: Address = Field(description="User's address")
    subscription: Subscription = Field(description="Subscription information")
    created_at: datetime = Field(description="Account creation timestamp") 