"""
core/vault.py — AES-256-CBC encryption for local secrets.
Used to encrypt Supabase token when stored in config.json.
Pattern reused from LuxeClaw Deployer.
"""

import base64
import hashlib
import os
import platform


def _derive_key(password: str = "") -> bytes:
    """Derive a 32-byte key from machine identity + optional password."""
    # Use hostname + MAC as base salt (machine-bound)
    import uuid
    salt = f"{platform.node()}-{uuid.getnode():012x}-gitquicktool"
    if password:
        salt += f"-{password}"
    return hashlib.sha256(salt.encode("utf-8")).digest()


def encrypt(plaintext: str, password: str = "") -> str:
    """Encrypt a string with AES-256-CBC. Returns base64-encoded ciphertext."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    key = _derive_key(password)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    # Prepend IV to ciphertext
    return base64.b64encode(iv + ct).decode("ascii")


def decrypt(ciphertext_b64: str, password: str = "") -> str:
    """Decrypt a base64-encoded AES-256-CBC ciphertext."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    key = _derive_key(password)
    raw = base64.b64decode(ciphertext_b64)
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """Check if a value looks like our encrypted format (base64, >= 32 bytes)."""
    try:
        raw = base64.b64decode(value)
        return len(raw) >= 32  # IV (16) + at least one block (16)
    except Exception:
        return False
