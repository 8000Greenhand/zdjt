from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext

from .adspower import AdsPowerClient, BrowserSession, connect_to_adspower
from .config import AppConfig, load_config, save_config
from .file_utils import sanitize_filename, unique_path
from .registry import append_registry
from .temu_page import ImageCandidate, TemuPageAssistant


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Temu 前台截图助手 v0.1")
        self.root.geometry("860x650")

        self.config: AppConfig = load_config()
        self.session: BrowserSession | None = None
        self.assistant: TemuPageAssistant | None = None

        self.profile_var = tk.StringVar(value=self.config.profile_id)
        self.api_var = tk.StringVar(value=self.config.adspower_api)
        self.output_var = tk.StringVar(value=self.config.output_root)
        self.registry_var = tk.StringVar(value=self.config.registry_path)
        self.title_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="未连接")
        self.candidate_var = tk.StringVar(value="候选图：无")

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 5}

        frm = tk.Frame(self.root)
        frm.pack(fill="x", **pad)

        tk.Label(frm, text="AdsPower API").grid(row=0, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.api_var, width=58).grid(row=0, column=1, sticky="we")
        tk.Button(frm, text="列出环境", command=self.list_profiles).grid(row=0, column=2, sticky="we", padx=5)

        tk.Label(frm, text="Profile ID").grid(row=1, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.profile_var, width=58).grid(row=1, column=1, sticky="we")
        tk.Button(frm, text="连接 AdsPower", command=self.connect_browser).grid(row=1, column=2, sticky="we", padx=5)

        tk.Label(frm, text="截图目录").grid(row=2, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.output_var, width=58).grid(row=2, column=1, sticky="we")
        tk.Button(frm, text="保存配置", command=self.save_current_config).grid(row=2, column=2, sticky="we", padx=5)

        tk.Label(frm, text="登记表").grid(row=3, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.registry_var, width=58).grid(row=3, column=1, sticky="we")

        frm.columnconfigure(1, weight=1)

        action = tk.Frame(self.root)
        action.pack(fill="x", **pad)

        tk.Button(action, text="识别当前商品页", height=2, command=self.scan_current_page).pack(side="left", padx=5)
        tk.Button(action, text="下一张候选图", height=2, command=self.next_candidate).pack(side="left", padx=5)
        tk.Button(action, text="保存截图", height=2, command=self.save_screenshot).pack(side="left", padx=5)

        tk.Label(action, textvariable=self.status_var, fg="blue").pack(side="left", padx=20)
        tk.Label(action, textvariable=self.candidate_var, fg="darkgreen").pack(side="left", padx=20)

        title_frame = tk.LabelFrame(self.root, text="文件名标题：默认使用自动提取的英文标题；不准就手动改这里")
        title_frame.pack(fill="x", **pad)
        tk.Entry(title_frame, textvariable=self.title_var, font=("Consolas", 11)).pack(fill="x", padx=8, pady=8)

        tips = tk.LabelFrame(self.root, text="操作顺序")
        tips.pack(fill="x", **pad)
        tk.Label(
            tips,
            justify="left",
            text=(
                "1. 先在 AdsPower 里打开 Temu 商品详情页，并确认是英文界面。\n"
                "2. 点击【连接 AdsPower】。\n"
                "3. 点击【识别当前商品页】，程序会抓标题并找主图候选区域。\n"
                "4. 看浏览器里的当前商品图，如果候选不对，点【下一张候选图】。\n"
                "5. 标题框确认无误后，点【保存截图】。\n"
                "6. 遇到验证码、登录异常、页面异常，先手动处理，再重新识别。"
            ),
        ).pack(anchor="w", padx=8, pady=6)

        log_frame = tk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=12)
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    def log(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{now}] {text}\n")
        self.log_box.see("end")
        self.root.update_idletasks()

    def save_current_config(self) -> None:
        self.config.adspower_api = self.api_var.get().strip()
        self.config.profile_id = self.profile_var.get().strip()
        self.config.output_root = self.output_var.get().strip()
        self.config.registry_path = self.registry_var.get().strip()
        save_config(self.config)
        self.log("配置已保存。")

    def list_profiles(self) -> None:
        try:
            self.save_current_config()
            client = AdsPowerClient(self.config.adspower_api)
            profiles = client.list_profiles()
            if not profiles:
                self.log("没有获取到 AdsPower 环境。请确认 AdsPower 已打开，Local API 已启用。")
                return

            self.log("AdsPower 环境列表：")
            for item in profiles[:30]:
                pid = item.get("user_id") or item.get("id") or ""
                name = item.get("name") or item.get("remark") or item.get("serial_number") or ""
                self.log(f"  profile_id={pid}    name={name}")
            self.log("把要用的 profile_id 复制到上方输入框，然后点【连接 AdsPower】。")
        except Exception as exc:
            self.handle_error("列出环境失败", exc)

    def connect_browser(self) -> None:
        try:
            self.save_current_config()
            client = AdsPowerClient(self.config.adspower_api)
            self.log("正在启动/连接 AdsPower 环境...")
            ws = client.start_profile(self.config.profile_id)
            self.session = connect_to_adspower(ws)
            self.assistant = TemuPageAssistant(
                self.session.page,
                min_width=self.config.min_image_width,
                min_height=self.config.min_image_height,
                prefer_left=self.config.prefer_left_side_image,
            )
            self.status_var.set("已连接")
            self.log(f"已连接页面：{self.session.page.url}")
        except Exception as exc:
            self.handle_error("连接 AdsPower 失败", exc)

    def scan_current_page(self) -> None:
        try:
            if not self.session:
                self.connect_browser()
            if not self.session:
                return

            self.assistant = TemuPageAssistant(
                self.session.page,
                min_width=self.config.min_image_width,
                min_height=self.config.min_image_height,
                prefer_left=self.config.prefer_left_side_image,
            )
            self.log("正在识别当前商品页标题和主图候选...")
            title = self.assistant.extract_title()
            self.title_var.set(title)

            candidates = self.assistant.reload_candidates()
            self.update_candidate_label()

            self.log(f"标题：{title}")
            self.log(f"找到 {len(candidates)} 张候选图。")
            if not candidates:
                self.log("没有找到可截图候选图。请确认当前主图已加载，或滚动/放大页面后重试。")
        except Exception as exc:
            self.handle_error("识别当前商品页失败", exc)

    def update_candidate_label(self) -> None:
        if not self.assistant:
            self.candidate_var.set("候选图：无")
            return
        candidate = self.assistant.current_candidate()
        if not candidate:
            self.candidate_var.set("候选图：无")
            return
        self.candidate_var.set(
            f"候选图：{candidate.index + 1}/{len(self.assistant.candidates)} "
            f"区域 {int(candidate.width)}x{int(candidate.height)}"
        )

    def next_candidate(self) -> None:
        try:
            if not self.assistant or not self.assistant.candidates:
                self.scan_current_page()
                return
            candidate = self.assistant.next_candidate()
            self.update_candidate_label()
            if candidate:
                self.log(
                    f"切换候选图：{candidate.index + 1}/{len(self.assistant.candidates)}，"
                    f"区域 {int(candidate.width)}x{int(candidate.height)}"
                )
        except Exception as exc:
            self.handle_error("切换候选图失败", exc)

    def save_screenshot(self) -> None:
        try:
            if not self.assistant or not self.assistant.candidates:
                self.scan_current_page()
            if not self.assistant:
                return

            title = self.title_var.get().strip()
            if not title:
                messagebox.showwarning("缺少标题", "标题为空。请先识别页面，或手动填写英文标题。")
                return

            today = datetime.now().strftime("%Y-%m-%d")
            out_dir = Path(self.output_var.get().strip()) / today
            safe_title = sanitize_filename(title, self.config.max_filename_length)
            output_path = unique_path(out_dir, safe_title, ".png")

            self.assistant.screenshot_candidate(output_path)

            page = self.session.page if self.session else None
            append_registry(
                self.registry_var.get().strip(),
                {
                    "商品标题": title,
                    "截图路径": str(output_path),
                    "商品URL": page.url if page else "",
                    "页面标题": page.title() if page else "",
                    "备注": "v0.1 手动确认保存",
                },
            )

            self.log(f"已保存截图：{output_path}")
            messagebox.showinfo("保存成功", f"已保存：\n{output_path}")
        except Exception as exc:
            self.handle_error("保存截图失败", exc)

    def handle_error(self, title: str, exc: Exception) -> None:
        self.log(f"[错误] {title}: {exc}")
        self.log(traceback.format_exc())
        messagebox.showerror(title, str(exc))

    def on_close(self) -> None:
        try:
            if self.session:
                # 这里只断开 Playwright，不主动 stop AdsPower 环境，避免误关用户窗口。
                self.session.close()
        finally:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
