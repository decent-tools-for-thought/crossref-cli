from __future__ import annotations

import json
import random
import time
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


class HttpClient:
    def __init__(self, headers: dict[str, str], timeout: float = 30.0) -> None:
        self.headers = headers
        self.timeout = timeout

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        request_url = f"{url}?{query}" if query else url
        request = Request(request_url, headers=self.headers)
        backoff = 1.0
        for attempt in range(5):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code not in {403, 429, 500, 502, 503, 504} or attempt == 4:
                    raise RuntimeError(
                        f"Request failed with HTTP {exc.code}: {request_url}"
                    ) from exc
            except URLError as exc:
                if attempt == 4:
                    reason = str(exc.reason)
                    raise RuntimeError(f"Request failed: {request_url} ({reason})") from exc
            time.sleep(backoff + random.uniform(0.0, backoff * 0.25))
            backoff = min(backoff * 2, 8.0)

    def resolve_url(self, url: str, *, follow_redirects: bool) -> str:
        if follow_redirects:
            request = Request(url, headers=self.headers, method="HEAD")
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return cast(str, response.geturl())
            except HTTPError as exc:
                raise RuntimeError(f"Request failed with HTTP {exc.code}: {url}") from exc
            except URLError as exc:
                reason = str(exc.reason)
                raise RuntimeError(f"Request failed: {url} ({reason})") from exc

        class _NoRedirectHandler(HTTPRedirectHandler):
            def redirect_request(
                self,
                req: Request,
                fp: Any,
                code: int,
                msg: str,
                headers: Any,
                newurl: str,
            ) -> None:
                del req, fp, code, msg, headers, newurl
                return None

        opener = build_opener(_NoRedirectHandler)
        request = Request(url, headers=self.headers, method="HEAD")
        try:
            with opener.open(request, timeout=self.timeout) as response:
                return cast(str, response.geturl())
        except HTTPError as exc:
            location = exc.headers.get("Location")
            if exc.code in {301, 302, 303, 307, 308} and location:
                return location
            raise RuntimeError(f"Request failed with HTTP {exc.code}: {url}") from exc
        except URLError as exc:
            reason = str(exc.reason)
            raise RuntimeError(f"Request failed: {url} ({reason})") from exc
