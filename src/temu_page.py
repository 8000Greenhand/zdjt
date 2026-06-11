from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page


@dataclass
class ImageCandidate:
    index: int
    x: float
    y: float
    width: float
    height: float
    src: str = ""
    score: float = 0.0

    @property
    def clip(self) -> dict[str, float]:
        return {
            "x": max(self.x, 0),
            "y": max(self.y, 0),
            "width": max(self.width, 1),
            "height": max(self.height, 1),
        }


class TemuPageAssistant:
    def __init__(self, page: Page, min_width: int = 250, min_height: int = 250, prefer_left: bool = True):
        self.page = page
        self.min_width = min_width
        self.min_height = min_height
        self.prefer_left = prefer_left
        self.candidates: list[ImageCandidate] = []
        self.current_index = 0

    def reload_candidates(self) -> list[ImageCandidate]:
        raw = self.page.evaluate(
            """
            () => {
                const vw = window.innerWidth || document.documentElement.clientWidth;
                const vh = window.innerHeight || document.documentElement.clientHeight;
                const imgs = Array.from(document.images || []);
                const rows = [];
                for (const img of imgs) {
                    const rect = img.getBoundingClientRect();
                    const style = window.getComputedStyle(img);
                    const visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                    const inView = rect.bottom > 0 && rect.right > 0 && rect.top < vh && rect.left < vw;
                    if (!visible || !inView) continue;
                    rows.push({
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        src: img.currentSrc || img.src || '',
                        naturalWidth: img.naturalWidth || 0,
                        naturalHeight: img.naturalHeight || 0,
                        vw,
                        vh
                    });
                }
                return rows;
            }
            """
        )

        candidates: list[ImageCandidate] = []
        for i, item in enumerate(raw):
            w = float(item.get("width") or 0)
            h = float(item.get("height") or 0)
            if w < self.min_width or h < self.min_height:
                continue

            x = float(item.get("x") or 0)
            y = float(item.get("y") or 0)
            area = w * h
            vw = float(item.get("vw") or 1200)

            # 商品主图通常面积大，且在详情页左侧；这里不是反爬，只是帮助选中截图区域。
            left_bonus = 1.2 if self.prefer_left and x < vw * 0.55 else 1.0
            near_top_bonus = 1.1 if y < 500 else 1.0
            score = area * left_bonus * near_top_bonus

            candidates.append(
                ImageCandidate(
                    index=len(candidates),
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    src=str(item.get("src") or ""),
                    score=score,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        for idx, candidate in enumerate(candidates):
            candidate.index = idx

        self.candidates = candidates
        self.current_index = 0
        return candidates

    def current_candidate(self) -> ImageCandidate | None:
        if not self.candidates:
            return None
        self.current_index = max(0, min(self.current_index, len(self.candidates) - 1))
        return self.candidates[self.current_index]

    def next_candidate(self) -> ImageCandidate | None:
        if not self.candidates:
            return None
        self.current_index = (self.current_index + 1) % len(self.candidates)
        return self.current_candidate()

    def extract_title(self) -> str:
        """尽力从商品详情页提取英文标题。提取不准时，用户可以在界面手动改。"""
        title = self.page.evaluate(
            """
            () => {
                function clean(s) {
                    return (s || '').replace(/\s+/g, ' ').trim();
                }
                function hasEnglish(s) {
                    return /[A-Za-z]{3,}/.test(s || '');
                }
                function badText(s) {
                    if (!s) return true;
                    if (s.length < 20 || s.length > 260) return true;
                    if (/^\$?\d+[\d.,]*$/.test(s)) return true;
                    if (/add to cart|buy now|shipping|delivery|review|quantity/i.test(s) && s.length < 80) return true;
                    return false;
                }

                const selectors = [
                    'h1',
                    '[data-testid*=title i]',
                    '[class*=title i]',
                    '[class*=goods i]',
                    '[class*=product i]'
                ];

                const seen = new Set();
                const candidates = [];
                for (const selector of selectors) {
                    for (const el of Array.from(document.querySelectorAll(selector))) {
                        if (seen.has(el)) continue;
                        seen.add(el);
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const text = clean(el.innerText || el.textContent || '');
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        if (rect.width <= 0 || rect.height <= 0) continue;
                        if (!hasEnglish(text) || badText(text)) continue;
                        const fs = parseFloat(style.fontSize || '14') || 14;
                        const rightBonus = rect.x > window.innerWidth * 0.35 ? 80 : 0;
                        const topBonus = rect.y < 500 ? 50 : 0;
                        const score = fs * 10 + rightBonus + topBonus - Math.abs(text.length - 110) * 0.2;
                        candidates.push({ text, score });
                    }
                }

                candidates.sort((a, b) => b.score - a.score);
                if (candidates.length) return candidates[0].text;

                const fallback = clean(document.title || '');
                return fallback.replace(/\|.*$/, '').replace(/Temu.*/i, '').trim();
            }
            """
        )
        return str(title or "").strip()

    def screenshot_candidate(self, output_path: str | Path, candidate: ImageCandidate | None = None) -> None:
        target = candidate or self.current_candidate()
        if target is None:
            raise RuntimeError("没有可截图的图片候选区域。请确认当前是商品详情页，并且主图已加载。")
        self.page.screenshot(path=str(output_path), clip=target.clip)
