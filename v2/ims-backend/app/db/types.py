from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        return decrypt(value)
