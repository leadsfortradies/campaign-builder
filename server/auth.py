"""Single-user password login with a signed, expiring session cookie."""

import hashlib
import hmac
import secrets
import time

from . import config

COOKIE = "lft_session"

_secret = (config.SESSION_SECRET or config.APP_PASSWORD or secrets.token_hex(32)).encode()


def _sign(msg):
    return hmac.new(_secret, msg.encode(), hashlib.sha256).hexdigest()


def make_token():
    expires = int(time.time()) + config.SESSION_DAYS * 86400
    return f"{expires}.{_sign(str(expires))}"


def valid_token(token):
    try:
        expires, sig = token.split(".", 1)
        return int(expires) > time.time() and hmac.compare_digest(sig, _sign(expires))
    except (ValueError, AttributeError):
        return False


def check_password(candidate):
    if not config.APP_PASSWORD:
        return False
    return hmac.compare_digest(
        hashlib.sha256(candidate.encode()).digest(),
        hashlib.sha256(config.APP_PASSWORD.encode()).digest(),
    )


LOGIN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f1115;color:#e8eaed;font-family:system-ui,sans-serif}
form{width:min(320px,86vw);display:grid;gap:12px}
input,button{font-size:16px;padding:12px;border-radius:8px;border:1px solid #2a2f3a;background:#171a21;color:inherit}
button{background:#3d7bff;border-color:#3d7bff;cursor:pointer}
.err{color:#ff6b6b;margin:0}
</style></head><body>
<form method="post" action="/login">
<h2 style="margin:0">Campaign Builder</h2>
<input type="password" name="password" placeholder="Password" autofocus autocomplete="current-password">
{error}
<button type="submit">Sign in</button>
</form></body></html>"""
