"""
Service layer for the core app.

All business logic resides here. Views delegate to services.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import logging
import time

import stripe
from django.conf import settings
from supabase import Client, create_client

from .utils import serialize_uuid

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for all services in the core app."""

    def __init__(self) -> None:
        self._setup()

    def _setup(self) -> None:
        """Initialization hook for subclasses."""
        pass


class SupabaseService(BaseService):
    """
    Service for interacting with Supabase.

    Uses Singleton pattern to reuse client connection.
    Enforces RLS-First policy: all patient-data queries filter by parent_id.
    """

    _instance: Optional["SupabaseService"] = None
    _client: Optional[Client] = None

    def __new__(cls) -> "SupabaseService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _setup(self) -> None:
        """Initialize Supabase client with settings."""
        if self._client is None:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY,
            )
            logger.info("Supabase client initialized")

    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            raise RuntimeError("Supabase client not initialized")
        return self._client

    def query_table(
        self,
        table_name: str,
        user_id: UUID,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query a Supabase table with automatic RLS filtering.

        All queries are filtered by parent_id to enforce RLS-First policy.

        Args:
            table_name: Name of the Supabase table
            user_id: UUID of the authenticated user (used for RLS filter)
            columns: Columns to select (default: "*")
            filters: Additional filters to apply

        Returns:
            List of records from the table
        """
        parent_id = serialize_uuid(user_id)
        query = self.client.table(table_name).select(columns).eq("parent_id", parent_id)

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        try:
            response = query.execute()
            logger.info("Query executed: table=%s, user_id=%s", table_name, serialize_uuid(user_id))
            return response.data or []
        except Exception as e:
            logger.error("Query failed: table=%s, error=%s", table_name, str(e))
            raise

    def insert_record(
        self,
        table_name: str,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Insert a record into a Supabase table with audit logging.

        Args:
            table_name: Name of the Supabase table
            user_id: UUID of the authenticated user
            data: Record data to insert

        Returns:
            The inserted record

        Raises:
            ValueError: If data is invalid
        """
        data["parent_id"] = serialize_uuid(user_id)

        try:
            response = self.client.table(table_name).insert(data).execute()
            result = response.data[0] if response.data else {}

            audit_service = AuditLogService()
            audit_service.log(
                user_id=user_id,
                action="CREATE",
                table_name=table_name,
                record_id=result.get("id"),
                payload=data,
            )

            logger.info("Record inserted: table=%s, user_id=%s", table_name, serialize_uuid(user_id))
            return result
        except Exception as e:
            logger.error("Insert failed: table=%s, error=%s", table_name, str(e))
            raise

    def update_record(
        self,
        table_name: str,
        user_id: UUID,
        record_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a record in a Supabase table with audit logging.

        Args:
            table_name: Name of the Supabase table
            user_id: UUID of the authenticated user
            record_id: UUID of the record to update
            data: Updated data

        Returns:
            The updated record
        """
        parent_id = serialize_uuid(user_id)

        try:
            response = (
                self.client.table(table_name)
                .update(data)
                .eq("id", serialize_uuid(record_id))
                .eq("parent_id", parent_id)
                .execute()
            )
            result = response.data[0] if response.data else {}

            audit_service = AuditLogService()
            audit_service.log(
                user_id=user_id,
                action="UPDATE",
                table_name=table_name,
                record_id=record_id,
                payload=data,
            )

            logger.info("Record updated: table=%s, record_id=%s", table_name, serialize_uuid(record_id))
            return result
        except Exception as e:
            logger.error("Update failed: table=%s, error=%s", table_name, str(e))
            raise

    def delete_record(
        self,
        table_name: str,
        user_id: UUID,
        record_id: UUID,
    ) -> bool:
        """
        Delete a record from a Supabase table with audit logging.

        Args:
            table_name: Name of the Supabase table
            user_id: UUID of the authenticated user
            record_id: UUID of the record to delete

        Returns:
            True if deletion was successful
        """
        parent_id = serialize_uuid(user_id)

        try:
            response = (
                self.client.table(table_name)
                .delete()
                .eq("id", serialize_uuid(record_id))
                .eq("parent_id", parent_id)
                .execute()
            )

            audit_service = AuditLogService()
            audit_service.log(
                user_id=user_id,
                action="DELETE",
                table_name=table_name,
                record_id=record_id,
                payload={"deleted": True},
            )

            logger.info("Record deleted: table=%s, record_id=%s", table_name, serialize_uuid(record_id))
            return True
        except Exception as e:
            logger.error("Delete failed: table=%s, error=%s", table_name, str(e))
            raise

    def query_with_retry(
        self,
        table_name: str,
        user_id: UUID,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """
        Query with automatic retry when Supabase is unavailable.

        Args:
            table_name: Name of the Supabase table
            user_id: UUID of the authenticated user
            columns: Columns to select
            filters: Additional filters
            max_retries: Maximum number of retry attempts
            timeout: Timeout in seconds between retries

        Returns:
            List of records from the table
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.query_table(table_name, user_id, columns, filters)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Query attempt %d/%d failed, retrying: error=%s",
                    attempt + 1,
                    max_retries,
                    str(e),
                )
                time.sleep(timeout)

        logger.error("All query attempts failed: table=%s, max_retries=%d", table_name, max_retries)
        raise last_error


class StripeService(BaseService):
    """
    Service for interacting with Stripe API.

    Isolates Stripe SDK usage from views and other services.
    """

    def __init__(self) -> None:
        super().__init__()
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def _setup(self) -> None:
        """Initialize Stripe configuration."""
        logger.info("Stripe service initialized")

    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer.

        Args:
            email: Customer email address
            name: Customer name
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with customer data
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            logger.info("Stripe customer created: customer_id=%s", customer.id)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe customer creation failed: error=%s", str(e))
            raise

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "brl",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe PaymentIntent.

        Args:
            amount: Amount in cents (minor units)
            currency: Currency code (default: brl)
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with payment intent data
        """
        try:
            params: Dict[str, Any] = {
                "amount": amount,
                "currency": currency,
                "metadata": metadata or {},
            }
            if customer_id:
                params["customer"] = customer_id

            intent = stripe.PaymentIntent.create(**params)
            logger.info("Payment intent created: intent_id=%s, amount=%d", intent.id, amount)
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status,
            }
        except stripe.error.StripeError as e:
            logger.error("Payment intent creation failed: error=%s", str(e))
            raise


class AuditLogService(BaseService):
    """
    Service for audit logging.

    All write operations on patient data must be logged via this service.
    """

    def log(
        self,
        user_id: UUID,
        action: str,
        table_name: str,
        record_id: Optional[UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            user_id: UUID of the user who performed the action
            action: Type of action (CREATE, UPDATE, DELETE, SYNC)
            table_name: Name of the affected table
            record_id: UUID of the affected record (optional)
            payload: Relevant operation data (snapshot or delta)
        """
        log_entry = {
            "user_id": serialize_uuid(user_id),
            "action": action,
            "metadata": {
                "table_name": table_name,
                "record_id": serialize_uuid(record_id) if record_id else None,
                **(payload or {}),
            },
        }

        logger.info("Audit log entry: user_id=%s, action=%s, table=%s", serialize_uuid(user_id), action, table_name)

        try:
            supabase = SupabaseService()
            supabase.client.table("audit_logs").insert(log_entry).execute()
        except Exception as e:
            logger.error("Audit log write failed: error=%s", str(e))
