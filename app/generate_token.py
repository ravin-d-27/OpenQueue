import hashlib
import secrets

token = "oq_live_" + secrets.token_urlsafe(32)
token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

print("TOKEN:", token)
print("TOKEN_HASH:", token_hash)
