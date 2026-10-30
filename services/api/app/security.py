import base64
import hashlib
import hmac
import json
import os
import secrets
import time


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384,r=8,p=1).hex()
    return salt+':'+digest


def password_ok(password, stored):
    salt, digest = stored.split(':')
    actual = hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
    return hmac.compare_digest(actual,digest)


def secret():
    value = os.getenv('SESSION_SECRET','')
    if len(value) < 32:
        raise RuntimeError('Set SESSION_SECRET to at least 32 random characters')
    return value.encode()


def token(user_id):
    payload = base64.urlsafe_b64encode(json.dumps({'sub':user_id,'exp':int(time.time())+28800}).encode()).decode()
    sig = hmac.new(secret(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig


def subject(value):
    try:
        payload, sig = value.split('.')
        if not hmac.compare_digest(hmac.new(secret(),payload.encode(),hashlib.sha256).hexdigest(),sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data['sub'] if data['exp'] > time.time() else None
    except (ValueError,KeyError,TypeError):
        return None
