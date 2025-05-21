"""
Repository-related exception classes.
"""


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class ConnectionError(RepositoryError):
    """Exception raised when there's an issue connecting to the repository."""
    pass


class QueryError(RepositoryError):
    """Exception raised when there's an issue executing a query."""
    pass


class DataSerializationError(RepositoryError):
    """Exception raised when there's an issue serializing or deserializing data."""
    pass 