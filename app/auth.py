import hashlib
import uuid


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return str(uuid.uuid4())


def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(ch.isupper() for ch in password):
        return False
    if not any(ch.islower() for ch in password):
        return False
    if not any(ch.isdigit() for ch in password):
        return False
    return True


def is_valid_phone(phone_number: str) -> bool:
    return phone_number.isdigit() and len(phone_number) >= 10