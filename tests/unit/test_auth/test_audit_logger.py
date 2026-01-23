"""Unit tests for audit logger.

Tests for opera_cloud_mcp/auth/audit_logger.py
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import hashlib

from opera_cloud_mcp.auth.audit_logger import (
    AuditRecord,
    AuditDatabase,
    AuditLogger,
)


class TestAuditRecord:
    """Test AuditRecord model."""

    def test_audit_record_creation(self):
        """Test creating an audit record with all fields."""
        record = AuditRecord(
            id="test_001",
            timestamp=datetime.now(UTC),
            event_type="authentication",
            client_id_hash="abc123",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            success=True,
            details={"key": "value"},
            risk_score=10,
            session_id="session_123",
        )
        assert record.id == "test_001"
        assert record.event_type == "authentication"
        assert record.client_id_hash == "abc123"
        assert record.ip_address == "192.168.1.1"
        assert record.user_agent == "TestAgent/1.0"
        assert record.success is True
        assert record.details == {"key": "value"}
        assert record.risk_score == 10
        assert record.session_id == "session_123"

    def test_audit_record_defaults(self):
        """Test audit record default values."""
        record = AuditRecord(
            id="test_002",
            timestamp=datetime.now(UTC),
            event_type="test",
            client_id_hash="xyz789",
            success=False,
        )
        assert record.ip_address is None
        assert record.user_agent is None
        assert record.details == {}
        assert record.risk_score == 0
        assert record.session_id is None
        assert record.checksum is None

    def test_calculate_checksum(self):
        """Test checksum calculation for integrity protection."""
        record = AuditRecord(
            id="test_003",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            event_type="auth_event",
            client_id_hash="client123",
            ip_address="10.0.0.1",
            user_agent="TestAgent",
            success=True,
            details={"action": "login"},
        )

        secret_key = b"test_secret_key_32_bytes_long!!!!"
        checksum = record.calculate_checksum(secret_key)

        assert checksum is not None
        assert len(checksum) == 64  # SHA256 hex length
        assert isinstance(checksum, str)

    def test_calculate_checksum_deterministic(self):
        """Test checksum is deterministic for same input."""
        record = AuditRecord(
            id="test_004",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            event_type="auth_event",
            client_id_hash="client123",
            success=True,
        )

        secret_key = b"test_secret_key_32_bytes_long!!!!"

        checksum1 = record.calculate_checksum(secret_key)
        checksum2 = record.calculate_checksum(secret_key)

        assert checksum1 == checksum2

    def test_verify_checksum_valid(self):
        """Test checksum verification for valid record."""
        record = AuditRecord(
            id="test_005",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            event_type="auth_event",
            client_id_hash="client123",
            success=True,
        )

        secret_key = b"test_secret_key_32_bytes_long!!!!"
        record.checksum = record.calculate_checksum(secret_key)

        assert record.verify_checksum(secret_key) is True

    def test_verify_checksum_invalid(self):
        """Test checksum verification fails for tampered record."""
        record = AuditRecord(
            id="test_006",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            event_type="auth_event",
            client_id_hash="client123",
            success=True,
            checksum="invalid_checksum",
        )

        secret_key = b"test_secret_key_32_bytes_long!!!!"

        assert record.verify_checksum(secret_key) is False

    def test_verify_checksum_no_checksum(self):
        """Test checksum verification returns False when no checksum."""
        record = AuditRecord(
            id="test_007",
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            event_type="auth_event",
            client_id_hash="client123",
            success=True,
        )

        secret_key = b"test_secret_key_32_bytes_long!!!!"

        assert record.verify_checksum(secret_key) is False


class TestAuditDatabase:
    """Test AuditDatabase class."""

    def test_audit_database_init_default_path(self, tmp_path):
        """Test database initialization with default path."""
        # Patch home directory to use temp path
        with patch.object(Path, "home", return_value=tmp_path):
            db = AuditDatabase()
            expected_path = tmp_path / ".opera_cloud_mcp" / "audit" / "audit.db"
            assert db.db_path == expected_path
            assert db.db_path.exists()

    def test_audit_database_init_custom_path(self, tmp_path):
        """Test database initialization with custom path."""
        custom_path = tmp_path / "custom_audit.db"
        db = AuditDatabase(db_path=custom_path)
        assert db.db_path == custom_path
        assert db.db_path.exists()

    def test_audit_database_init_with_encryption_key(self, tmp_path):
        """Test database initialization with provided encryption key."""
        key = b"test_key_32_bytes_long!!!!!!!!"
        db = AuditDatabase(db_path=tmp_path / "test.db", encryption_key=key)

        assert db.encryption_key == key

    def test_get_or_create_encryption_key_creates_new(self, tmp_path):
        """Test encryption key creation when none exists."""
        db = AuditDatabase(db_path=tmp_path / "test.db")
        key = db._get_or_create_encryption_key()

        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_get_or_create_encryption_key_loads_existing(self, tmp_path):
        """Test loading existing encryption key."""
        db1 = AuditDatabase(db_path=tmp_path / "test.db")
        key1 = db1.encryption_key

        db2 = AuditDatabase(db_path=tmp_path / "test.db")
        key2 = db2.encryption_key

        # Keys should be the same when loaded from file
        assert key1 == key2

    def test_init_database_creates_tables(self, tmp_path):
        """Test database schema initialization."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        conn = sqlite3.connect(str(db.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "audit_records" in tables
        assert "database_audit" in tables

    def test_init_database_creates_indexes(self, tmp_path):
        """Test database index creation."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        conn = sqlite3.connect(str(db.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "idx_timestamp" in indexes
        assert "idx_event_type" in indexes
        assert "idx_client_id" in indexes
        assert "idx_success" in indexes

    def test_insert_record_success(self, tmp_path):
        """Test successful record insertion."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        record = AuditRecord(
            id="test_insert_001",
            timestamp=datetime.now(UTC),
            event_type="test_event",
            client_id_hash="client123",
            success=True,
            details={"test": "data"},
        )

        result = db.insert_record(record)

        assert result is True

    def test_insert_record_with_encryption(self, tmp_path):
        """Test that details are encrypted in database."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        record = AuditRecord(
            id="test_enc_001",
            timestamp=datetime.now(UTC),
            event_type="test_event",
            client_id_hash="client123",
            success=True,
            details={"sensitive": "data"},
        )

        db.insert_record(record)

        # Verify data is encrypted in database
        conn = sqlite3.connect(str(db.db_path))
        cursor = conn.execute(
            "SELECT encrypted_details FROM audit_records WHERE id = ?", ("test_enc_001",)
        )
        encrypted_data = cursor.fetchone()[0]
        conn.close()

        assert encrypted_data is not None
        # Plaintext should not be in the encrypted data
        assert b"sensitive" not in encrypted_data

    def test_insert_record_generates_checksum(self, tmp_path):
        """Test that checksum is generated during insertion."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        record = AuditRecord(
            id="test_checksum_001",
            timestamp=datetime.now(UTC),
            event_type="test_event",
            client_id_hash="client123",
            success=True,
        )

        db.insert_record(record)

        # Verify checksum was stored
        conn = sqlite3.connect(str(db.db_path))
        cursor = conn.execute(
            "SELECT checksum FROM audit_records WHERE id = ?", ("test_checksum_001",)
        )
        checksum = cursor.fetchone()[0]
        conn.close()

        assert checksum is not None
        assert len(checksum) == 64

    def test_build_query_conditions_no_filters(self, tmp_path):
        """Test query building with no filters."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        where_clause, params = db._build_query_conditions(
            start_time=None, end_time=None, event_types=None, client_id_hash=None, success_only=None
        )

        assert where_clause == ""
        assert params == []

    def test_build_query_conditions_with_filters(self, tmp_path):
        """Test query building with filters."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        start_time = datetime.now(UTC) - timedelta(hours=1)
        end_time = datetime.now(UTC)
        event_types = {"login", "logout"}
        client_id_hash = "abc123"
        success_only = True

        where_clause, params = db._build_query_conditions(
            start_time=start_time,
            end_time=end_time,
            event_types=event_types,
            client_id_hash=client_id_hash,
            success_only=success_only,
        )

        assert "WHERE" in where_clause
        assert "timestamp >= ?" in where_clause
        assert "timestamp <= ?" in where_clause
        assert "event_type IN" in where_clause
        assert "client_id_hash = ?" in where_clause
        assert "success = ?" in where_clause

        assert len(params) == 6  # 2 timestamps + 2 event types + client_id + success

    def test_query_records_empty(self, tmp_path):
        """Test querying records from empty database."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        records = db.query_records()

        assert records == []

    def test_query_records_with_data(self, tmp_path):
        """Test querying records with data."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        # Insert test records
        record1 = AuditRecord(
            id="query_001",
            timestamp=datetime.now(UTC),
            event_type="login",
            client_id_hash="client1",
            success=True,
        )
        record2 = AuditRecord(
            id="query_002",
            timestamp=datetime.now(UTC),
            event_type="logout",
            client_id_hash="client1",
            success=True,
        )

        db.insert_record(record1)
        db.insert_record(record2)

        records = db.query_records()

        assert len(records) == 2

    def test_query_records_with_event_filter(self, tmp_path):
        """Test querying records with event type filter."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        # Insert test records
        record1 = AuditRecord(
            id="filter_001",
            timestamp=datetime.now(UTC),
            event_type="login",
            client_id_hash="client1",
            success=True,
        )
        record2 = AuditRecord(
            id="filter_002",
            timestamp=datetime.now(UTC),
            event_type="logout",
            client_id_hash="client1",
            success=True,
        )

        db.insert_record(record1)
        db.insert_record(record2)

        records = db.query_records(event_types={"login"})

        assert len(records) == 1
        assert records[0].event_type == "login"

    def test_get_statistics_empty_database(self, tmp_path):
        """Test statistics from empty database."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        stats = db.get_statistics(hours=24)

        assert stats["total_records"] == 0
        assert stats["successful_events"] == 0
        assert stats["failed_events"] == 0
        assert stats["unique_clients"] == 0

    def test_get_statistics_with_data(self, tmp_path):
        """Test statistics with actual data."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        # Insert test records
        for i in range(5):
            record = AuditRecord(
                id=f"stat_{i:03d}",
                timestamp=datetime.now(UTC),
                event_type="login",
                client_id_hash=f"client{i}",
                success=i < 4,  # 4 success, 1 failure
            )
            db.insert_record(record)

        stats = db.get_statistics(hours=24)

        assert stats["total_records"] == 5
        assert stats["successful_events"] == 4
        assert stats["failed_events"] == 1
        assert stats["unique_clients"] == 5

    def test_cleanup_old_records(self, tmp_path):
        """Test cleanup of old records."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        # Insert old record
        old_record = AuditRecord(
            id="old_001",
            timestamp=datetime.now(UTC) - timedelta(days=100),
            event_type="old_event",
            client_id_hash="client1",
            success=True,
        )
        db.insert_record(old_record)

        # Insert recent record
        recent_record = AuditRecord(
            id="recent_001",
            timestamp=datetime.now(UTC),
            event_type="recent_event",
            client_id_hash="client1",
            success=True,
        )
        db.insert_record(recent_record)

        # Cleanup records older than 90 days
        deleted_count = db.cleanup_old_records(days=90)

        assert deleted_count >= 1

    def test_verify_database_integrity_empty(self, tmp_path):
        """Test integrity verification on empty database."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        integrity = db.verify_database_integrity()

        assert integrity["total_records"] == 0
        assert integrity["valid_records"] == 0
        assert integrity["invalid_records"] == 0
        assert integrity["database_healthy"] is True

    def test_verify_database_integrity_with_valid_records(self, tmp_path):
        """Test integrity verification with valid records."""
        db = AuditDatabase(db_path=tmp_path / "test.db")

        # Insert valid record
        record = AuditRecord(
            id="valid_001",
            timestamp=datetime.now(UTC),
            event_type="test",
            client_id_hash="client1",
            success=True,
        )
        db.insert_record(record)

        integrity = db.verify_database_integrity()

        assert integrity["total_records"] == 1
        assert integrity["valid_records"] == 1
        assert integrity["invalid_records"] == 0
        assert integrity["database_healthy"] is True


class TestAuditLogger:
    """Test AuditLogger high-level interface."""

    def test_audit_logger_init(self, tmp_path):
        """Test audit logger initialization."""
        logger = AuditLogger(db_path=tmp_path / "test.db")

        assert logger.database is not None
        assert logger._session_counter == 0
        assert logger._session_prefix is not None

    def test_log_authentication_event_success(self, tmp_path):
        """Test successful authentication event logging."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        result = audit_logger.log_authentication_event(
            event_type="login",
            client_id="test_client",
            success=True,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            details={"action": "login"},
            risk_score=5,
        )

        assert result is True

    def test_log_authentication_event_generates_id(self, tmp_path):
        """Test that unique IDs are generated for each event."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        audit_logger.log_authentication_event(
            event_type="login", client_id="test_client", success=True
        )

        # Check session counter incremented
        assert audit_logger._session_counter == 1

    def test_log_authentication_event_hashes_client_id(self, tmp_path):
        """Test that client ID is hashed for privacy."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        audit_logger.log_authentication_event(
            event_type="login", client_id="sensitive_client", success=True
        )

        records = audit_logger.database.query_records()

        assert len(records) == 1
        # Client ID should be hashed, not plaintext
        assert "sensitive_client" not in records[0].client_id_hash
        assert len(records[0].client_id_hash) == 16

    def test_get_audit_trail_no_filter(self, tmp_path):
        """Test getting audit trail without filters."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # Insert some events
        audit_logger.log_authentication_event(
            event_type="login", client_id="client1", success=True
        )
        audit_logger.log_authentication_event(
            event_type="logout", client_id="client1", success=True
        )

        trail = audit_logger.get_audit_trail(hours=1)

        assert len(trail) == 2

    def test_get_audit_trail_with_client_filter(self, tmp_path):
        """Test getting audit trail filtered by client."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # Insert events for different clients
        audit_logger.log_authentication_event(
            event_type="login", client_id="client1", success=True
        )
        audit_logger.log_authentication_event(
            event_type="login", client_id="client2", success=True
        )

        trail = audit_logger.get_audit_trail(client_id="client1", hours=1)

        assert len(trail) == 1

    def test_get_audit_trail_with_event_filter(self, tmp_path):
        """Test getting audit trail filtered by event types."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # Insert different event types
        audit_logger.log_authentication_event(
            event_type="login", client_id="client1", success=True
        )
        audit_logger.log_authentication_event(
            event_type="logout", client_id="client1", success=True
        )
        audit_logger.log_authentication_event(
            event_type="login", client_id="client2", success=True
        )

        trail = audit_logger.get_audit_trail(hours=1, event_types={"login"})

        assert len(trail) == 2
        assert all(r.event_type == "login" for r in trail)

    def test_get_security_report(self, tmp_path):
        """Test security report generation."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # Insert various events
        for i in range(10):
            audit_logger.log_authentication_event(
                event_type="login",
                client_id=f"client{i}",
                success=i < 8,  # 8 success, 2 failures
            )

        report = audit_logger.get_security_report(hours=1)

        assert "total_records" in report
        assert "successful_events" in report
        assert "failed_events" in report
        assert "threat_level" in report
        assert "recommendations" in report
        assert report["total_records"] == 10
        assert report["successful_events"] == 8
        assert report["failed_events"] == 2

    def test_get_security_report_threat_level_low(self, tmp_path):
        """Test threat level calculation for low risk."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # All successful events
        for i in range(10):
            audit_logger.log_authentication_event(
                event_type="login", client_id=f"client{i}", success=True, risk_score=0
            )

        report = audit_logger.get_security_report(hours=1)

        assert report["threat_level"] == "low"

    def test_get_security_report_threat_level_high(self, tmp_path):
        """Test threat level calculation for high risk."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # High failure rate and high risk events
        for i in range(10):
            audit_logger.log_authentication_event(
                event_type="login", client_id=f"client{i}", success=False, risk_score=75
            )

        report = audit_logger.get_security_report(hours=1)

        assert report["threat_level"] == "high"

    def test_generate_recommendations_no_concerns(self, tmp_path):
        """Test recommendations when no security concerns."""
        audit_logger = AuditLogger(db_path=tmp_path / "test.db")

        # All successful events
        for i in range(3):
            audit_logger.log_authentication_event(
                event_type="login", client_id=f"client{i}", success=True, risk_score=0
            )

        report = audit_logger.get_security_report(hours=1)

        assert "No immediate security concerns detected" in report["recommendations"]
