"""Thin wrapper around the Upbit REST API used for order execution."""

try:
    import requests
except Exception:  # pragma: no cover - fallback for test env
    requests = None
    import urllib.request as _urlreq
try:
    import jwt
except Exception:  # pragma: no cover - simple JWT replacement
    import base64

    class _FakeJWT:
        @staticmethod
        def encode(payload, secret):
            import json
            header = base64.urlsafe_b64encode(b"{}").decode().rstrip("=")
            body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
            signature = base64.urlsafe_b64encode(b"sig").decode().rstrip("=")
            return ".".join([header, body, signature])

    jwt = _FakeJWT()
import uuid
import hashlib
from urllib.parse import urlencode
from .utils import load_api_keys


class UpbitClient:
    """Minimal Upbit REST API client."""

    BASE_URL = "https://api.upbit.com"

    def __init__(self, access_key: str = None, secret_key: str = None):
        if not access_key or not secret_key:
            access_key, secret_key = load_api_keys()
        self.access_key = access_key
        self.secret_key = secret_key

    def _headers(self, params=None):
        payload = {"access_key": self.access_key, "nonce": str(uuid.uuid4())}
        if params:
            m = hashlib.sha512()
            m.update(urlencode(params).encode())
            payload["query_hash"] = m.hexdigest()
            payload["query_hash_alg"] = "SHA512"
        token = jwt.encode(payload, self.secret_key)
        return {"Authorization": f"Bearer {token}"}

    def get(self, path: str, params=None):
        url = f"{self.BASE_URL}{path}"
        headers = self._headers(params)
        if requests:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        else:
            if params:
                url = f"{url}?{urlencode(params)}"
            req = _urlreq.Request(url, headers=headers)
            with _urlreq.urlopen(req, timeout=10) as r:
                import json
                return json.loads(r.read().decode())

    def post(self, path: str, params=None):
        url = f"{self.BASE_URL}{path}"
        headers = self._headers(params)
        if requests:
            resp = requests.post(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        else:
            data = urlencode(params or {}).encode()
            req = _urlreq.Request(url, data=data, headers=headers)
            with _urlreq.urlopen(req, timeout=10) as r:
                import json
                return json.loads(r.read().decode())

    def place_order(self, market: str, side: str, volume: float, price: float | None, ord_type: str):
        params = {
            "market": market,
            "side": side,
            "ord_type": ord_type,
        }
        if ord_type == "market" and side == "bid":
            params["price"] = str(price)
        elif ord_type == "market" and side == "ask":
            params["volume"] = str(volume)
        else:
            params["volume"] = str(volume)
            if price is not None:
                params["price"] = str(price)
        return self.post("/v1/orders", params)

    def order_info(self, uuid: str):
        return self.get("/v1/order", {"uuid": uuid})

    def orders(self, params=None):
        return self.get("/v1/orders", params or {})

    def order_chance(self, market: str):
        return self.get("/v1/order_chance", {"market": market})

    def get_accounts(self):
        """Return account balances via ``/v1/accounts``."""
        return self.get("/v1/accounts")
