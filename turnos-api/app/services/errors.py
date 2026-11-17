class DomainError(Exception):
    """Error de regla de negocio. El controlador lo traduce a una respuesta HTTP."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class NotFound(DomainError):
    def __init__(self, message: str):
        super().__init__(message, 404)


class Conflict(DomainError):
    def __init__(self, message: str):
        super().__init__(message, 409)
