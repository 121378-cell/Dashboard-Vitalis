"""
Excepciones personalizadas para el módulo Garmin
"""


class GarminRateLimitError(Exception):
    """
    Excepción lanzada cuando Garmin aplica rate limiting.
    
    Attributes:
        retry_after (datetime): Timestamp cuando se puede reintentar
        message (str): Descripción del error
    """
    
    def __init__(self, message: str, retry_after=None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
    
    def __str__(self):
        if self.retry_after:
            return f"{self.message} (retry after: {self.retry_after})"
        return self.message


class GarminSessionError(Exception):
    """Excepción lanzada cuando hay problemas con la sesión de Garmin."""
    pass


class GarminAuthError(Exception):
    """Excepción lanzada cuando falla la autenticación con Garmin."""
    pass
