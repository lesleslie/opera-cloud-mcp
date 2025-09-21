"""
SQLModel-based audit logging system for OPERA Cloud MCP.

This module provides a modern, SQLModel-based approach to audit logging
with improved maintainability and type safety.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet
from sqlmodel import Session, SQLModel, create_engine, desc, select

from opera_cloud_mcp.auth.audit_logger import AuditRecord
from opera_cloud_mcp.models.common import AuditRecordDB

logger = logging.getLogger(__name__)


class AuditLoggerSQLModel:
    """Modern SQLModel-based audit logger."""

    def __init__(
        self, db_path: Path | None = None, encryption_key: bytes | None = None
    ):
        """Initialize SQLModel-based audit logger."""
        self.db_path = (
            db_path or Path.home() / ".opera_cloud_mcp" / "audit" / "audit.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Initialize encryption
        if encryption_key:
            self.encryption_key = encryption_key
        else:
            self.encryption_key = self._get_or_create_encryption_key()

        # Create Fernet cipher
        if len(self.encryption_key) == 32:
            import base64

            fernet_key = base64.urlsafe_b64encode(self.encryption_key)
        else:
            fernet_key = Fernet.generate_key()

        self.cipher = Fernet(fernet_key)

        # Create engine
        self.engine = create_engine(f"sqlite:///{self.db_path}")

        # Initialize database
        SQLModel.metadata.create_all(self.engine)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key."""
        key_file = self.db_path.parent / ".audit_key"

        if key_file.exists():
            try:
                with key_file.open("rb") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load audit encryption key: {e}")

        # Generate new key
        key = Fernet.generate_key()[:32]  # Take first 32 bytes
        try:
            key_file.write_bytes(key)
            key_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save audit encryption key: {e}")

        return key

    def log_audit_event(self, record: AuditRecord) -> bool:
        """Log an audit event using SQLModel."""
        try:
            # Create database record
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

            # Save to database
            with Session(self.engine) as session:
                session.add(db_record)
                session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def get_audit_events(
        self,
        event_type: str | None = None,
        client_id_hash: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecordDB]:
        """Retrieve audit events using SQLModel."""
        try:
            with Session(self.engine) as session:
                query = select(AuditRecordDB)

                if event_type:
                    query = query.where(AuditRecordDB.event_type == event_type)

                if client_id_hash:
                    query = query.where(AuditRecordDB.client_id_hash == client_id_hash)

                query = query.order_by(desc(AuditRecordDB.timestamp)).limit(limit)

                results = session.exec(query).all()
                return list(results)

        except Exception as e:
            logger.error(f"Failed to retrieve audit events: {e}")
            return []
