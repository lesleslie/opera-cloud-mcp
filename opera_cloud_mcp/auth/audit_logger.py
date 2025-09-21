"""
Comprehensive audit logging system for OPERA Cloud MCP authentication.

This module provides enterprise-grade audit logging capabilities for tracking
all authentication and authorization events with tamper-resistant storage.
"""

import hashlib
import json
import logging
import secrets
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine

from opera_cloud_mcp.models.common import AuditRecordDB

logger = logging.getLogger(__name__)


class AuditRecord(BaseModel):
    """Immutable audit record for security events."""

    id: str
    timestamp: datetime
    event_type: str
    client_id_hash: str
    ip_address: str | None = None
    user_agent: str | None = None
    success: bool
    details: dict[str, Any] = {}
    risk_score: int = 0
    session_id: str | None = None
    checksum: str | None = None

    def calculate_checksum(self, secret_key: bytes) -> str:
        """Calculate tamper-resistant checksum."""
        # Create deterministic string representation
        data = (
            f"{self.id}{self.timestamp.isoformat()}{self.event_type}"
            f"{self.client_id_hash}{self.success}"
        )
        if self.ip_address:
            data += self.ip_address
        if self.user_agent:
            data += hashlib.sha256(self.user_agent.encode()).hexdigest()[:16]

        # Add details hash
        details_str = json.dumps(self.details, sort_keys=True)
        data += hashlib.sha256(details_str.encode()).hexdigest()

        # Create HMAC
        import hmac

        return hmac.new(secret_key, data.encode(), hashlib.sha256).hexdigest()

    def verify_checksum(self, secret_key: bytes) -> bool:
        """Verify record integrity."""
        if not self.checksum:
            return False
        return self.checksum == self.calculate_checksum(secret_key)


class AuditDatabase:
    """SQLite-based audit database with encryption and integrity protection."""

    def __init__(
        self, db_path: Path | None = None, encryption_key: bytes | None = None
    ):
        """Initialize audit database."""
        self.db_path = (
            db_path or Path.home() / ".opera_cloud_mcp" / "audit" / "audit.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Initialize encryption
        if encryption_key:
            self.encryption_key = encryption_key
        else:
            self.encryption_key = self._get_or_create_encryption_key()

        # Create proper Fernet key (must be 32 bytes, URL-safe base64 encoded)
        if len(self.encryption_key) == 32:
            # Convert raw 32 bytes to Fernet key format
            import base64

            fernet_key = base64.urlsafe_b64encode(self.encryption_key)
        else:
            # Generate new Fernet-compatible key
            fernet_key = Fernet.generate_key()

        self.cipher = Fernet(fernet_key)

        # Database lock for thread safety
        self._lock = threading.RLock()

        # Initialize SQLModel engine
        self.engine = create_engine(f"sqlite:///{self.db_path}")

        # Initialize database schema
        self._init_database()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for audit records."""
        key_file = self.db_path.parent / ".audit_key"

        if key_file.exists():
            try:
                with key_file.open("rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load audit encryption key: {e}")

        # Generate new key
        key = secrets.token_bytes(32)
        try:
            key_file.write_bytes(key)
            key_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save audit encryption key: {e}")

        return key

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._lock:
            # Create tables using SQLModel
            SQLModel.metadata.create_all(self.engine)

            # Also maintain compatibility with existing SQLite approach
            conn = sqlite3.connect(str(self.db_path))
            try:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=FULL")
                conn.execute("PRAGMA foreign_keys=ON")

                # Create audit records table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_records (
                        id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        client_id_hash TEXT NOT NULL,
                        ip_address TEXT,
                        user_agent_hash TEXT,
                        success INTEGER NOT NULL,
                        risk_score INTEGER DEFAULT 0,
                        session_id TEXT,
                        encrypted_details BLOB,
                        checksum TEXT NOT NULL,
                        created_at REAL DEFAULT (julianday('now'))
                    )
                """)

                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON audit_records(timestamp DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_event_type
                    ON audit_records(event_type, timestamp DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_client_id
                    ON audit_records(client_id_hash, timestamp DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_success
                    ON audit_records(success, timestamp DESC)
                """)

                # Create audit log for database operations
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS database_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        operation TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        record_id TEXT,
                        checksum TEXT,
                        created_at REAL DEFAULT (julianday('now'))
                    )
                """)

                conn.commit()

            finally:
                conn.close()

    def insert_record(self, record: AuditRecord) -> bool:
        """Insert audit record with integrity protection."""
        try:
            with self._lock:
                # Calculate checksum
                record.checksum = record.calculate_checksum(self.encryption_key)

                # Encrypt sensitive details
                encrypted_details = None
                if record.details:
                    details_json = json.dumps(record.details)
                    encrypted_details = self.cipher.encrypt(details_json.encode())

                # Hash user agent for storage
                user_agent_hash = None
                if record.user_agent:
                    user_agent_hash = hashlib.sha256(
                        record.user_agent.encode()
                    ).hexdigest()[:32]

                conn = sqlite3.connect(str(self.db_path))
                try:
                    conn.execute(
                        """
                        INSERT INTO audit_records (
                            id, timestamp, event_type, client_id_hash, ip_address,
                            user_agent_hash, success, risk_score, session_id,
                            encrypted_details, checksum
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            record.id,
                            record.timestamp.timestamp(),
                            record.event_type,
                            record.client_id_hash,
                            record.ip_address,
                            user_agent_hash,
                            1 if record.success else 0,
                            record.risk_score,
                            record.session_id,
                            encrypted_details,
                            record.checksum,
                        ),
                    )

                    # Log database operation
                    conn.execute(
                        """
                        INSERT INTO database_audit (
                            timestamp, operation, table_name, record_id, checksum
                        )
                        VALUES (?, 'INSERT', 'audit_records', ?, ?)
                        """,
                        (datetime.now(UTC).timestamp(), record.id, record.checksum),
                    )

                    conn.commit()
                    return True

                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"Failed to insert audit record: {e}")
            return False

    def insert_record_sqlmodel(self, record: AuditRecord) -> bool:
        """Insert audit record using SQLModel."""
        try:
            with self._lock:
                # Create SQLModel instance
                db_record = AuditRecordDB(
                    id=record.id,
                    timestamp=record.timestamp,
                    event_type=record.event_type,
                    client_id_hash=record.client_id_hash,
                    ip_address=record.ip_address,
                    user_agent_hash=(
                        hashlib.sha256(record.user_agent.encode()).hexdigest()[:32]
                        if record.user_agent
                        else None
                    ),
                    success=record.success,
                    risk_score=record.risk_score,
                    session_id=record.session_id,
                    encrypted_details=(
                        self.cipher.encrypt(json.dumps(record.details).encode())
                        if record.details
                        else None
                    ),
                    checksum=record.calculate_checksum(self.encryption_key),
                    created_at=datetime.now(UTC),
                )

                # Insert using SQLModel
                with Session(self.engine) as session:
                    session.add(db_record)
                    session.commit()

                return True

        except Exception as e:
            logger.error(f"Failed to insert audit record via SQLModel: {e}")
            return False

    def _build_query_conditions(
        self,
        start_time: datetime | None,
        end_time: datetime | None,
        event_types: set[str] | None,
        client_id_hash: str | None,
        success_only: bool | None,
    ) -> tuple[str, list[str | int | float]]:
        """Build query conditions and parameters."""
        conditions = []
        params: list[str | int | float] = []

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.timestamp())

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.timestamp())

        if event_types:
            placeholders = ",".join("?" * len(event_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)

        if client_id_hash:
            conditions.append("client_id_hash = ?")
            params.append(client_id_hash)

        if success_only is not None:
            conditions.append("success = ?")
            params.append(1 if success_only else 0)

        return "WHERE " + " AND ".join(conditions) if conditions else "", params

    def _build_query(
        self, where_clause: str, limit: int
    ) -> tuple[str, list[str | int | float]]:
        """Build the complete query with parameters."""
        base_query = """
            SELECT id, timestamp, event_type, client_id_hash, ip_address,
                   user_agent_hash, success, risk_score, session_id,
                   encrypted_details, checksum
            FROM audit_records
        """

        # Add WHERE clause if needed
        if where_clause:
            query = base_query + f"\n{where_clause}\nORDER BY timestamp DESC\nLIMIT ?"
        else:
            query = base_query + "\nORDER BY timestamp DESC\nLIMIT ?"

        return query, [limit]

    def _decrypt_record_details(
        self, encrypted_details: bytes | None
    ) -> dict[str, Any]:
        """Decrypt record details."""
        details = {}
        if encrypted_details:
            try:
                decrypted_data = self.cipher.decrypt(encrypted_details)
                details = json.loads(decrypted_data.decode())
            except Exception as e:
                logger.warning(f"Failed to decrypt audit details: {e}")
        return details

    def _convert_row_to_record(self, row: tuple) -> AuditRecord | None:
        """Convert database row to AuditRecord object."""
        # Decrypt details
        details = self._decrypt_record_details(row[9])  # encrypted_details

        record = AuditRecord(
            id=row[0],
            timestamp=datetime.fromtimestamp(row[1], tz=UTC),
            event_type=row[2],
            client_id_hash=row[3],
            ip_address=row[4],
            user_agent=None,  # Not stored, only hash
            success=bool(row[6]),
            risk_score=row[7],
            session_id=row[8],
            details=details,
            checksum=row[10],
        )

        # Verify integrity
        if record.verify_checksum(self.encryption_key):
            return record
        else:
            logger.warning(f"Audit record integrity check failed: {record.id}")
            return None

    def query_records(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: set[str] | None = None,
        client_id_hash: str | None = None,
        success_only: bool | None = None,
        limit: int = 1000,
    ) -> list[AuditRecord]:
        """Query audit records with filtering."""
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    # Build query conditions
                    where_clause, params = self._build_query_conditions(
                        start_time, end_time, event_types, client_id_hash, success_only
                    )

                    # Build complete query
                    query, query_params = self._build_query(where_clause, limit)
                    params.extend(query_params)

                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()

                    # Convert to AuditRecord objects
                    records = []
                    for row in rows:
                        record = self._convert_row_to_record(row)
                        if record:
                            records.append(record)

                    return records

                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"Failed to query audit records: {e}")
            return []

    def get_statistics(self, hours: int = 24) -> dict[str, Any]:
        """Get audit statistics for monitoring."""
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    cutoff_time = (
                        datetime.now(UTC) - timedelta(hours=hours)
                    ).timestamp()

                    # Total records
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM audit_records WHERE timestamp >= ?",
                        (cutoff_time,),
                    )
                    total_records = cursor.fetchone()[0]

                    # Success/failure counts
                    cursor = conn.execute(
                        """
                        SELECT success, COUNT(*)
                        FROM audit_records
                        WHERE timestamp >= ?
                        GROUP BY success
                    """,
                        (cutoff_time,),
                    )

                    success_counts = {row[0]: row[1] for row in cursor.fetchall()}

                    # Event type distribution
                    cursor = conn.execute(
                        """
                        SELECT event_type, COUNT(*)
                        FROM audit_records
                        WHERE timestamp >= ?
                        GROUP BY event_type
                        ORDER BY COUNT(*) DESC
                    """,
                        (cutoff_time,),
                    )

                    event_types = dict(cursor.fetchall())

                    # Risk distribution
                    cursor = conn.execute(
                        """
                        SELECT
                            CASE
                                WHEN risk_score = 0 THEN 'low'
                                WHEN risk_score < 50 THEN 'medium'
                                ELSE 'high'
                            END as risk_level,
                            COUNT(*)
                        FROM audit_records
                        WHERE timestamp >= ?
                        GROUP BY risk_level
                    """,
                        (cutoff_time,),
                    )

                    risk_distribution = dict(cursor.fetchall())

                    # Unique clients
                    cursor = conn.execute(
                        """
                        SELECT COUNT(DISTINCT client_id_hash)
                        FROM audit_records
                        WHERE timestamp >= ?
                    """,
                        (cutoff_time,),
                    )
                    unique_clients = cursor.fetchone()[0]

                    return {
                        "period_hours": hours,
                        "total_records": total_records,
                        "successful_events": success_counts.get(1, 0),
                        "failed_events": success_counts.get(0, 0),
                        "success_rate": (
                            success_counts.get(1, 0) / max(1, total_records)
                        )
                        * 100,
                        "event_types": event_types,
                        "risk_distribution": risk_distribution,
                        "unique_clients": unique_clients,
                        "database_path": str(self.db_path),
                        "generated_at": datetime.now(UTC).isoformat(),
                    }

                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {"error": str(e)}

    def cleanup_old_records(self, days: int = 90) -> int:
        """Clean up old audit records."""
        try:
            with self._lock:
                cutoff_time = (datetime.now(UTC) - timedelta(days=days)).timestamp()

                conn = sqlite3.connect(str(self.db_path))
                try:
                    cursor = conn.execute(
                        "DELETE FROM audit_records WHERE timestamp < ?", (cutoff_time,)
                    )
                    deleted_count = cursor.rowcount

                    # Also clean up database audit log
                    conn.execute(
                        "DELETE FROM database_audit WHERE timestamp < ?", (cutoff_time,)
                    )

                    # Log cleanup operation
                    conn.execute(
                        """
                        INSERT INTO database_audit
                        (timestamp, operation, table_name, record_id)
                        VALUES (?, 'CLEANUP', 'audit_records', ?)
                        """,
                        (datetime.now(UTC).timestamp(), str(deleted_count)),
                    )

                    conn.commit()

                    logger.info(f"Cleaned up {deleted_count} old audit records")
                    return deleted_count

                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"Failed to cleanup audit records: {e}")
            return 0

    def _verify_record_integrity(self, row: tuple, conn: sqlite3.Connection) -> bool:
        """Verify the integrity of a single audit record."""
        try:
            # Decrypt and verify each record
            details = {}
            if row[9]:  # encrypted_details
                decrypted_data = self.cipher.decrypt(row[9])
                details = json.loads(decrypted_data.decode())

            record = AuditRecord(
                id=row[0],
                timestamp=datetime.fromtimestamp(row[1], tz=UTC),
                event_type=row[2],
                client_id_hash=row[3],
                ip_address=row[4],
                user_agent=None,
                success=bool(row[6]),
                risk_score=row[7],
                session_id=row[8],
                details=details,
                checksum=row[10],
            )

            return record.verify_checksum(self.encryption_key)
        except Exception:
            return False

    def _check_all_records(self, conn: sqlite3.Connection) -> tuple[int, int]:
        """Check all records for integrity and return (valid_count, invalid_count)."""
        cursor = conn.execute("""
            SELECT id, timestamp, event_type, client_id_hash, ip_address,
                   user_agent_hash, success, risk_score, session_id,
                   encrypted_details, checksum
            FROM audit_records
            ORDER BY timestamp DESC
            LIMIT 1000
        """)

        valid_records = 0
        invalid_records = 0

        for row in cursor.fetchall():
            if self._verify_record_integrity(row, conn):
                valid_records += 1
            else:
                invalid_records += 1

        return valid_records, invalid_records

    def verify_database_integrity(self) -> dict[str, Any]:
        """Verify database integrity and detect tampering."""
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    # Check all records for integrity
                    cursor = conn.execute("SELECT COUNT(*) FROM audit_records")
                    total_records = cursor.fetchone()[0]

                    valid_records, invalid_records = self._check_all_records(conn)

                    return {
                        "total_records": total_records,
                        "checked_records": valid_records + invalid_records,
                        "valid_records": valid_records,
                        "invalid_records": invalid_records,
                        "integrity_percentage": (
                            valid_records / max(1, valid_records + invalid_records)
                        )
                        * 100,
                        "database_healthy": invalid_records == 0,
                        "checked_at": datetime.now(UTC).isoformat(),
                    }

                finally:
                    conn.close()

        except Exception as e:
            logger.error(f"Failed to verify database integrity: {e}")
            return {"error": str(e), "database_healthy": False}


class AuditLogger:
    """High-level audit logging interface."""

    def __init__(
        self, db_path: Path | None = None, encryption_key: bytes | None = None
    ):
        """Initialize audit logger."""
        self.database = AuditDatabase(db_path, encryption_key)
        self._session_counter = 0
        self._session_prefix = secrets.token_urlsafe(8)

    def log_authentication_event(
        self,
        event_type: str,
        client_id: str,
        success: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
        risk_score: int = 0,
    ) -> bool:
        """Log authentication event."""
        try:
            # Generate unique session-scoped record ID
            self._session_counter += 1
            session_part = f"{self._session_prefix}_{self._session_counter:06d}"
            token_part = secrets.token_urlsafe(8)
            record_id = f"{session_part}_{token_part}"

            # Hash client ID for privacy
            client_id_hash = hashlib.sha256(f"client_{client_id}".encode()).hexdigest()[
                :16
            ]

            record = AuditRecord(
                id=record_id,
                timestamp=datetime.now(UTC),
                event_type=event_type,
                client_id_hash=client_id_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                details=details or {},
                risk_score=risk_score,
                session_id=f"{self._session_prefix}_{int(datetime.now(UTC).timestamp())}",
            )

            return self.database.insert_record(record)

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def get_audit_trail(
        self,
        client_id: str | None = None,
        hours: int = 24,
        event_types: set[str] | None = None,
        success_only: bool | None = None,
    ) -> list[AuditRecord]:
        """Get audit trail for analysis."""
        start_time = datetime.now(UTC) - timedelta(hours=hours)
        client_id_hash = None

        if client_id:
            client_id_hash = hashlib.sha256(f"client_{client_id}".encode()).hexdigest()[
                :16
            ]

        return self.database.query_records(
            start_time=start_time,
            event_types=event_types,
            client_id_hash=client_id_hash,
            success_only=success_only,
        )

    def get_security_report(self, hours: int = 24) -> dict[str, Any]:
        """Generate security report from audit data."""
        statistics = self.database.get_statistics(hours)

        # Get recent high-risk events
        high_risk_events = self.database.query_records(
            start_time=datetime.now(UTC) - timedelta(hours=hours), limit=100
        )
        high_risk_events = [e for e in high_risk_events if e.risk_score >= 50]

        # Detect patterns
        failed_auth_count = statistics.get("failed_events", 0)
        total_events = statistics.get("total_records", 1)
        failure_rate = (failed_auth_count / max(1, total_events)) * 100

        threat_level = "low"
        if failure_rate > 20 or len(high_risk_events) > 10:
            threat_level = "high"
        elif failure_rate > 10 or len(high_risk_events) > 5:
            threat_level = "medium"

        return (
            statistics
            | {
                "high_risk_events": len(high_risk_events),
                "failure_rate_percent": failure_rate,
                "threat_level": threat_level,
            }
            | {
                "recommendations": self._generate_recommendations(
                    statistics, high_risk_events
                )
            }
        )

    def _generate_recommendations(
        self, statistics: dict[str, Any], high_risk_events: list[AuditRecord]
    ) -> list[str]:
        """Generate security recommendations based on audit data."""
        recommendations = []

        failure_rate = (
            statistics.get("failed_events", 0)
            / max(1, statistics.get("total_records", 1))
        ) * 100

        if failure_rate > 15:
            recommendations.append(
                "High authentication failure rate detected - review client credentials"
            )

        if len(high_risk_events) > 5:
            recommendations.append(
                "Multiple high-risk events detected - investigate suspicious activity"
            )

        if statistics.get("unique_clients", 0) > 10:
            recommendations.append(
                "Multiple unique clients detected - verify all clients are authorized"
            )

        # Check for suspicious patterns in high-risk events
        if high_risk_events:
            ip_addresses = {e.ip_address for e in high_risk_events if e.ip_address}
            if len(ip_addresses) > 3:
                recommendations.append(
                    "Auth attempts from multiple IPs - consider IP restrictions"
                )

        if not recommendations:
            recommendations.append("No immediate security concerns detected")

        return recommendations


# Global audit logger instance
audit_logger = AuditLogger()
