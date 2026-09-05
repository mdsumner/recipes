"""Fetch a page as text with a browser-like User-Agent."""

import requests

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 recipes-harvest/0.1"
)


def fetch(url, timeout=30):
    resp = requests.get(
        url,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"},
        timeout=timeout,
        allow_redirects=True,
    )
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text, resp.url
