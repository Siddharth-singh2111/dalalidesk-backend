"""
Work OS support button — token signer.

Mints a short-lived (5 minute) HS256 JWT that names the signed-in person, which
the Holani & Co Work OS support widget (support.holani.co.in) trades for its own
session. The secret never reaches the browser; the route in routes.py only ever
signs for the person who is actually signed in. See migrations / the install
notes for WORKOS_WIDGET_KEY / WORKOS_WIDGET_SECRET.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def workos_widget_token(email: str, name: str, actor=None):
    """A 5-minute Work OS hand-off for the signed-in person, or None when the button is off."""
    key, secret = os.environ.get("WORKOS_WIDGET_KEY"), os.environ.get("WORKOS_WIDGET_SECRET")
    if not key or not secret:
        return None
    now, email = int(time.time()), email.strip().lower()
    p = {"iss": key, "aud": "work-os-widget", "email": email, "name": name or email,
         "iat": now, "exp": now + 300, "jti": secrets.token_urlsafe(16)}
    if actor and actor.get("email") and actor["email"].lower() != email:
        p["act"] = {"email": actor["email"].lower(), "name": actor.get("name") or actor["email"]}
        if actor.get("exp"):
            p["act"]["exp"] = int(actor["exp"])
    enc = lambda o: _b64(json.dumps(o, separators=(",", ":")).encode())
    unsigned = enc({"alg": "HS256", "typ": "JWT"}) + "." + enc(p)
    sig = hmac.new(secret.encode(), unsigned.encode(), hashlib.sha256).digest()
    return unsigned + "." + _b64(sig)
