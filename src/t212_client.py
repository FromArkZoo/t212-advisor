import base64
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests

from src.config import T212_API_KEY, T212_API_SECRET, T212_BASE_URL, DATA_DIR


class T212Client:
    def __init__(self, api_key=None, api_secret=None, base_url=None, data_dir=None):
        self.api_key = api_key or T212_API_KEY
        self.api_secret = api_secret or T212_API_SECRET
        self.base_url = (base_url or T212_BASE_URL).rstrip("/")
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._rate_limit_reset = 0

    def _get_latest_file(self, prefix: str) -> Path | None:
        files = sorted(self.data_dir.glob(f"{prefix}_*.json"))
        return files[-1] if files else None

    def _load_cached(self, prefix: str):
        path = self._get_latest_file(prefix)
        if path:
            with open(path) as f:
                return json.load(f)
        return None

    def _api_headers(self) -> dict:
        if not self.api_key:
            return {}
        if self.api_secret:
            creds = base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
            return {"Authorization": f"Basic {creds}"}
        return {"Authorization": self.api_key}

    def _api_get(self, endpoint: str, params: dict = None) -> dict:
        now = time.time()
        if now < self._rate_limit_reset:
            time.sleep(self._rate_limit_reset - now)

        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = self.base_url + "/" + endpoint.lstrip("/")

        resp = requests.get(url, headers=self._api_headers(), params=params, timeout=30)

        remaining = resp.headers.get("x-ratelimit-remaining")
        reset = resp.headers.get("x-ratelimit-reset")
        if remaining is not None and int(remaining) == 0 and reset:
            self._rate_limit_reset = time.time() + int(reset)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", reset or "5"))
            time.sleep(retry_after)
            return self._api_get(endpoint, params)

        resp.raise_for_status()
        return resp.json()

    def _paginate(self, endpoint: str, limit: int = 50) -> list:
        results = []
        params = {"limit": limit}
        current_endpoint = endpoint

        while True:
            data = self._api_get(current_endpoint, params)
            if "items" in data:
                results.extend(data["items"])

            next_path = data.get("nextPagePath")
            if not next_path:
                break

            if next_path.startswith("http"):
                current_endpoint = next_path
            else:
                clean = next_path.lstrip("/")
                if not clean.startswith("api/"):
                    clean = "api/v0/" + clean
                current_endpoint = self.base_url.rsplit("/api/", 1)[0] + "/" + clean
            params = None

        return results

    def get_account_summary(self) -> dict:
        cached = self._load_cached("account_summary")
        if cached:
            return cached
        return self._api_get("/equity/account/summary")

    def get_positions(self) -> list:
        cached = self._load_cached("positions")
        if cached:
            return cached
        return self._api_get("/equity/portfolio")

    def get_orders(self) -> list:
        cached = self._load_cached("orders")
        if cached:
            return cached
        return self._paginate("/equity/history/orders")

    def get_dividends(self) -> list:
        cached = self._load_cached("dividends")
        if cached:
            return cached
        return self._paginate("/equity/history/dividends")

    def get_transactions(self) -> list:
        cached = self._load_cached("transactions")
        if cached:
            return cached
        return self._paginate("/equity/history/transactions")

    def save_snapshot(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        endpoints = {
            "account_summary": "/equity/account/summary",
            "positions": "/equity/portfolio",
        }
        paginated = {
            "orders": "/equity/history/orders",
            "dividends": "/equity/history/dividends",
            "transactions": "/equity/history/transactions",
        }

        self.data_dir.mkdir(parents=True, exist_ok=True)

        for prefix, ep in endpoints.items():
            data = self._api_get(ep)
            path = self.data_dir / f"{prefix}_{ts}.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        for prefix, ep in paginated.items():
            data = self._paginate(ep)
            path = self.data_dir / f"{prefix}_{ts}.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
