"""Одноразовые коды (TOTP, RFC 6238) для Google Authenticator и подобных приложений."""
import base64
import hashlib
import hmac
import secrets
import struct
import time


def new_secret():
    return base64.b32encode(secrets.token_bytes(10)).decode()  # 16 символов


def _code(secret, counter):
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return "%06d" % number


def verify(secret, code, window=1):
    code = (code or "").strip().replace(" ", "")
    if not secret or not code.isdigit() or len(code) != 6:
        return False
    counter = int(time.time()) // 30
    return any(hmac.compare_digest(_code(secret, counter + d), code) for d in range(-window, window + 1))


def uri(secret, name):
    return "otpauth://totp/School:%s?secret=%s&issuer=School" % (name, secret)
