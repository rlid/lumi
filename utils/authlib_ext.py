import json
import time
from urllib.parse import urlparse

from authlib.common.urls import add_params_to_qs
from authlib.jose import jwt, JsonWebSignature
from authlib.jose.errors import BadSignatureError
from authlib.oauth2.rfc7523.assertion import sign_jwt_bearer_assertion


# Note that the current implementation AuthLib seems to require SameSite setting for the session cookie set to "None"
#
# See https://www.bscotch.net/post/sign-in-with-apple-implementation-hurdles (extract below)
#
# "Let's say you're using cookies for some important purpose, like session management. When Apple redirects the user
# back to your site to complete the authentication loop, you're going to want your user's cookies to come along for the
# ride so that you can match up session data (or whatever is stored in those cookies) to the login results. This means
# you need "cross-origin" cookies.
# (This "cross-origin" terminology is a bit confusing, since the cookies are always for your site. It's the request that
# is cross-origin.)
# Cookies have an optional parameter called "SameSite" that can be set to "lax" or "strict". "Strict" cookies don't
# travel with cross-origin requests at all, which would prevent you from getting cookie values via any OAuth2 redirect,
# no matter the provider. This is where "lax" cookies come in: they can still carry your cookies cross-origin. However,
# the browser only sends lax cookies along with GET requests: while lax cookies can be used for standard OAuth redirects
# they cannot be used with Apple's POST-based approach.
# So what's a dev to do? You could simply skip the "SameSite" field for any cookies required for the login process, thus
# allowing cross-origin cookies for all requests (whether by GET or by POST), but that would generally reduce your
# site's security."


def jws_compact_serialize_timed(payload, key, seconds_to_exp, alg='HS256'):
    protected = {
        'alg': alg,
        'crit': ['exp'],
        "exp": round(time.time()) + seconds_to_exp
    }
    jws = JsonWebSignature()
    return jws.serialize_compact(protected, json.dumps(payload), key).decode()


def jws_compact_deserialize_timed(compact, key):
    jws = JsonWebSignature()
    data = jws.deserialize_compact(compact, key)
    payload = json.loads(data.payload)

    expiry = data.header.get('exp')
    if expiry is None:
        raise BadSignatureError('Missing "exp" in header')

    try:
        expiry = int(expiry)
    except ValueError:
        raise BadSignatureError('"exp" is not an int')

    if expiry < round(time.time()):
        raise BadSignatureError("Signature expired")

    return payload


class ApplePrivateKeyJWT:
    name = 'apple_private_key_jwt'

    def __init__(self, token_endpoint=None, claims=None,
                 apple_key_id=None, apple_team_id=None):
        self.token_endpoint = token_endpoint
        self.claims = claims
        self.apple_key_id = apple_key_id
        self.apple_team_id = apple_team_id

    def sign(self, auth, token_endpoint):
        # print(f"auth = {auth}")
        # print(f"auth.client_id = {auth.client_id}")
        # print(f"auth.client_secret = {auth.client_secret}")
        # print(f"auth.auth_method = {auth.auth_method}")
        url = urlparse(token_endpoint)
        return sign_jwt_bearer_assertion(
            key=auth.client_secret,  # private key
            alg='ES256',  # header:alg
            header={'kid': self.apple_key_id},  # header:kid
            issuer=self.apple_team_id,  # payload:iss
            audience=f"{url.scheme}://{url.netloc}",  # payload:aud (= https://appleid.apple.com)
            subject=auth.client_id,  # payload:sub
            claims=self.claims  # payload:other (if any)
        )

    def __call__(self, auth, method, uri, headers, body):
        # print(f"auth = {auth}")
        # print(f"auth.client_id = {auth.client_id}")
        # print(f"auth.client_secret = {auth.client_secret}")
        # print(f"auth.auth_method = {auth.auth_method}")
        # print(f"method = {method}")
        token_endpoint = self.token_endpoint
        if not token_endpoint:
            token_endpoint = uri

        client_secret = self.sign(auth, token_endpoint)
        decoded_client_secret = jwt.decode(client_secret, key=auth.client_secret)
        # print(f'decoded_client_secret.header = {decoded_client_secret.header}')
        # print(f'decoded_client_secret(.payload) = {decoded_client_secret}')
        # print(f'decoded_client_secret.options = {decoded_client_secret.options}')
        # print(f'decoded_client_secret.params = {decoded_client_secret.params}')

        body = add_params_to_qs(body or '', [
            ('client_id', auth.client_id),
            ('client_secret', client_secret)
        ])
        # print(f"uri = {uri}")
        # print(f"headers = {headers}")
        # print(f"body = {body}")
        return uri, headers, body
