class PackagingServiceError(Exception):
    """Base exception for packaging service errors."""
    pass


class OrderNotFoundError(PackagingServiceError):
    """Raised when an order cannot be found by ID or order number."""
    pass


class EmptyOrderError(PackagingServiceError):
    """Raised when an order contains zero items to pack."""
    pass

