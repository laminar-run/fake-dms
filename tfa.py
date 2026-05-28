"""Fake 2FA (TOTP) for DealerDesk 98 - RFC 6238, stdlib only.

The same base32 secret is registered in Minicor's TFA vault and stored in the
workspace config store (`totp_secret`), so an RPA workflow can compute the
current code and enter it here. This is a QA fixture, not a real secret.
"""
import hmac
import hashlib
import base64
import struct
import time

TFA_ENABLED = True
TOTP_SECRET = "LYZUSCUNPYIRTKDYN46HUFHBWIGUOINJ"


def _hotp(secret_b32: str, counter: int) -> str:
    pad = "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(secret_b32 + pad, casefold=True)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def totp_now(secret_b32: str = TOTP_SECRET, step: int = 30) -> str:
    return _hotp(secret_b32, int(time.time()) // step)


def verify(code: str, secret_b32: str = TOTP_SECRET, step: int = 30, window: int = 1) -> bool:
    code = (code or "").strip()
    if not (code.isdigit() and len(code) == 6):
        return False
    counter = int(time.time()) // step
    return any(_hotp(secret_b32, counter + off) == code for off in range(-window, window + 1))
