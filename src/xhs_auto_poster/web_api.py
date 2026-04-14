from __future__ import annotations

import io
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .main import build_config_from_dict, run

_TASK_LOCK = Lock()


class PublishRequest(BaseModel):
    title: str = Field(..., description="笔记标题")
    content: str = Field(..., description="笔记正文")
    images: list[str] = Field(..., description="图片路径数组")
    topics: list[str] = Field(default_factory=list, description="话题数组")
    user_data_dir: str = Field(default=".xhs_profile", description="登录态目录")
    headless: bool = Field(default=False, description="是否无头")
    slow_mo_ms: int = Field(default=80, description="操作慢动作毫秒")
    wait_login_timeout_seconds: int = Field(default=300, description="等待登录秒数")
    dry_run: bool = Field(default=False, description="仅演练不点击发布")
    browser_channel: str | None = Field(default="chrome", description="浏览器通道")
    browser_executable_path: str | None = Field(default=None, description="浏览器可执行文件")
    base_dir: str | None = Field(default=None, description="相对路径解析基准目录")


class PublishResponse(BaseModel):
    success: bool
    message: str
    logs: list[str]
    duration_seconds: float


def _normalize_request_payload(req: PublishRequest) -> tuple[dict[str, Any], Path]:
    payload = req.model_dump()

    payload["topics"] = [topic.strip().lstrip("#") for topic in payload["topics"] if topic.strip()]
    
    processed_images = []
    import base64
    import tempfile
    for idx, image in enumerate(payload["images"]):
        image = image.strip()
        if not image:
            continue
        if image.startswith("data:image/"):
            try:
                header, encoded = image.split(",", 1)
                ext = header.split(";")[0].split("/")[1]
                if ext == "jpeg":
                    ext = "jpg"
                temp_dir = Path(tempfile.mkdtemp(prefix="xhs_images_"))
                file_path = temp_dir / f"image_{idx}.{ext}"
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(encoded))
                processed_images.append(str(file_path))
            except Exception as e:
                print(f"Failed to parse base64 image: {e}")
        else:
            processed_images.append(str(Path(image).expanduser()))
            
    payload["images"] = processed_images

    base_dir = Path(payload.pop("base_dir") or Path.cwd()).expanduser().resolve()
    return payload, base_dir


def create_app() -> FastAPI:
    app = FastAPI(title="XHS Auto Poster UI API", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/select_images")
    def select_images_api() -> dict[str, list[str]]:
        import subprocess, sys, json
        code = """
import tkinter as tk
from tkinter import filedialog
import json
import os
# Make tkinter work properly on mac
if os.uname().sysname == 'Darwin':
    os.system('''/usr/bin/osascript -e 'tell app "System Events" to set frontmost of process "Python" to true' ''')
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
file_paths = filedialog.askopenfilenames(
    title="选择图片",
    filetypes=[("Image Files", "*.bmp *.jpg *.jpeg *.png *.gif *.webp"), ("All Files", "*.*")]
)
root.destroy()
print(json.dumps(list(file_paths)))
"""
        try:
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
            paths = json.loads(result.stdout)
            return {"paths": paths}
        except Exception as e:
            print(f"File dialog error: {e}")
            return {"paths": []}

    @app.get("/api/accounts")
    def get_accounts() -> dict[str, list[str]]:
        base = Path.home() / ".xhs_auto_poster"
        if not base.exists():
            return {"accounts": [".xhs_profile"]}
        accounts = []
        for p in base.iterdir():
            if p.is_dir() and p.name.startswith(".xhs_profile"):
                accounts.append(p.name)
        if not accounts:
            accounts.append(".xhs_profile")
        return {"accounts": list(sorted(accounts))}

    @app.post("/api/publish", response_model=PublishResponse)
    def publish(req: PublishRequest) -> PublishResponse:
        if not _TASK_LOCK.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="当前已有发布任务在执行，请稍后再试")

        start = time.perf_counter()
        log_buffer = io.StringIO()
        try:
            payload, base_dir = _normalize_request_payload(req)
            config = build_config_from_dict(payload, base_dir=base_dir)
            with redirect_stdout(log_buffer), redirect_stderr(log_buffer):
                run(config)

            logs = [line for line in log_buffer.getvalue().splitlines() if line.strip()]
            return PublishResponse(
                success=True,
                message="发布流程执行完成",
                logs=logs,
                duration_seconds=round(time.perf_counter() - start, 2),
            )
        except Exception as exc:
            logs = [line for line in log_buffer.getvalue().splitlines() if line.strip()]
            logs.append(f"[错误] {exc}")
            return PublishResponse(
                success=False,
                message=str(exc),
                logs=logs,
                duration_seconds=round(time.perf_counter() - start, 2),
            )
        finally:
            _TASK_LOCK.release()

    return app
