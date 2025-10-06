"""
Fixed Income Securities Index Validation Example

This example demonstrates using Satya to validate a synthetic fixed income
security index containing bond data. It showcases:
- Complex model validation with nested structures
- String pattern validation (ISIN format)
- Numeric constraints (coupon rates, yields, prices)
- Enum validation (credit ratings, currencies)
- Date format validation
- Batch processing performance for large datasets
"""

from satya import Model, Field, StringValidator, NumberValidator
from typing import Optional, List
from datetime import datetime, timedelta
import random
import time

# ============================================================================
# Model Definitions
# ============================================================================

class Bond(Model):
    """Fixed Income Security (Bond) Model"""
    
    # Identifiers
    isin: str = Field(
        description="International Securities Identification Number",
        pattern=r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$',  # Standard ISIN format
        min_length=12,
        max_length=12
    )
    cusip: Optional[str] = Field(
        default=None,
        description="Committee on Uniform Securities Identification Procedures number",
        pattern=r'^[0-9]{3}[0-9A-Z]{5}[0-9]$',
        min_length=9,
        max_length=9
    )
    
    # Issuer Information
    issuer_name: str = Field(
        description="Name of the bond issuer",
        min_length=2,
        max_length=200
    )
    issuer_type: str = Field(
        enum=["Government", "Corporate", "Municipal", "Agency"],
        description="Type of issuer"
    )
    
    # Bond Characteristics
    face_value: float = Field(
        min_value=100.0,
        max_value=1000000000.0,
        description="Face/par value of the bond"
    )
    currency: str = Field(
        enum=["USD", "EUR", "GBP", "JPY", "CHF"],
        description="Currency denomination"
    )
    
    # Pricing and Yield
    current_price: float = Field(
        min_value=0.01,
        max_value=200.0,  # As percentage of face value
        description="Current market price as % of face value"
    )
    coupon_rate: float = Field(
        min_value=0.0,
        max_value=20.0,
        description="Annual coupon rate as percentage"
    )
    coupon_frequency: str = Field(
        enum=["Annual", "Semi-Annual", "Quarterly", "Monthly"],
        description="Frequency of coupon payments"
    )
    
    # Risk Metrics
    credit_rating: str = Field(
        enum=[
            "AAA", "AA+", "AA", "AA-",
            "A+", "A", "A-",
            "BBB+", "BBB", "BBB-",
            "BB+", "BB", "BB-",
            "B+", "B", "B-",
            "CCC+", "CCC", "CCC-",
            "CC", "C", "D"
        ],
        description="Credit rating (S&P style)"
    )
    yield_to_maturity: float = Field(
        min_value=-2.0,  # Allow negative yields (e.g., some European bonds)
        max_value=30.0,
        description="Yield to maturity as percentage"
    )
    duration: float = Field(
        min_value=0.01,
        max_value=30.0,
        description="Modified duration in years"
    )
    convexity: Optional[float] = Field(
        default=None,
        min_value=0.0,
        max_value=1000.0,
        description="Bond convexity"
    )
    
    # Dates
    issue_date: str = Field(
        description="Bond issue date (ISO format: YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    maturity_date: str = Field(
        description="Bond maturity date (ISO format: YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    # Optional Fields
    callable: bool = Field(
        default=False,
        description="Whether the bond is callable"
    )
    call_date: Optional[str] = Field(
        default=None,
        description="Call date if callable (ISO format: YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )


class BondIndex(Model):
    """Fixed Income Security Index containing multiple bonds"""
    
    index_name: str = Field(
        description="Name of the bond index",
        min_length=3,
        max_length=100
    )
    index_type: str = Field(
        enum=["Government", "Corporate", "Municipal", "Aggregate"],
        description="Type of index"
    )
    base_currency: str = Field(
        enum=["USD", "EUR", "GBP", "JPY", "CHF"],
        description="Base currency for index calculations"
    )
    total_market_value: float = Field(
        min_value=0.0,
        description="Total market value of all securities in the index"
    )
    average_duration: float = Field(
        min_value=0.0,
        max_value=30.0,
        description="Weighted average duration"
    )
    average_yield: float = Field(
        min_value=-2.0,
        max_value=30.0,
        description="Weighted average yield to maturity"
    )
    securities: List[Bond] = Field(
        description="List of bonds in the index",
        min_items=1
    )


# ============================================================================
# Synthetic Data Generation
# ============================================================================

def generate_random_isin(country_code: str = "US") -> str:
    """Generate a random ISIN number"""
    alphanumeric = [random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(9)]
    check_digit = random.randint(0, 9)
    return f"{country_code}{''.join(alphanumeric)}{check_digit}"


def generate_random_cusip() -> str:
    """Generate a random CUSIP number"""
    first_three = ''.join([str(random.randint(0, 9)) for _ in range(3)])
    middle_five = ''.join([random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5)])
    check_digit = random.randint(0, 9)
    return f"{first_three}{middle_five}{check_digit}"


def generate_random_date(start_year: int, end_year: int) -> str:
    """Generate a random date in ISO format"""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Simplified to avoid month/day validation
    return f"{year:04d}-{month:02d}-{day:02d}"


def generate_synthetic_bond(index: int) -> dict:
    """Generate synthetic bond data"""
    issuer_types = ["Government", "Corporate", "Municipal", "Agency"]
    issuer_type = random.choice(issuer_types)
    
    # Generate issuer name based on type
    if issuer_type == "Government":
        issuers = ["US Treasury", "German Bund", "UK Gilt", "Japanese JGB", "French OAT"]
    elif issuer_type == "Corporate":
        issuers = ["Apple Inc", "Microsoft Corp", "Goldman Sachs", "JPMorgan Chase", "ExxonMobil"]
    elif issuer_type == "Municipal":
        issuers = ["California State", "New York City", "Texas Municipal", "Florida Bond"]
    else:
        issuers = ["Fannie Mae", "Freddie Mac", "Ginnie Mae"]
    
    issuer_name = random.choice(issuers)
    
    # Credit ratings by issuer type
    if issuer_type == "Government":
        ratings = ["AAA", "AA+", "AA", "AA-", "A+", "A"]
    elif issuer_type == "Corporate":
        ratings = ["AAA", "AA", "A+", "A", "A-", "BBB+", "BBB", "BBB-"]
    elif issuer_type == "Municipal":
        ratings = ["AA", "AA-", "A+", "A", "A-", "BBB+", "BBB"]
    else:
        ratings = ["AAA", "AA+", "AA"]
    
    credit_rating = random.choice(ratings)
    
    # Generate dates
    issue_year = random.randint(2015, 2023)
    maturity_years = random.randint(2, 30)
    issue_date = generate_random_date(issue_year, issue_year)
    maturity_date = generate_random_date(issue_year + maturity_years, issue_year + maturity_years)
    
    # Coupon and yield based on credit rating and maturity
    base_rate = 2.0 + random.uniform(-1.0, 3.0)
    rating_spread = {"AAA": 0.0, "AA+": 0.2, "AA": 0.3, "AA-": 0.4, "A+": 0.5, 
                     "A": 0.6, "A-": 0.7, "BBB+": 1.0, "BBB": 1.2, "BBB-": 1.5}
    spread = rating_spread.get(credit_rating, 2.0)
    
    coupon_rate = round(base_rate + spread, 2)
    yield_to_maturity = round(coupon_rate + random.uniform(-0.5, 1.0), 2)
    
    # Price based on yield (simplified)
    price = round(100.0 + random.uniform(-10.0, 10.0), 2)
    
    # Duration roughly related to maturity
    duration = round(maturity_years * random.uniform(0.6, 0.9), 2)
    
    callable = random.random() < 0.3  # 30% chance of being callable
    
    return {
        "isin": generate_random_isin(),
        "cusip": generate_random_cusip() if random.random() < 0.8 else None,
        "issuer_name": issuer_name,
        "issuer_type": issuer_type,
        "face_value": random.choice([1000.0, 5000.0, 10000.0, 100000.0]),
        "currency": random.choice(["USD", "EUR", "GBP"]),
        "current_price": price,
        "coupon_rate": coupon_rate,
        "coupon_frequency": random.choice(["Annual", "Semi-Annual", "Quarterly"]),
        "credit_rating": credit_rating,
        "yield_to_maturity": yield_to_maturity,
        "duration": duration,
        "convexity": round(random.uniform(10.0, 200.0), 2) if random.random() < 0.7 else None,
        "issue_date": issue_date,
        "maturity_date": maturity_date,
        "callable": callable,
        "call_date": generate_random_date(issue_year + 1, issue_year + maturity_years - 1) if callable else None
    }


def generate_synthetic_index(name: str, index_type: str, num_securities: int) -> dict:
    """Generate a synthetic bond index with multiple securities"""
    securities = [generate_synthetic_bond(i) for i in range(num_securities)]
    
    # Calculate index metrics
    total_market_value = sum(s["face_value"] * s["current_price"] / 100.0 for s in securities)
    average_duration = sum(s["duration"] for s in securities) / len(securities)
    average_yield = sum(s["yield_to_maturity"] for s in securities) / len(securities)
    
    return {
        "index_name": name,
        "index_type": index_type,
        "base_currency": "USD",
        "total_market_value": round(total_market_value, 2),
        "average_duration": round(average_duration, 2),
        "average_yield": round(average_yield, 2),
        "securities": securities
    }


# ============================================================================
# Validation Examples
# ============================================================================

def example_single_bond_validation():
    """Example 1: Validate a single bond"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Single Bond Validation")
    print("=" * 80)
    
    # Generate a synthetic bond
    bond_data = generate_synthetic_bond(1)
    
    print("\n📊 Bond Data:")
    print(f"  ISIN: {bond_data['isin']}")
    print(f"  Issuer: {bond_data['issuer_name']} ({bond_data['issuer_type']})")
    print(f"  Rating: {bond_data['credit_rating']}")
    print(f"  Coupon: {bond_data['coupon_rate']}% ({bond_data['coupon_frequency']})")
    print(f"  YTM: {bond_data['yield_to_maturity']}%")
    print(f"  Duration: {bond_data['duration']} years")
    print(f"  Maturity: {bond_data['maturity_date']}")
    
    # Validate using Satya - Model construction validates automatically
    try:
        bond = Bond(**bond_data)
        print("\n✅ Bond validation PASSED!")
        print(f"   Successfully validated bond: {bond.isin}")
        print(f"   Issuer: {bond.issuer_name}")
        print(f"   Price: ${bond.current_price:.2f}")
    except Exception as e:
        print(f"\n❌ Bond validation FAILED: {str(e)[:200]}")


def example_batch_bond_validation():
    """Example 2: Batch validate multiple bonds"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Batch Bond Validation")
    print("=" * 80)
    
    num_bonds = 1000
    print(f"\n📊 Generating {num_bonds:,} synthetic bonds...")
    
    bonds_data = [generate_synthetic_bond(i) for i in range(num_bonds)]
    
    # Validate using Satya's batch processing
    # Note: validate_batch returns a list of booleans for performance
    print(f"⚡ Validating {num_bonds:,} bonds with Satya...")
    validator = Bond.validator()
    validator.set_batch_size(1000)  # Optimal batch size
    
    start_time = time.time()
    results = validator.validate_batch(bonds_data)  # Returns list of bools
    duration = time.time() - start_time
    
    valid_count = sum(1 for r in results if r)  # r is bool
    invalid_count = len(results) - valid_count
    rate = len(bonds_data) / duration
    
    print(f"\n✅ Validation Complete!")
    print(f"   Duration: {duration:.4f}s")
    print(f"   Performance: {rate:,.0f} bonds/second")
    print(f"   Valid: {valid_count:,}/{num_bonds:,}")
    print(f"   Invalid: {invalid_count:,}/{num_bonds:,}")
    
    # Show summary statistics
    if valid_count > 0:
        print(f"\n   ✨ {valid_count:,} bonds passed validation at Rust speed!")


def example_index_validation():

    print("\n" + "=" * 80)
    print("EXAMPLE 3: Bond Index Validation")
    print("=" * 80)
    
    # Generate a corporate bond index
    print("\n📊 Generating Corporate Bond Index with 50 securities...")
    index_data = generate_synthetic_index("US Corporate Bond Index", "Corporate", 50)
    
    print(f"\n   Index: {index_data['index_name']}")
    print(f"   Type: {index_data['index_type']}")
    print(f"   Securities: {len(index_data['securities'])}")
    print(f"   Total Market Value: ${index_data['total_market_value']:,.2f}")
    print(f"   Avg Duration: {index_data['average_duration']:.2f} years")
    print(f"   Avg Yield: {index_data['average_yield']:.2f}%")
    
    # Validate the entire index (validates nested bond structures automatically)
    print("\n⚡ Validating entire index structure...")
    try:
        start_time = time.time()
        index = BondIndex(**index_data)
        duration = time.time() - start_time
        
        print(f"✅ Index validation PASSED!")
        print(f"   Duration: {duration:.4f}s")
        print(f"   Successfully validated {len(index.securities)} bonds in index")
        
        # Show sample securities
        print(f"\n   Sample Securities:")
        for i, bond in enumerate(index.securities[:3]):
            print(f"   [{i+1}] {bond.issuer_name}: {bond.credit_rating}, "
                  f"{bond.coupon_rate}% coupon, YTM {bond.yield_to_maturity}%")
        
    except Exception as e:
        print(f"❌ Index validation FAILED: {str(e)[:200]}")


def example_validation_constraints():
    """Example 4: Demonstrate validation constraints"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Validation Constraints & Error Handling")
    print("=" * 80)
    
    # Test 1: Invalid ISIN format
    print("\n📋 Test 1: Invalid ISIN Format")
    invalid_bond_1 = generate_synthetic_bond(1)
    invalid_bond_1["isin"] = "INVALID123"  # Wrong format
    
    try:
        bond = Bond(**invalid_bond_1)
        print("   ❌ Should have failed!")
    except Exception as e:
        print(f"   ✅ Caught error: ISIN validation failed")
    
    # Test 2: Negative coupon rate
    print("\n📋 Test 2: Invalid Coupon Rate (negative)")
    invalid_bond_2 = generate_synthetic_bond(1)
    invalid_bond_2["coupon_rate"] = -1.0  # Invalid negative
    
    try:
        bond = Bond(**invalid_bond_2)
        print("   ❌ Should have failed!")
    except Exception as e:
        print(f"   ✅ Caught error: Coupon rate must be >= 0")
    
    # Test 3: Invalid credit rating
    print("\n📋 Test 3: Invalid Credit Rating")
    invalid_bond_3 = generate_synthetic_bond(1)
    invalid_bond_3["credit_rating"] = "ZZZ"  # Not a valid rating
    
    try:
        bond = Bond(**invalid_bond_3)
        print("   ❌ Should have failed!")
    except Exception as e:
        print(f"   ✅ Caught error: Invalid credit rating")
    
    # Test 4: Price out of range
    print("\n📋 Test 4: Price Out of Range")
    invalid_bond_4 = generate_synthetic_bond(1)
    invalid_bond_4["current_price"] = 250.0  # > 200% of face value
    
    try:
        bond = Bond(**invalid_bond_4)
        print("   ❌ Should have failed!")
    except Exception as e:
        print(f"   ✅ Caught error: Price exceeds maximum")


def example_performance_comparison():
    """Example 5: Performance analysis with different dataset sizes"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Performance Analysis")
    print("=" * 80)
    
    validator = Bond.validator()
    validator.set_batch_size(10000)
    
    sizes = [100, 1000, 10000, 50000]
    
    print("\n⚡ Performance scaling with dataset size:\n")
    print(f"{'Dataset Size':<15} {'Duration (s)':<15} {'Rate (bonds/s)':<20} {'Valid':<15}")
    print("-" * 70)
    
    for size in sizes:
        bonds_data = [generate_synthetic_bond(i) for i in range(size)]
        
        start_time = time.time()
        results = validator.validate_batch(bonds_data)  # Returns list of bools
        duration = time.time() - start_time
        
        rate = size / duration
        valid_count = sum(1 for r in results if r)  # r is bool
        
        print(f"{size:<15,} {duration:<15.4f} {rate:<20,.0f} {valid_count:<15,}")
    
    print("\n✨ Satya maintains consistent high performance across dataset sizes!")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all examples"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  SATYA: Fixed Income Securities Validation Example".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    
    # Run all examples
    example_single_bond_validation()
    example_batch_bond_validation()
    example_index_validation()
    example_validation_constraints()
    example_performance_comparison()
    
    print("\n" + "=" * 80)
    print("🎉 All Examples Complete!")
    print("=" * 80)
    print("\n📚 Key Takeaways:")
    print("  • Satya provides comprehensive validation for complex financial data")
    print("  • Pattern matching ensures data format compliance (ISIN, CUSIP, dates)")
    print("  • Numeric constraints enforce valid ranges for rates, prices, and yields")
    print("  • Enum validation ensures categorical data integrity")
    print("  • Batch processing delivers high-performance validation at scale")
    print("  • Nested model support handles complex index structures")
    print("\n✨ Satya: Truth and Integrity in Financial Data Validation!\n")


if __name__ == "__main__":
    main()
