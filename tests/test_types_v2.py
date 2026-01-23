"""Comprehensive tests for pydantic v2 compatible types in satya."""

import unittest
import math
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from satya import Model, Field
from satya.special_types import (
    # Numeric types
    PositiveInt, NegativeInt, NonNegativeInt, NonPositiveInt,
    PositiveFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat,
    FiniteFloat,
    # Strict types
    StrictStr, StrictInt, StrictFloat, StrictBool, StrictBytes,
    # Constrained constructors
    conint, confloat, constr, conbytes, conlist, conset, confrozenset, condecimal,
    # UUID types
    UUID1, UUID3, UUID4, UUID5,
    # DateTime types
    FutureDate, PastDate, FutureDatetime, PastDatetime,
    AwareDatetime, NaiveDatetime,
    # Network types
    AnyUrl, AnyHttpUrl, FileUrl, FtpUrl, WebsocketUrl,
    IPvAnyAddress, IPvAnyInterface, IPvAnyNetwork,
    NameEmail, PostgresDsn, MySQLDsn, RedisDsn, MongoDsn, KafkaDsn,
    # Other types
    ByteSize, Json,
    # String types
    EmailStr, HttpUrl,
)


class TestNumericTypes(unittest.TestCase):
    """Test numeric constraint types."""

    def test_positive_int(self):
        self.assertEqual(PositiveInt(5), 5)
        self.assertIsInstance(PositiveInt(1), int)
        with self.assertRaises(ValueError):
            PositiveInt(0)
        with self.assertRaises(ValueError):
            PositiveInt(-1)

    def test_negative_int(self):
        self.assertEqual(NegativeInt(-3), -3)
        with self.assertRaises(ValueError):
            NegativeInt(0)
        with self.assertRaises(ValueError):
            NegativeInt(5)

    def test_non_negative_int(self):
        self.assertEqual(NonNegativeInt(0), 0)
        self.assertEqual(NonNegativeInt(5), 5)
        with self.assertRaises(ValueError):
            NonNegativeInt(-1)

    def test_non_positive_int(self):
        self.assertEqual(NonPositiveInt(0), 0)
        self.assertEqual(NonPositiveInt(-5), -5)
        with self.assertRaises(ValueError):
            NonPositiveInt(1)

    def test_positive_float(self):
        self.assertEqual(PositiveFloat(1.5), 1.5)
        with self.assertRaises(ValueError):
            PositiveFloat(0.0)
        with self.assertRaises(ValueError):
            PositiveFloat(-0.1)

    def test_negative_float(self):
        self.assertEqual(NegativeFloat(-1.5), -1.5)
        with self.assertRaises(ValueError):
            NegativeFloat(0.0)

    def test_non_negative_float(self):
        self.assertEqual(NonNegativeFloat(0.0), 0.0)
        self.assertEqual(NonNegativeFloat(1.5), 1.5)
        with self.assertRaises(ValueError):
            NonNegativeFloat(-0.1)

    def test_non_positive_float(self):
        self.assertEqual(NonPositiveFloat(0.0), 0.0)
        self.assertEqual(NonPositiveFloat(-1.5), -1.5)
        with self.assertRaises(ValueError):
            NonPositiveFloat(0.1)

    def test_finite_float(self):
        self.assertEqual(FiniteFloat(1.5), 1.5)
        self.assertEqual(FiniteFloat(0.0), 0.0)
        with self.assertRaises(ValueError):
            FiniteFloat(float('inf'))
        with self.assertRaises(ValueError):
            FiniteFloat(float('-inf'))
        with self.assertRaises(ValueError):
            FiniteFloat(float('nan'))


class TestStrictTypes(unittest.TestCase):
    """Test strict types that reject coercion."""

    def test_strict_str(self):
        self.assertEqual(StrictStr("hello"), "hello")
        with self.assertRaises(TypeError):
            StrictStr(123)
        with self.assertRaises(TypeError):
            StrictStr(True)

    def test_strict_int(self):
        self.assertEqual(StrictInt(42), 42)
        with self.assertRaises(TypeError):
            StrictInt("42")
        with self.assertRaises(TypeError):
            StrictInt(True)  # bool is subclass of int but should be rejected

    def test_strict_float(self):
        self.assertEqual(StrictFloat(3.14), 3.14)
        # Python's float() natively accepts int, so StrictFloat allows it
        self.assertEqual(StrictFloat(42), 42.0)
        with self.assertRaises(TypeError):
            StrictFloat("3.14")

    def test_strict_bool(self):
        self.assertEqual(StrictBool(True), True)
        self.assertEqual(StrictBool(False), False)
        with self.assertRaises(TypeError):
            StrictBool(1)
        with self.assertRaises(TypeError):
            StrictBool("true")

    def test_strict_bytes(self):
        self.assertEqual(StrictBytes(b"hello"), b"hello")
        with self.assertRaises(TypeError):
            StrictBytes("hello")


class TestConstrainedConstructors(unittest.TestCase):
    """Test constrained type constructors."""

    def test_conint_gt(self):
        PosInt = conint(gt=0)
        self.assertEqual(PosInt(5), 5)
        with self.assertRaises(ValueError):
            PosInt(0)

    def test_conint_le(self):
        MaxInt = conint(le=100)
        self.assertEqual(MaxInt(100), 100)
        with self.assertRaises(ValueError):
            MaxInt(101)

    def test_conint_range(self):
        RangeInt = conint(ge=1, le=10)
        self.assertEqual(RangeInt(1), 1)
        self.assertEqual(RangeInt(10), 10)
        with self.assertRaises(ValueError):
            RangeInt(0)
        with self.assertRaises(ValueError):
            RangeInt(11)

    def test_conint_multiple_of(self):
        EvenInt = conint(multiple_of=2)
        self.assertEqual(EvenInt(4), 4)
        with self.assertRaises(ValueError):
            EvenInt(3)

    def test_confloat_gt(self):
        PosFloat = confloat(gt=0.0)
        self.assertEqual(PosFloat(0.1), 0.1)
        with self.assertRaises(ValueError):
            PosFloat(0.0)

    def test_confloat_allow_inf_nan(self):
        NoInf = confloat(allow_inf_nan=False)
        self.assertEqual(NoInf(1.5), 1.5)
        with self.assertRaises(ValueError):
            NoInf(float('inf'))
        with self.assertRaises(ValueError):
            NoInf(float('nan'))

    def test_constr_min_max_length(self):
        BoundedStr = constr(min_length=2, max_length=5)
        self.assertEqual(BoundedStr("hi"), "hi")
        self.assertEqual(BoundedStr("hello"), "hello")
        with self.assertRaises(ValueError):
            BoundedStr("x")
        with self.assertRaises(ValueError):
            BoundedStr("toolong")

    def test_constr_pattern(self):
        AlphaStr = constr(pattern=r'^[a-z]+$')
        self.assertEqual(AlphaStr("hello"), "hello")
        with self.assertRaises(ValueError):
            AlphaStr("Hello")
        with self.assertRaises(ValueError):
            AlphaStr("123")

    def test_constr_strip_whitespace(self):
        StrippedStr = constr(strip_whitespace=True)
        self.assertEqual(StrippedStr("  hello  "), "hello")

    def test_constr_to_lower(self):
        LowerStr = constr(to_lower=True)
        self.assertEqual(LowerStr("HELLO"), "hello")

    def test_constr_to_upper(self):
        UpperStr = constr(to_upper=True)
        self.assertEqual(UpperStr("hello"), "HELLO")

    def test_conbytes_min_max(self):
        BoundedBytes = conbytes(min_length=2, max_length=5)
        self.assertEqual(BoundedBytes(b"hi"), b"hi")
        with self.assertRaises(ValueError):
            BoundedBytes(b"x")
        with self.assertRaises(ValueError):
            BoundedBytes(b"toolong")

    def test_conlist(self):
        ShortList = conlist(int, min_length=1, max_length=3)
        self.assertEqual(ShortList([1, 2]), [1, 2])
        with self.assertRaises(ValueError):
            ShortList([])
        with self.assertRaises(ValueError):
            ShortList([1, 2, 3, 4])

    def test_conset(self):
        BoundedSet = conset(int, min_length=1, max_length=3)
        self.assertEqual(BoundedSet({1, 2}), {1, 2})
        with self.assertRaises(ValueError):
            BoundedSet(set())
        with self.assertRaises(ValueError):
            BoundedSet({1, 2, 3, 4})

    def test_confrozenset(self):
        BoundedFrozen = confrozenset(int, min_length=1, max_length=3)
        result = BoundedFrozen(frozenset([1, 2]))
        self.assertEqual(result, frozenset([1, 2]))
        with self.assertRaises(ValueError):
            BoundedFrozen(frozenset())

    def test_condecimal(self):
        BoundedDec = condecimal(gt=Decimal('0'), le=Decimal('100'))
        self.assertEqual(BoundedDec(Decimal('50')), Decimal('50'))
        with self.assertRaises(ValueError):
            BoundedDec(Decimal('0'))
        with self.assertRaises(ValueError):
            BoundedDec(Decimal('101'))

    def test_condecimal_max_digits(self):
        LimitedDec = condecimal(max_digits=5)
        self.assertEqual(LimitedDec(Decimal('123.45')), Decimal('123.45'))
        with self.assertRaises(ValueError):
            LimitedDec(Decimal('123456'))

    def test_condecimal_decimal_places(self):
        TwoPlaces = condecimal(decimal_places=2)
        self.assertEqual(TwoPlaces(Decimal('1.23')), Decimal('1.23'))
        with self.assertRaises(ValueError):
            TwoPlaces(Decimal('1.234'))

    def test_type_info_protocol(self):
        """Test __satya_type_info__ protocol on constrained types."""
        PosInt = conint(gt=0)
        info = getattr(PosInt, '__satya_type_info__', None)
        self.assertIsNotNone(info)
        self.assertEqual(info['base_type'], 'int')
        self.assertEqual(info['constraints']['gt'], 0)

    def test_type_info_strict(self):
        info = getattr(StrictStr, '__satya_type_info__', None)
        self.assertIsNotNone(info)
        self.assertTrue(info.get('strict', False))


class TestUUIDTypes(unittest.TestCase):
    """Test UUID validation types."""

    def test_uuid4_valid(self):
        # Standard UUID4
        val = UUID4("550e8400-e29b-41d4-a716-446655440000")
        self.assertIsInstance(val, str)

    def test_uuid4_invalid(self):
        with self.assertRaises(ValueError):
            UUID4("not-a-uuid")
        with self.assertRaises(ValueError):
            UUID4("")

    def test_uuid1_valid(self):
        import uuid
        u = str(uuid.uuid1())
        val = UUID1(u)
        self.assertIsInstance(val, str)

    def test_uuid1_wrong_version(self):
        # UUID4 should not be accepted as UUID1
        import uuid
        u = str(uuid.uuid4())
        with self.assertRaises(ValueError):
            UUID1(u)

    def test_uuid3_valid(self):
        import uuid
        u = str(uuid.uuid3(uuid.NAMESPACE_DNS, "example.com"))
        val = UUID3(u)
        self.assertIsInstance(val, str)

    def test_uuid5_valid(self):
        import uuid
        u = str(uuid.uuid5(uuid.NAMESPACE_DNS, "example.com"))
        val = UUID5(u)
        self.assertIsInstance(val, str)


class TestDateTimeTypes(unittest.TestCase):
    """Test date/time validation types."""

    def test_future_date(self):
        tomorrow = date.today() + timedelta(days=1)
        val = FutureDate(tomorrow.isoformat())
        self.assertIsInstance(val, date)
        self.assertEqual(val, tomorrow)

        with self.assertRaises(ValueError):
            yesterday = date.today() - timedelta(days=1)
            FutureDate(yesterday.isoformat())

    def test_past_date(self):
        yesterday = date.today() - timedelta(days=1)
        val = PastDate(yesterday.isoformat())
        self.assertIsInstance(val, date)
        self.assertEqual(val, yesterday)

        with self.assertRaises(ValueError):
            tomorrow = date.today() + timedelta(days=1)
            PastDate(tomorrow.isoformat())

    def test_future_datetime(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        val = FutureDatetime(future.isoformat())
        self.assertIsInstance(val, datetime)

        with self.assertRaises(ValueError):
            past = datetime.now(timezone.utc) - timedelta(hours=1)
            FutureDatetime(past.isoformat())

    def test_past_datetime(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        val = PastDatetime(past.isoformat())
        self.assertIsInstance(val, datetime)

        with self.assertRaises(ValueError):
            future = datetime.now(timezone.utc) + timedelta(hours=1)
            PastDatetime(future.isoformat())

    def test_aware_datetime(self):
        aware = datetime.now(timezone.utc).isoformat()
        val = AwareDatetime(aware)
        self.assertIsInstance(val, datetime)
        self.assertIsNotNone(val.tzinfo)

        with self.assertRaises(ValueError):
            naive = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            AwareDatetime(naive)

    def test_naive_datetime(self):
        naive = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        val = NaiveDatetime(naive)
        self.assertIsInstance(val, datetime)
        self.assertIsNone(val.tzinfo)

        with self.assertRaises(ValueError):
            aware = datetime.now(timezone.utc).isoformat()
            NaiveDatetime(aware)


class TestNetworkTypes(unittest.TestCase):
    """Test network validation types."""

    def test_any_url(self):
        self.assertEqual(AnyUrl("https://example.com"), "https://example.com")
        self.assertEqual(AnyUrl("ftp://files.example.com"), "ftp://files.example.com")
        with self.assertRaises(ValueError):
            AnyUrl("not-a-url")

    def test_any_http_url(self):
        self.assertEqual(AnyHttpUrl("https://example.com"), "https://example.com")
        self.assertEqual(AnyHttpUrl("http://example.com"), "http://example.com")
        with self.assertRaises(ValueError):
            AnyHttpUrl("ftp://example.com")

    def test_file_url(self):
        self.assertEqual(FileUrl("file:///tmp/test.txt"), "file:///tmp/test.txt")
        with self.assertRaises(ValueError):
            FileUrl("https://example.com")

    def test_ftp_url(self):
        self.assertEqual(FtpUrl("ftp://files.example.com"), "ftp://files.example.com")
        with self.assertRaises(ValueError):
            FtpUrl("https://example.com")

    def test_websocket_url(self):
        self.assertEqual(WebsocketUrl("ws://example.com/ws"), "ws://example.com/ws")
        self.assertEqual(WebsocketUrl("wss://example.com/ws"), "wss://example.com/ws")
        with self.assertRaises(ValueError):
            WebsocketUrl("https://example.com")

    def test_ip_address(self):
        self.assertEqual(IPvAnyAddress("192.168.1.1"), "192.168.1.1")
        self.assertEqual(IPvAnyAddress("::1"), "::1")
        with self.assertRaises(ValueError):
            IPvAnyAddress("not-an-ip")

    def test_ip_interface(self):
        self.assertEqual(IPvAnyInterface("192.168.1.1/24"), "192.168.1.1/24")
        with self.assertRaises(ValueError):
            IPvAnyInterface("not-an-interface")

    def test_ip_network(self):
        self.assertEqual(IPvAnyNetwork("192.168.1.0/24"), "192.168.1.0/24")
        with self.assertRaises(ValueError):
            IPvAnyNetwork("not-a-network")

    def test_name_email(self):
        self.assertEqual(NameEmail("John <john@example.com>"), "John <john@example.com>")
        with self.assertRaises(ValueError):
            NameEmail("not-a-name-email")

    def test_postgres_dsn(self):
        self.assertEqual(
            PostgresDsn("postgresql://user:pass@localhost/db"),
            "postgresql://user:pass@localhost/db"
        )
        with self.assertRaises(ValueError):
            PostgresDsn("mysql://user:pass@localhost/db")

    def test_mysql_dsn(self):
        self.assertEqual(
            MySQLDsn("mysql://user:pass@localhost/db"),
            "mysql://user:pass@localhost/db"
        )

    def test_redis_dsn(self):
        self.assertEqual(
            RedisDsn("redis://localhost:6379/0"),
            "redis://localhost:6379/0"
        )

    def test_mongo_dsn(self):
        self.assertEqual(
            MongoDsn("mongodb://localhost:27017/mydb"),
            "mongodb://localhost:27017/mydb"
        )

    def test_kafka_dsn(self):
        self.assertEqual(
            KafkaDsn("kafka://localhost:9092"),
            "kafka://localhost:9092"
        )


class TestByteSize(unittest.TestCase):
    """Test ByteSize type."""

    def test_from_int(self):
        self.assertEqual(ByteSize(1024), 1024)

    def test_from_string_kb(self):
        self.assertEqual(ByteSize("1KB"), 1000)
        self.assertEqual(ByteSize("1kb"), 1000)

    def test_from_string_mb(self):
        self.assertEqual(ByteSize("1MB"), 1000 * 1000)

    def test_from_string_gb(self):
        self.assertEqual(ByteSize("1GB"), 1000 ** 3)

    def test_from_string_tb(self):
        self.assertEqual(ByteSize("1TB"), 1000 ** 4)

    def test_from_string_bytes(self):
        self.assertEqual(ByteSize("500B"), 500)

    def test_human_readable(self):
        b = ByteSize(1000)
        self.assertEqual(b.human_readable(), "1KB")
        b2 = ByteSize(1000 * 1000)
        self.assertEqual(b2.human_readable(), "1MB")
        b3 = ByteSize(1500)
        self.assertEqual(b3.human_readable(), "1.5KB")

    def test_invalid_string(self):
        with self.assertRaises(ValueError):
            ByteSize("not-a-size")


class TestJson(unittest.TestCase):
    """Test Json type."""

    def test_valid_json(self):
        val = Json('{"key": "value"}')
        # Json is its own type, not a plain str
        self.assertIsInstance(val, Json)

    def test_valid_json_array(self):
        val = Json('[1, 2, 3]')
        self.assertIsInstance(val, Json)

    def test_invalid_json(self):
        with self.assertRaises(ValueError):
            Json("not valid json")

    def test_parsed(self):
        val = Json('{"key": "value"}')
        # .parsed is a property, not a method
        self.assertEqual(val.parsed, {"key": "value"})

    def test_parsed_array(self):
        val = Json('[1, 2, 3]')
        self.assertEqual(val.parsed, [1, 2, 3])


class TestTypesInModel(unittest.TestCase):
    """Test that special types work correctly inside Models."""

    def test_positive_int_in_model(self):
        class Order(Model):
            quantity: PositiveInt

        order = Order(quantity=5)
        self.assertEqual(order.quantity, 5)

    def test_conint_in_model(self):
        Qty = conint(gt=0, le=1000)
        class Order(Model):
            quantity: Qty

        order = Order(quantity=10)
        self.assertEqual(order.quantity, 10)

    def test_email_str_in_model(self):
        class User(Model):
            email: EmailStr

        user = User(email="test@example.com")
        self.assertEqual(user.email, "test@example.com")

    def test_constrained_str_in_model(self):
        Name = constr(min_length=2, max_length=50)
        class Person(Model):
            name: Name

        person = Person(name="Alice")
        self.assertEqual(person.name, "Alice")

    def test_multiple_special_types_in_model(self):
        class Product(Model):
            name: str = Field(min_length=1)
            price: PositiveFloat
            quantity: NonNegativeInt

        product = Product(name="Widget", price=9.99, quantity=0)
        self.assertEqual(product.name, "Widget")
        self.assertEqual(product.price, 9.99)
        self.assertEqual(product.quantity, 0)


class TestTypeInfoProtocol(unittest.TestCase):
    """Test that __satya_type_info__ protocol works correctly."""

    def test_positive_int_type_info(self):
        info = PositiveInt.__satya_type_info__
        self.assertEqual(info['base_type'], 'int')
        self.assertEqual(info['constraints']['gt'], 0)

    def test_negative_float_type_info(self):
        info = NegativeFloat.__satya_type_info__
        self.assertEqual(info['base_type'], 'float')
        self.assertEqual(info['constraints']['lt'], 0.0)

    def test_finite_float_type_info(self):
        info = FiniteFloat.__satya_type_info__
        self.assertEqual(info['base_type'], 'float')
        self.assertTrue(info['constraints'].get('finite'))

    def test_strict_str_type_info(self):
        info = StrictStr.__satya_type_info__
        self.assertEqual(info['base_type'], 'str')
        self.assertTrue(info.get('strict'))

    def test_conint_type_info(self):
        RangeInt = conint(ge=0, le=100)
        info = RangeInt.__satya_type_info__
        self.assertEqual(info['base_type'], 'int')
        self.assertEqual(info['constraints']['ge'], 0)
        self.assertEqual(info['constraints']['le'], 100)

    def test_constr_type_info(self):
        BoundedStr = constr(min_length=5, max_length=20, pattern=r'^\w+$')
        info = BoundedStr.__satya_type_info__
        self.assertEqual(info['base_type'], 'str')
        self.assertEqual(info['constraints']['min_length'], 5)
        self.assertEqual(info['constraints']['max_length'], 20)
        self.assertEqual(info['constraints']['pattern'], r'^\w+$')

    def test_email_str_type_info(self):
        info = EmailStr.__satya_type_info__
        self.assertEqual(info['base_type'], 'str')
        self.assertTrue(info['constraints'].get('email'))


if __name__ == '__main__':
    unittest.main()
