"""
Utility functions for the core app.
"""

from uuid import UUID


def serialize_uuid(uuid_obj: UUID) -> str:
    """
    Convert a UUID object to its string representation.

    All UUIDs must be serialized to strings before passing to the Supabase SDK.

    Args:
        uuid_obj: UUID object to serialize

    Returns:
        String representation of the UUID
    """
    return str(uuid_obj)
