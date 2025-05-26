from satya import StreamValidator, Model, Field
from typing import List, Dict, Optional, Union, Literal, Any, Tuple
from datetime import datetime, date, time
from enum import Enum
from uuid import UUID
from decimal import Decimal
import json

# Enums for validation
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"

class Protocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SFTP = "sftp"

# Basic validation models
class ContactInfo(Model):
    """Contact information with comprehensive validation"""
    email: str = Field(
        email=True,
        description="Valid email address"
    )
    phone: str = Field(
        pattern=r'^\+?1?\d{9,15}$',
        description="International phone number format"
    )
    website: str = Field(
        url=True,
        description="Website URL"
    )
    fax: Optional[str] = Field(
        pattern=r'^\+?1?\d{9,15}$',
        required=False,
        description="Fax number (optional)"
    )

class Address(Model):
    """Address with geographic validation"""
    street_address: str = Field(
        min_length=5,
        max_length=200,
        description="Street address"
    )
    apartment: Optional[str] = Field(
        max_length=50,
        required=False,
        description="Apartment/unit number"
    )
    city: str = Field(
        pattern=r'^[A-Za-z\s\-\'\.]+$',
        min_length=2,
        max_length=100,
        description="City name (letters, spaces, hyphens, apostrophes, dots only)"
    )
    state_province: str = Field(
        pattern=r'^[A-Za-z\s\-]+$',
        min_length=2,
        max_length=100,
        description="State or province"
    )
    postal_code: str = Field(
        pattern=r'^[A-Za-z0-9\s\-]{3,12}$',
        description="Postal/ZIP code"
    )
    country_code: str = Field(
        pattern=r'^[A-Z]{2}$',
        description="Two-letter ISO country code"
    )
    latitude: Optional[float] = Field(
        min_value=-90.0,
        max_value=90.0,
        required=False,
        description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        min_value=-180.0,
        max_value=180.0,
        required=False,
        description="Longitude coordinate"
    )

class SecurityCredentials(Model):
    """Security and authentication information"""
    username: str = Field(
        pattern=r'^[a-zA-Z0-9_\-\.]{3,50}$',
        min_length=3,
        max_length=50,
        description="Username (alphanumeric, underscore, hyphen, dot)"
    )
    password_hash: str = Field(
        pattern=r'^[a-fA-F0-9]{64}$',
        description="SHA-256 password hash (64 hex characters)"
    )
    salt: str = Field(
        pattern=r'^[a-fA-F0-9]{32}$',
        description="Password salt (32 hex characters)"
    )
    api_key: Optional[str] = Field(
        pattern=r'^[a-zA-Z0-9]{32,128}$',
        required=False,
        description="API key (32-128 alphanumeric characters)"
    )
    two_factor_enabled: bool = Field(
        description="Two-factor authentication status"
    )
    security_questions: List[str] = Field(
        min_items=2,
        max_items=5,
        description="Security questions (2-5 items)"
    )
    allowed_ip_ranges: List[str] = Field(
        min_items=0,
        max_items=10,
        description="Allowed IP ranges for access"
    )

class FinancialInfo(Model):
    """Financial and payment information"""
    account_number: str = Field(
        pattern=r'^\d{8,20}$',
        description="Bank account number (8-20 digits)"
    )
    routing_number: str = Field(
        pattern=r'^\d{9}$',
        description="Bank routing number (9 digits)"
    )
    credit_card: Optional[str] = Field(
        pattern=r'^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$',
        required=False,
        description="Credit card number (with optional separators)"
    )
    cvv: Optional[str] = Field(
        pattern=r'^\d{3,4}$',
        required=False,
        description="Credit card CVV (3-4 digits)"
    )
    currency: Currency = Field(
        description="Currency code"
    )
    balance: Decimal = Field(
        min_value=Decimal('0.00'),
        max_value=Decimal('999999999.99'),
        description="Account balance"
    )
    credit_limit: Optional[Decimal] = Field(
        min_value=Decimal('0.00'),
        required=False,
        description="Credit limit (optional)"
    )
    transaction_history: List[Dict[str, Any]] = Field(
        min_items=0,
        max_items=1000,
        description="Recent transaction history"
    )

class SystemConfiguration(Model):
    """System and technical configuration"""
    hostname: str = Field(
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$',
        min_length=1,
        max_length=253,
        description="Valid hostname"
    )
    ip_address: str = Field(
        pattern=r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        description="IPv4 address"
    )
    ipv6_address: Optional[str] = Field(
        pattern=r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        required=False,
        description="IPv6 address (optional)"
    )
    mac_address: str = Field(
        pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        description="MAC address"
    )
    port_number: int = Field(
        min_value=1,
        max_value=65535,
        description="Network port number"
    )
    protocol: Protocol = Field(
        description="Network protocol"
    )
    ssl_enabled: bool = Field(
        description="SSL/TLS encryption status"
    )
    timeout_seconds: int = Field(
        min_value=1,
        max_value=3600,
        description="Connection timeout in seconds"
    )
    max_connections: int = Field(
        min_value=1,
        max_value=10000,
        description="Maximum concurrent connections"
    )
    environment_variables: Dict[str, str] = Field(
        description="Environment configuration"
    )

class DocumentMetadata(Model):
    """Document and file metadata"""
    filename: str = Field(
        pattern=r'^[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+$',
        min_length=1,
        max_length=255,
        description="Valid filename with extension"
    )
    file_size_bytes: int = Field(
        min_value=0,
        max_value=10_737_418_240,  # 10GB
        description="File size in bytes"
    )
    mime_type: str = Field(
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*$',
        description="MIME type"
    )
    checksum_md5: str = Field(
        pattern=r'^[a-fA-F0-9]{32}$',
        description="MD5 checksum (32 hex characters)"
    )
    checksum_sha256: str = Field(
        pattern=r'^[a-fA-F0-9]{64}$',
        description="SHA-256 checksum (64 hex characters)"
    )
    created_at: datetime = Field(
        description="File creation timestamp"
    )
    modified_at: datetime = Field(
        description="Last modification timestamp"
    )
    version: str = Field(
        pattern=r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-]+)?$',
        description="Semantic version (e.g., 1.2.3 or 1.2.3-beta)"
    )
    tags: List[str] = Field(
        min_items=0,
        max_items=20,
        unique_items=True,
        description="Document tags (unique)"
    )
    permissions: Dict[str, List[str]] = Field(
        description="Access permissions by role"
    )

class PersonalIdentification(Model):
    """Personal identification and verification"""
    first_name: str = Field(
        pattern=r'^[A-Za-z\s\-\'\.]{1,50}$',
        min_length=1,
        max_length=50,
        description="First name (letters, spaces, hyphens, apostrophes, dots)"
    )
    middle_name: Optional[str] = Field(
        pattern=r'^[A-Za-z\s\-\'\.]{1,50}$',
        max_length=50,
        required=False,
        description="Middle name (optional)"
    )
    last_name: str = Field(
        pattern=r'^[A-Za-z\s\-\'\.]{1,50}$',
        min_length=1,
        max_length=50,
        description="Last name"
    )
    date_of_birth: date = Field(
        description="Date of birth"
    )
    social_security_number: Optional[str] = Field(
        pattern=r'^\d{3}-\d{2}-\d{4}$',
        required=False,
        description="SSN format: XXX-XX-XXXX"
    )
    passport_number: Optional[str] = Field(
        pattern=r'^[A-Z0-9]{6,12}$',
        required=False,
        description="Passport number (6-12 alphanumeric)"
    )
    driver_license: Optional[str] = Field(
        pattern=r'^[A-Z0-9\-]{8,20}$',
        required=False,
        description="Driver's license number"
    )
    nationality: str = Field(
        pattern=r'^[A-Z]{2}$',
        description="Two-letter nationality code"
    )
    gender: Literal["M", "F", "O", "N"] = Field(
        description="Gender: M(ale), F(emale), O(ther), N(ot specified)"
    )
    emergency_contacts: List[ContactInfo] = Field(
        min_items=1,
        max_items=3,
        description="Emergency contact information"
    )

class ProjectManagement(Model):
    """Project and task management"""
    project_id: UUID = Field(
        description="Unique project identifier"
    )
    project_name: str = Field(
        pattern=r'^[A-Za-z0-9\s\-_\.]{3,100}$',
        min_length=3,
        max_length=100,
        description="Project name"
    )
    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Project description"
    )
    priority: Priority = Field(
        description="Project priority level"
    )
    status: Status = Field(
        description="Current project status"
    )
    start_date: date = Field(
        description="Project start date"
    )
    end_date: Optional[date] = Field(
        required=False,
        description="Project end date (optional)"
    )
    budget: Decimal = Field(
        min_value=Decimal('0.00'),
        max_value=Decimal('10000000.00'),
        description="Project budget"
    )
    team_members: List[UUID] = Field(
        min_items=1,
        max_items=50,
        unique_items=True,
        description="Team member IDs (unique)"
    )
    milestones: List[Dict[str, Any]] = Field(
        min_items=0,
        max_items=20,
        description="Project milestones"
    )
    dependencies: List[UUID] = Field(
        min_items=0,
        max_items=10,
        unique_items=True,
        description="Dependent project IDs"
    )
    risk_assessment: Dict[str, Union[str, int, float]] = Field(
        description="Risk assessment data"
    )

class HealthcareRecord(Model):
    """Healthcare and medical information"""
    patient_id: UUID = Field(
        description="Unique patient identifier"
    )
    medical_record_number: str = Field(
        pattern=r'^MRN\d{8,12}$',
        description="Medical record number (MRN followed by 8-12 digits)"
    )
    blood_type: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] = Field(
        description="Blood type"
    )
    height_cm: float = Field(
        min_value=30.0,
        max_value=300.0,
        description="Height in centimeters"
    )
    weight_kg: float = Field(
        min_value=0.5,
        max_value=1000.0,
        description="Weight in kilograms"
    )
    allergies: List[str] = Field(
        min_items=0,
        max_items=50,
        description="Known allergies"
    )
    medications: List[Dict[str, Any]] = Field(
        min_items=0,
        max_items=100,
        description="Current medications"
    )
    medical_conditions: List[str] = Field(
        min_items=0,
        max_items=50,
        description="Medical conditions"
    )
    emergency_contact: ContactInfo = Field(
        description="Emergency contact information"
    )
    insurance_policy_number: str = Field(
        pattern=r'^[A-Z0-9\-]{8,20}$',
        description="Insurance policy number"
    )
    last_visit: datetime = Field(
        description="Last medical visit"
    )
    next_appointment: Optional[datetime] = Field(
        required=False,
        description="Next scheduled appointment"
    )

class ComprehensiveEntity(Model):
    """Ultra-comprehensive entity showcasing all Satya validation features"""
    
    # Basic identification
    entity_id: UUID = Field(
        description="Unique entity identifier"
    )
    entity_type: Literal["person", "organization", "system", "project"] = Field(
        description="Type of entity"
    )
    created_timestamp: datetime = Field(
        description="Entity creation timestamp"
    )
    last_updated: datetime = Field(
        description="Last update timestamp"
    )
    
    # Personal identification (deeply nested)
    personal_info: PersonalIdentification = Field(
        description="Personal identification information"
    )
    
    # Contact and address information
    primary_address: Address = Field(
        description="Primary address"
    )
    secondary_addresses: List[Address] = Field(
        min_items=0,
        max_items=5,
        description="Additional addresses"
    )
    contact_methods: List[ContactInfo] = Field(
        min_items=1,
        max_items=10,
        description="Contact information"
    )
    
    # Security and authentication
    security: SecurityCredentials = Field(
        description="Security credentials"
    )
    
    # Financial information
    financial_profiles: List[FinancialInfo] = Field(
        min_items=0,
        max_items=5,
        description="Financial accounts"
    )
    
    # System configuration
    system_configs: Dict[str, SystemConfiguration] = Field(
        description="System configurations by environment"
    )
    
    # Document management
    documents: List[DocumentMetadata] = Field(
        min_items=0,
        max_items=1000,
        description="Associated documents"
    )
    
    # Project management
    projects: List[ProjectManagement] = Field(
        min_items=0,
        max_items=100,
        description="Associated projects"
    )
    
    # Healthcare records (if applicable)
    healthcare_records: Optional[List[HealthcareRecord]] = Field(
        min_items=0,
        max_items=10,
        required=False,
        description="Healthcare information (optional)"
    )
    
    # Complex nested data structures
    nested_metadata: Dict[str, Dict[str, List[Dict[str, Any]]]] = Field(
        description="Deeply nested metadata structure"
    )
    
    # Arrays with complex validation
    priority_scores: List[float] = Field(
        min_items=1,
        max_items=10,
        description="Priority scores (1-10 items)"
    )
    
    # Unique identifiers list
    related_entity_ids: List[UUID] = Field(
        min_items=0,
        max_items=100,
        unique_items=True,
        description="Related entity IDs (unique)"
    )
    
    # Complex validation combinations
    verification_codes: List[str] = Field(
        min_items=0,
        max_items=5,
        description="Verification codes"
    )
    
    # Enum arrays
    status_history: List[Status] = Field(
        min_items=1,
        max_items=50,
        description="Status change history"
    )
    
    # Optional complex nested structure
    advanced_settings: Optional[Dict[str, Union[str, int, float, bool, List[Any]]]] = Field(
        required=False,
        description="Advanced configuration settings"
    )
    
    # Tuple-like structures (represented as lists with validation)
    coordinates_3d: List[float] = Field(
        min_items=3,
        max_items=3,
        description="3D coordinates [x, y, z]"
    )
    
    # Color codes
    theme_colors: List[str] = Field(
        min_items=1,
        max_items=10,
        description="Theme color hex codes"
    )
    
    # Version tracking
    schema_version: str = Field(
        pattern=r'^\d+\.\d+\.\d+$',
        description="Schema version"
    )
    
    # Compliance and regulatory
    compliance_flags: Dict[str, bool] = Field(
        description="Compliance status flags"
    )
    
    # Performance metrics
    performance_metrics: Dict[str, float] = Field(
        description="Performance measurement data"
    )

def main():
    """Demonstrate the comprehensive validation capabilities"""
    print("🚀 Satya Comprehensive Validation Example")
    print("=" * 50)
    
    # Print the JSON Schema
    print("\nJSON Schema for ComprehensiveEntity:")
    schema = ComprehensiveEntity.json_schema()
    print(json.dumps(schema, indent=2)[:2000] + "..." if len(json.dumps(schema, indent=2)) > 2000 else json.dumps(schema, indent=2))
    
    # Create a comprehensive test entity
    test_entity = {
        "entity_id": "123e4567-e89b-12d3-a456-426614174000",
        "entity_type": "person",
        "created_timestamp": "2024-01-01T12:00:00Z",
        "last_updated": "2024-01-15T14:30:00Z",
        "personal_info": {
            "first_name": "John",
            "middle_name": "Michael",
            "last_name": "Doe",
            "date_of_birth": "1990-05-15",
            "social_security_number": "123-45-6789",
            "passport_number": "AB1234567",
            "driver_license": "DL123456789",
            "nationality": "US",
            "gender": "M",
            "emergency_contacts": [
                {
                    "email": "emergency@example.com",
                    "phone": "+1234567890",
                    "website": "https://emergency.example.com"
                }
            ]
        },
        "primary_address": {
            "street_address": "123 Main Street",
            "apartment": "Apt 4B",
            "city": "New York",
            "state_province": "New York",
            "postal_code": "10001",
            "country_code": "US",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        "secondary_addresses": [],
        "contact_methods": [
            {
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "website": "https://johndoe.example.com"
            }
        ],
        "security": {
            "username": "johndoe123",
            "password_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            "salt": "5d41402abc4b2a76b9719d911017c592",
            "api_key": "abcd1234efgh5678ijkl9012mnop3456",
            "two_factor_enabled": True,
            "security_questions": ["What is your mother's maiden name?", "What was your first pet's name?"],
            "allowed_ip_ranges": ["192.168.1.0/24", "10.0.0.0/8"]
        },
        "financial_profiles": [
            {
                "account_number": "1234567890123456",
                "routing_number": "123456789",
                "credit_card": "4111-1111-1111-1111",
                "cvv": "123",
                "currency": "USD",
                "balance": "1000.50",
                "credit_limit": "5000.00",
                "transaction_history": []
            }
        ],
        "system_configs": {
            "production": {
                "hostname": "prod.example.com",
                "ip_address": "192.168.1.100",
                "ipv6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                "mac_address": "00:1B:44:11:3A:B7",
                "port_number": 443,
                "protocol": "https",
                "ssl_enabled": True,
                "timeout_seconds": 30,
                "max_connections": 1000,
                "environment_variables": {"ENV": "production", "DEBUG": "false"}
            }
        },
        "documents": [
            {
                "filename": "document.pdf",
                "file_size_bytes": 1048576,
                "mime_type": "application/pdf",
                "checksum_md5": "5d41402abc4b2a76b9719d911017c592",
                "checksum_sha256": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "created_at": "2024-01-01T12:00:00Z",
                "modified_at": "2024-01-01T12:00:00Z",
                "version": "1.0.0",
                "tags": ["important", "legal"],
                "permissions": {"admin": ["read", "write"], "user": ["read"]}
            }
        ],
        "projects": [
            {
                "project_id": "987fcdeb-51a2-43d1-b456-426614174000",
                "project_name": "Sample Project",
                "description": "This is a comprehensive sample project for demonstration purposes.",
                "priority": "high",
                "status": "active",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "budget": "100000.00",
                "team_members": ["123e4567-e89b-12d3-a456-426614174001"],
                "milestones": [{"name": "Phase 1", "date": "2024-06-01"}],
                "dependencies": [],
                "risk_assessment": {"overall_risk": "medium", "score": 5.5}
            }
        ],
        "healthcare_records": [
            {
                "patient_id": "456e7890-e89b-12d3-a456-426614174000",
                "medical_record_number": "MRN123456789",
                "blood_type": "O+",
                "height_cm": 175.5,
                "weight_kg": 70.2,
                "allergies": ["peanuts", "shellfish"],
                "medications": [{"name": "Aspirin", "dosage": "81mg", "frequency": "daily"}],
                "medical_conditions": ["hypertension"],
                "emergency_contact": {
                    "email": "emergency@example.com",
                    "phone": "+1234567890",
                    "website": "https://emergency.example.com"
                },
                "insurance_policy_number": "INS123456789",
                "last_visit": "2024-01-01T10:00:00Z",
                "next_appointment": "2024-02-01T10:00:00Z"
            }
        ],
        "nested_metadata": {
            "level1": {
                "level2": [
                    {"level3": {"key": "value"}},
                    {"level3": {"another": "data"}}
                ]
            }
        },
        "priority_scores": [8.5, 7.2, 9.1],
        "related_entity_ids": ["111e1111-e89b-12d3-a456-426614174000"],
        "verification_codes": ["ABC123", "DEF456"],
        "status_history": ["pending", "active"],
        "advanced_settings": {
            "feature_flags": {"new_ui": True, "beta_features": False},
            "thresholds": {"warning": 80, "critical": 95}
        },
        "coordinates_3d": [10.5, 20.3, 30.7],
        "theme_colors": ["#FF5733", "#33FF57", "#3357FF"],
        "schema_version": "2.1.0",
        "compliance_flags": {"gdpr": True, "hipaa": True, "sox": False},
        "performance_metrics": {"response_time": 0.25, "throughput": 1000.5, "error_rate": 0.01}
    }
    
    # Create validator and validate
    validator = ComprehensiveEntity.validator()
    
    print(f"\n🔍 Validating comprehensive entity with {len(str(test_entity))} characters of data...")
    
    result = validator.validate(test_entity)
    if result.is_valid:
        print("✅ Comprehensive validation passed!")
        print(f"📊 Validated entity with {len(test_entity)} top-level fields")
        print("🎯 All nested validations successful:")
        print("   • Personal identification with regex patterns")
        print("   • Address with geographic coordinates")
        print("   • Security credentials with hash validation")
        print("   • Financial information with decimal precision")
        print("   • System configuration with network validation")
        print("   • Document metadata with checksums")
        print("   • Project management with UUID references")
        print("   • Healthcare records with medical constraints")
        print("   • Deep nested structures (4+ levels)")
        print("   • Complex array validations")
        print("   • Enum and literal type checking")
        print("   • Optional field handling")
        print("   • Unique item constraints")
        print("   • Range and pattern validations")
    else:
        print("❌ Validation failed!")
        for error in result.errors:
            print(f"   Error in {error.field}: {error.message}")

if __name__ == "__main__":
    main() 