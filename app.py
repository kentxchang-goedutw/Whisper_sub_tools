from __future__ import annotations

import importlib.util
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import customtkinter as ctk
from tkinter import filedialog, messagebox


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_dir()))
    return base / relative_path


APP_DIR = app_dir()
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm", ".mkv", ".mov", ".aac", ".flac"}

SEGMENT_RULES = {
    "fine": {"label": "細緻", "max_chars": 24, "max_duration": 4.2, "punctuation": "，。！？；,.!?;"},
    "standard": {"label": "標準", "max_chars": 36, "max_duration": 6.5, "punctuation": "。！？；.!?;"},
    "loose": {"label": "寬鬆", "max_chars": 58, "max_duration": 9.5, "punctuation": "。！？.!?"},
}

LANGUAGES = {
    "自動判斷": "",
    "中文": "zh",
    "英文": "en",
    "日文": "ja",
    "韓文": "ko",
    "西班牙文": "es",
}


class WhisperSubtitleApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Whisper 本地字幕生成工具 - Python GUI")
        self.set_window_icon()
        self.geometry("980x560")
        self.minsize(780, 540)
        self.maxsize(10000, 560)

        self.file_path: Path | None = None
        self.last_srt = ""
        self.last_output_path: Path | None = None
        self.worker: threading.Thread | None = None
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.model_var = ctk.StringVar(value="medium")
        self.language_var = ctk.StringVar(value="自動判斷")
        self.device_var = ctk.StringVar(value="auto")
        self.compute_var = ctk.StringVar(value="float16")
        self.segment_var = ctk.StringVar(value="standard")
        self.status_var = ctk.StringVar(value="等待檔案")
        self.file_var = ctk.StringVar(value="尚未選擇媒體檔")
        self.meta_var = ctk.StringVar(value="")
        self.env_summary_var = ctk.StringVar(value="尚未檢查環境。")
        self.env_detail = "尚未檢查環境。"
        self.progress: ctk.CTkProgressBar | None = None

        self.configure(fg_color="#f6f3f8")
        self.build_ui()
        self.poll_events()

    def set_window_icon(self) -> None:
        icon_path = bundle_path("assets/app_icon.ico")
        if not icon_path.exists():
            return
        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            pass

    def build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hero = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=20)
        hero.grid(row=0, column=0, padx=14, pady=(14, 10), sticky="ew")
        hero.grid_columnconfigure(1, weight=1)
        hero.grid_columnconfigure(2, weight=0)

        logo = ctk.CTkFrame(hero, width=44, height=44, fg_color="#287fec", corner_radius=14)
        logo.grid(row=0, column=0, rowspan=2, padx=(18, 14), pady=12, sticky="n")
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="♪", text_color="#ffffff", font=ctk.CTkFont(size=24, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            hero,
            text="Whisper 本地字幕生成工具",
            text_color="#f64b88",
            font=ctk.CTkFont(family="Microsoft JhengHei UI", size=24, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 18), pady=(10, 2), sticky="w")

        author = ctk.CTkFrame(hero, fg_color="transparent")
        author.grid(row=0, column=2, padx=(8, 18), pady=(10, 2), sticky="ne")
        author_line = ctk.CTkFrame(author, fg_color="transparent")
        author_line.pack(anchor="e")
        ctk.CTkLabel(author_line, text="Made by", text_color="#81768f", font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkButton(
            author_line,
            text="阿剛老師",
            width=72,
            height=24,
            fg_color="transparent",
            hover_color="#f0eafa",
            text_color="#287fec",
            command=self.open_author_link,
        ).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(
            author_line,
            text="CC：標示作者、非商業、相同方式分享",
            text_color="#8d829c",
            font=ctk.CTkFont(family="Microsoft JhengHei UI", size=11),
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(
            hero,
            textvariable=self.status_var,
            text_color="#81768f",
            font=ctk.CTkFont(family="Microsoft JhengHei UI", size=13),
            wraplength=660,
            justify="left",
        ).grid(row=1, column=1, padx=(0, 18), pady=(0, 10), sticky="w")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        content.grid_columnconfigure(0, weight=42)
        content.grid_columnconfigure(1, weight=58)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=22)
        left.grid(row=0, column=0, padx=(0, 7), sticky="nsew")
        right = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=22)
        right.grid(row=0, column=1, padx=(7, 0), sticky="nsew")

        self.build_left(left)
        self.build_right(right)

    @staticmethod
    def open_author_link() -> None:
        webbrowser.open_new("https://kentxchang.blogspot.tw")

    def build_left(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(parent, text="媒體檔", text_color="#30283f", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(16, 8), sticky="w"
        )

        drop = ctk.CTkFrame(parent, fg_color="#fbf9fd", border_width=1, border_color="#d9d0e5", corner_radius=16)
        drop.grid(row=1, column=0, padx=18, sticky="ew")
        drop.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(drop, textvariable=self.file_var, text_color="#625875", wraplength=350, justify="left").grid(
            row=0, column=0, padx=14, pady=12, sticky="ew"
        )
        ctk.CTkButton(drop, text="選擇檔案", width=112, height=34, command=self.choose_file).grid(
            row=0, column=1, padx=(8, 14), pady=12, sticky="e"
        )

        settings = ctk.CTkFrame(parent, fg_color="transparent")
        settings.grid(row=2, column=0, padx=18, pady=(12, 0), sticky="ew")
        settings.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.add_option(settings, "模型", self.model_var, ["tiny", "base", "small", "medium", "large-v3"], 0, 0)
        self.add_option(settings, "語言", self.language_var, list(LANGUAGES.keys()), 0, 1)
        self.add_option(settings, "裝置", self.device_var, ["auto", "cuda", "cpu"], 0, 2)
        self.add_option(settings, "精度", self.compute_var, ["float16", "int8_float16", "int8"], 0, 3)

        segment_box = ctk.CTkFrame(parent, fg_color="#fbf9fd", corner_radius=16)
        segment_box.grid(row=3, column=0, padx=18, pady=(10, 0), sticky="ew")
        segment_box.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(segment_box, text="字幕切割粒度", text_color="#30283f", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=14, pady=(10, 4), sticky="w"
        )
        for column, (value, text) in enumerate([("fine", "細緻"), ("standard", "標準"), ("loose", "寬鬆")]):
            ctk.CTkRadioButton(segment_box, text=text, value=value, variable=self.segment_var).grid(
                row=1, column=column, padx=(14 if column == 0 else 6, 14 if column == 2 else 6), pady=(2, 12), sticky="w"
            )

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=4, column=0, padx=18, pady=(14, 18), sticky="ew")
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        self.check_button = ctk.CTkButton(actions, text="檢查環境", height=36, fg_color="#2dc9be", hover_color="#23aaa1", command=self.check_environment)
        self.check_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.transcribe_button = ctk.CTkButton(
            actions,
            text="開始辨識",
            height=36,
            fg_color="#ff9b44",
            hover_color="#e58432",
            command=self.start_transcribe,
            state="disabled",
        )
        self.transcribe_button.grid(row=0, column=1, padx=6, sticky="ew")
        self.save_button = ctk.CTkButton(actions, text="另存 SRT", height=36, command=self.save_as, state="disabled")
        self.save_button.grid(row=0, column=2, padx=(6, 0), sticky="ew")

    def build_right(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.grid(row=0, column=0, padx=18, pady=(16, 8), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="輸出結果", text_color="#30283f", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(head, textvariable=self.meta_var, text_color="#81768f").grid(row=0, column=1, sticky="e")

        self.tabs = ctk.CTkTabview(parent, fg_color="#fbf9fd", segmented_button_fg_color="#ede8f3")
        self.tabs.grid(row=1, column=0, padx=18, sticky="nsew")
        transcript_tab = self.tabs.add("逐字稿")
        srt_tab = self.tabs.add("SRT")
        transcript_tab.grid_columnconfigure(0, weight=1)
        transcript_tab.grid_rowconfigure(0, weight=1)
        srt_tab.grid_columnconfigure(0, weight=1)
        srt_tab.grid_rowconfigure(0, weight=1)

        self.transcript_text = ctk.CTkTextbox(transcript_tab, fg_color="#ffffff", text_color="#30283f", corner_radius=12, wrap="word")
        self.transcript_text.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self.srt_text = ctk.CTkTextbox(srt_tab, fg_color="#ffffff", text_color="#30283f", corner_radius=12, wrap="none")
        self.srt_text.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        output_actions = ctk.CTkFrame(parent, fg_color="transparent")
        output_actions.grid(row=2, column=0, padx=18, pady=(12, 18), sticky="ew")
        output_actions.grid_columnconfigure((0, 1, 2), weight=1)
        self.copy_button = ctk.CTkButton(output_actions, text="複製 SRT", height=36, command=self.copy_srt)
        self.copy_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.open_folder_button = ctk.CTkButton(output_actions, text="打開輸出資料夾", height=36, command=self.open_output_dir)
        self.open_folder_button.grid(row=0, column=1, padx=6, sticky="ew")
        self.clear_button = ctk.CTkButton(output_actions, text="清除", height=36, fg_color="#6758e8", hover_color="#5749cb", command=self.clear_outputs)
        self.clear_button.grid(
            row=0, column=2, padx=(6, 0), sticky="ew"
        )

    def add_option(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        values: list[str],
        row: int,
        column: int,
    ) -> None:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        left_pad = 0 if column == 0 else 5
        right_pad = 0 if column == 3 else 5
        box.grid(row=row, column=column, padx=(left_pad, right_pad), pady=(0, 9), sticky="ew")
        ctk.CTkLabel(box, text=label, text_color="#30283f", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkOptionMenu(box, variable=variable, values=values, height=34).pack(fill="x")

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="選擇音訊或影片",
            filetypes=[
                ("媒體檔", "*.mp3 *.mp4 *.wav *.m4a *.ogg *.webm *.mkv *.mov *.aac *.flac"),
                ("所有檔案", "*.*"),
            ],
        )
        if not path:
            return

        selected = Path(path)
        if selected.suffix.lower() not in ALLOWED_EXTENSIONS:
            if not messagebox.askyesno("格式確認", "這個副檔名不在常見清單內，仍要嘗試辨識嗎？"):
                return

        self.file_path = selected
        self.file_var.set(f"{selected.name}\n{readable_bytes(selected.stat().st_size)}")
        self.transcribe_button.configure(state="normal")
        self.set_status("檔案已就緒，可以開始辨識。")

    def check_environment(self) -> None:
        env = collect_environment()
        text = [
            f"Python：{env['python']}",
            f"執行位置：{APP_DIR}",
            f"ffmpeg：{'可用' if env['ffmpeg'] else '未在 PATH 偵測到'}",
            f"nvidia-smi：{env['nvidia_smi']['text']}",
            f"CUDA 裝置數：{env['cuda_device_count']}",
            f"建議裝置：{env['recommended_device']}",
            "",
            "套件：",
        ]
        text.extend(f"- {name}: {'OK' if ok else '缺少'}" for name, ok in env["packages"].items())
        if env["ctranslate2_error"]:
            text.extend(["", f"CTranslate2 錯誤：{env['ctranslate2_error']}"])

        self.write_env("\n".join(text))
        self.device_var.set("auto" if env["cuda_available"] else "cpu")
        self.set_status("環境檢查完成。" if env["cuda_available"] else "CUDA 未就緒，目前建議使用 CPU 或補齊 CUDA 依賴。")

    def start_transcribe(self) -> None:
        if not self.file_path:
            messagebox.showwarning("尚未選擇檔案", "請先選擇音訊或影片。")
            return
        if self.worker and self.worker.is_alive():
            return

        config = {
            "file_path": self.file_path,
            "model_name": self.model_var.get(),
            "language": LANGUAGES.get(self.language_var.get(), ""),
            "device": self.device_var.get(),
            "compute_type": self.compute_var.get(),
            "segment_mode": self.segment_var.get(),
        }

        self.clear_outputs()
        self.set_busy(True)
        self.set_status("正在載入模型並辨識，第一次使用該模型會下載模型檔。")

        self.worker = threading.Thread(target=self.transcribe_worker, args=(config,), daemon=True)
        self.worker.start()

    def transcribe_worker(self, config: dict[str, Any]) -> None:
        started_at = time.perf_counter()
        try:
            if importlib.util.find_spec("faster_whisper") is None:
                raise RuntimeError("缺少 faster-whisper。請使用 build_exe.ps1 打包完整版本，或先安裝 requirements.txt。")

            from faster_whisper import WhisperModel

            file_path = Path(config["file_path"])
            requested_device = str(config["device"])
            device = resolve_device(requested_device)
            compute_type = resolve_compute_type(device, str(config["compute_type"]))
            model_name = str(config["model_name"])
            language = str(config["language"])

            self.events.put(("status", f"使用 {device} / {compute_type} 載入 {model_name} 模型。"))
            try:
                model = WhisperModel(model_name, device=device, compute_type=compute_type)
            except Exception as exc:
                if device != "cuda" or not is_cuda_runtime_error(exc):
                    raise

                self.events.put(
                    (
                        "status",
                        "CUDA runtime 缺少必要 DLL，已自動改用 CPU / int8。若要用 GPU，請安裝相容的 NVIDIA CUDA runtime。",
                    )
                )
                device = "cpu"
                compute_type = "int8"
                model = WhisperModel(model_name, device=device, compute_type=compute_type)

            vad_enabled = package_available("onnxruntime")
            if not vad_enabled:
                self.events.put(("status", "未偵測到 onnxruntime，已關閉 VAD 靜音過濾。"))

            segments_iter, info = model.transcribe(
                str(file_path),
                language=language or None,
                vad_filter=vad_enabled,
                beam_size=5,
            )

            raw_segments = []
            for segment in segments_iter:
                text = clean_text(segment.text)
                if text:
                    raw_segments.append({"start": float(segment.start), "end": float(segment.end), "text": text})
                    self.events.put(("status", f"已處理到 {format_short_time(float(segment.end))}。"))

            if not raw_segments:
                raise RuntimeError("沒有辨識到可輸出的字幕內容。")

            subtitle_segments = rebuild_segments(raw_segments, str(config["segment_mode"]))
            transcript = "\n".join(segment["text"] for segment in subtitle_segments)
            srt = to_srt(subtitle_segments)

            output_name = f"{sanitize_stem(file_path.stem)}-{int(time.time())}.srt"
            output_path = OUTPUT_DIR / output_name
            output_path.write_text("\ufeff" + srt, encoding="utf-8")

            elapsed = round(time.perf_counter() - started_at, 2)
            meta = {
                "model": model_name,
                "device": device,
                "compute_type": compute_type,
                "language": getattr(info, "language", None),
                "duration": getattr(info, "duration", None),
                "elapsed": elapsed,
                "segments": len(subtitle_segments),
                "output_path": output_path,
            }
            self.events.put(("done", {"transcript": transcript, "srt": srt, "meta": meta}))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "status":
                    self.set_status(payload)
                elif event == "done":
                    self.render_result(payload)
                    self.set_busy(False)
                elif event == "error":
                    self.set_busy(False)
                    self.set_status(f"辨識失敗：{payload}")
                    messagebox.showerror("辨識失敗", payload)
        except queue.Empty:
            pass
        self.after(160, self.poll_events)

    def render_result(self, payload: dict[str, Any]) -> None:
        self.last_srt = payload["srt"]
        self.last_output_path = payload["meta"]["output_path"]
        self.set_text(self.transcript_text, payload["transcript"])
        self.set_text(self.srt_text, payload["srt"])
        meta = payload["meta"]
        self.meta_var.set(f"{meta['segments']} 段 · {meta['device']} · {meta['elapsed']} 秒")
        self.save_button.configure(state="normal")
        self.set_status(f"辨識完成，已輸出：{self.last_output_path}")

    def save_as(self) -> None:
        if not self.last_srt:
            return
        default_name = self.last_output_path.name if self.last_output_path else "subtitle.srt"
        path = filedialog.asksaveasfilename(
            title="另存 SRT",
            defaultextension=".srt",
            initialfile=default_name,
            filetypes=[("SRT 字幕", "*.srt"), ("所有檔案", "*.*")],
        )
        if path:
            Path(path).write_text("\ufeff" + self.last_srt, encoding="utf-8")
            self.set_status(f"已另存：{path}")

    def copy_srt(self) -> None:
        if not self.last_srt:
            return
        self.clipboard_clear()
        self.clipboard_append(self.last_srt)
        self.set_status("已複製 SRT 到剪貼簿。")

    def open_output_dir(self) -> None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(OUTPUT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])

    def clear_outputs(self) -> None:
        self.last_srt = ""
        self.last_output_path = None
        self.meta_var.set("")
        self.save_button.configure(state="disabled")
        self.set_text(self.transcript_text, "")
        self.set_text(self.srt_text, "")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else ("normal" if self.file_path else "disabled")
        self.transcribe_button.configure(state=state)
        self.check_button.configure(state="disabled" if busy else "normal")
        if busy and self.progress is not None:
            self.progress.start()
        elif self.progress is not None:
            self.progress.stop()
            self.progress.set(0)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def write_env(self, text: str) -> None:
        self.env_detail = text
        lines = [line for line in text.splitlines() if line.strip()]
        cuda_line = next((line for line in lines if line.startswith("CUDA 裝置數")), "")
        device_line = next((line for line in lines if line.startswith("建議裝置")), "")
        self.env_summary_var.set(" · ".join(line for line in [cuda_line, device_line] if line) or lines[0])

    @staticmethod
    def set_text(widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)


def collect_environment() -> dict[str, Any]:
    package_names = ["customtkinter", "faster_whisper", "ctranslate2", "av", "onnxruntime"]
    packages = {name: package_available(name) for name in package_names}
    cuda_devices = 0
    ctranslate2_error = None

    if packages["ctranslate2"]:
        try:
            import ctranslate2

            cuda_devices = int(ctranslate2.get_cuda_device_count())
        except Exception as exc:
            ctranslate2_error = str(exc)

    return {
        "python": sys.version.split()[0],
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "packages": packages,
        "nvidia_smi": check_nvidia_smi(),
        "cuda_device_count": cuda_devices,
        "cuda_available": cuda_devices > 0,
        "ctranslate2_error": ctranslate2_error,
        "recommended_device": "cuda" if cuda_devices > 0 else "cpu",
    }


def check_nvidia_smi() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"available": False, "text": "找不到 nvidia-smi"}

    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
            timeout=8,
        )
    except Exception as exc:
        return {"available": False, "text": str(exc)}

    return {"available": True, "text": result.stdout.strip()}


def package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import ctranslate2

        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def resolve_compute_type(device: str, requested: str) -> str:
    if device == "cpu":
        return "int8"
    return requested or "float16"


def is_cuda_runtime_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = [
        "cublas64",
        "cudnn",
        "cudart",
        "cuda",
        "library",
        "dll",
        "not found",
        "cannot be loaded",
    ]
    return any(marker in text for marker in markers)


def rebuild_segments(chunks: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    rule = SEGMENT_RULES.get(mode, SEGMENT_RULES["standard"])
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for chunk in chunks:
        text_parts = split_text(chunk["text"], rule)
        duration = max(0.2, float(chunk["end"]) - float(chunk["start"]))
        cursor = float(chunk["start"])

        for part in text_parts:
            ratio = len(part) / max(len(chunk["text"]), 1)
            part_duration = max(0.55, duration * ratio)
            next_segment = {
                "start": cursor,
                "end": min(cursor + part_duration, float(chunk["end"])),
                "text": part,
            }
            cursor = float(next_segment["end"])

            if current is None:
                current = dict(next_segment)
                continue

            separator = " " if needs_space(str(current["text"]), str(next_segment["text"])) else ""
            candidate_text = f"{current['text']}{separator}{next_segment['text']}"
            candidate_duration = float(next_segment["end"]) - float(current["start"])
            ends_cleanly = str(current["text"])[-1:] in rule["punctuation"]

            if (
                len(candidate_text) <= rule["max_chars"]
                and candidate_duration <= rule["max_duration"]
                and not ends_cleanly
            ):
                current["text"] = candidate_text
                current["end"] = next_segment["end"]
            else:
                segments.append(current)
                current = dict(next_segment)

    if current is not None:
        segments.append(current)

    for index, segment in enumerate(segments):
        next_start = segments[index + 1]["start"] if index + 1 < len(segments) else segment["end"]
        segment["end"] = max(float(segment["end"]), float(segment["start"]) + 0.5, float(next_start))
        segment["start"] = round(float(segment["start"]), 3)
        segment["end"] = round(float(segment["end"]), 3)

    return segments


def split_text(text: str, rule: dict[str, Any]) -> list[str]:
    clean = clean_text(text)
    if len(clean) <= rule["max_chars"]:
        return [clean]

    parts: list[str] = []
    buffer = ""
    for char in clean:
        buffer += char
        should_split = len(buffer) >= rule["max_chars"] or (
            len(buffer) >= rule["max_chars"] * 0.65 and char in rule["punctuation"]
        )
        if should_split:
            parts.append(buffer.strip())
            buffer = ""

    if buffer.strip():
        parts.append(buffer.strip())
    return parts


def to_srt(segments: list[dict[str, Any]]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n"
            f"{format_srt_time(float(segment['start']))} --> {format_srt_time(float(segment['end']))}\n"
            f"{segment['text']}"
        )
    return "\n\n".join(blocks)


def format_srt_time(seconds: float) -> str:
    safe = max(0.0, seconds)
    hours = int(safe // 3600)
    minutes = int((safe % 3600) // 60)
    secs = int(safe % 60)
    millis = int((safe % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_short_time(seconds: float) -> str:
    safe = max(0.0, seconds)
    minutes = int(safe // 60)
    secs = int(safe % 60)
    return f"{minutes:02d}:{secs:02d}"


def clean_text(text: str) -> str:
    return " ".join(str(text).split()).strip()


def needs_space(left: str, right: str) -> bool:
    return bool(left and right and left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum())


def sanitize_stem(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value).strip("-")
    return safe or "subtitle"


def readable_bytes(bytes_count: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(bytes_count)
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024
        unit += 1
    return f"{value:.0f} {units[unit]}" if unit == 0 else f"{value:.1f} {units[unit]}"


if __name__ == "__main__":
    if "--check-bundle-assets" in sys.argv:
        required_assets = [
            bundle_path("faster_whisper/assets/silero_vad_v6.onnx"),
            bundle_path("assets/app_icon.ico"),
        ]
        missing_assets = [str(path) for path in required_assets if not path.exists()]
        if missing_assets:
            raise SystemExit(f"Missing bundled assets: {', '.join(missing_assets)}")
        raise SystemExit(0)

    if "--smoke-test" in sys.argv:
        env = collect_environment()
        required = ["customtkinter", "faster_whisper", "ctranslate2", "av"]
        missing = [name for name in required if not env["packages"].get(name)]
        if missing:
            raise SystemExit(f"Missing packages: {', '.join(missing)}")
        raise SystemExit(0)

    os.environ.setdefault("CTK_SCALING", "1")
    app = WhisperSubtitleApp()
    app.mainloop()
