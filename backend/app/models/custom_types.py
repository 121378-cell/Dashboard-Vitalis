from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from app.utils.crypto import decrypt_text, encrypt_text


class EncryptedString(TypeDecorator):
    """String column that automatically encrypts on save and decrypts on load."""
    impl = String

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_text(value)
