"""
Password hashing.

One implementation for the whole backend (API, seed, admin bootstrap). Uses bcrypt
directly: the hashes are the same `$2b$` format passlib produced, so existing
users keep working, and there is no unmaintained wrapper pinning bcrypt.
"""

import hashlib

import bcrypt

# bcrypt ignores bytes beyond 72; recent versions raise instead. Enforced in the
# API schemas too, this is the last line of defence for scripts.
MAX_PASSWORD_BYTES = 72


class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        """
        Hash a plain password.
        @param password: plain text password
        @return: bcrypt hash, ASCII string
        """
        encoded = password.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password longer than {MAX_PASSWORD_BYTES} bytes")
        return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """
        Verify a plain password against a stored hash.
        @return: True when it matches; False for a mismatch or a malformed/oversized input
        """
        if not password or not hashed:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
        except ValueError:
            return False

    @staticmethod
    def fingerprint(hashed: str) -> str:
        """
        A short, non-reversible stamp of a stored hash. Stamped into session and reset tokens
        so that every token issued before a password change stops verifying the moment the
        password changes: other devices are signed out, and a reset link is single-use.
        """
        return hashlib.sha256(hashed.encode("ascii")).hexdigest()[:16]
