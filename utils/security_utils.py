import base64
import secrets
from hashlib import blake2b


def hash_string(s, digest_size):
    return base64.urlsafe_b64encode(blake2b(s.encode(), digest_size=digest_size).digest()).decode()


def random_urlsafe(nbytes):
    return secrets.token_urlsafe(nbytes=nbytes)
