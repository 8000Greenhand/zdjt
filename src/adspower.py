from __future__ import annotations

import requests
from playwright.sync_api import Browser, Page, Playwright, sync_playwright


class AdsPowerClient:
    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip("/")

    def list_profiles(self) -> list[dict]:
        url = f"{self.api_base}/api/v1/browser/list"
        resp = requests.get(url, params={"page": 1, "page_size": 100}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (0, "0", None):
            raise RuntimeError(f"AdsPower 返回异常：{data}")
        return data.get("data", {}).get("list", []) or []

    def start_profile(self, profile_id: str) -> str:
        if not profile_id:
            raise ValueError("profile_id 为空。请先在 config.json 或程序窗口中填写 AdsPower 环境 ID。")

        url = f"{self.api_base}/api/v1/browser/start"
        resp = requests.get(url, params={"user_id": profile_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (0, "0"):
            raise RuntimeError(f"启动 AdsPower 环境失败：{data}")

        payload = data.get("data") or {}
        ws = (payload.get("ws") or {}).get("puppeteer")
        if not ws:
            raise RuntimeError(f"AdsPower 未返回 CDP WebSocket 地址：{data}")
        return ws


class BrowserSession:
    def __init__(self, page: Page, browser: Browser, playwright: Playwright):
        self.page = page
        self.browser = browser
        self.playwright = playwright

    def close(self) -> None:
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self.playwright.stop()
        except Exception:
            pass


def connect_to_adspower(ws_endpoint: str) -> BrowserSession:
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(ws_endpoint)

    if not browser.contexts:
        raise RuntimeError("已连接浏览器，但没有可用 context。")

    context = browser.contexts[0]
    pages = list(context.pages)
    if not pages:
        page = context.new_page()
    else:
        temu_pages = [p for p in pages if "temu" in (p.url or "").lower()]
        page = temu_pages[-1] if temu_pages else pages[-1]

    return BrowserSession(page=page, browser=browser, playwright=pw)
