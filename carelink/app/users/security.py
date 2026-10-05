import base64
import hashlib
import hmac
import secrets


ALGORITHM = "sha256"
ITERATIONS = 600_000
SALT_LENGTH = 16


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    if not password:
        raise ValueError("Password cannot be empty")

    salt = secrets.token_bytes(SALT_LENGTH)

    derived_key = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )

    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_key = base64.b64encode(derived_key).decode("ascii")

    return (
        f"pbkdf2_{ALGORITHM}${ITERATIONS}"
        f"${encoded_salt}${encoded_key}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    if not isinstance(password, str):
        return False

    if not isinstance(password_hash, str):
        return False

    try:
        algorithm_part, iterations_text, encoded_salt, encoded_key = (
            password_hash.split("$", maxsplit=3)
        )

        if not algorithm_part.startswith("pbkdf2_"):
            return False

        algorithm = algorithm_part.removeprefix("pbkdf2_")

        if algorithm != ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = base64.b64decode(encoded_salt, validate=True)
        expected_key = base64.b64decode(encoded_key, validate=True)

    except (ValueError, base64.binascii.Error):
        return False

    actual_key = hashlib.pbkdf2_hmac(
        algorithm,
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(actual_key, expected_key)
