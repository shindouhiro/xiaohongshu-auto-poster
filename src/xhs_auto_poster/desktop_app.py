import os
import sys
import webview
from pathlib import Path
from xhs_auto_poster.main import PublishConfig, run

# 自动识别打包后的路径
def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后的临时解压目录
        return Path(sys._MEIPASS) / relative_path
    # 开发环境下的源码根目录
    return Path(__file__).resolve().parent.parent.parent / relative_path

WEB_DIST_DIR = get_resource_path("web/dist")

class API:
    """供 JavaScript 调用的接口"""
    def select_images(self, data=None):
        import webview
        try:
            window = webview.windows[0]
            file_types = ('Image Files (*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.webp)', 'All files (*.*)')
            result = window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types
            )
            return {"status": "success", "paths": result if result else []}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def publish_note(self, data):
        """前端点击发布按钮时调用"""
        try:
            # 修正路径逻辑：禁止在根目录写入，改为在用户家目录下创建一个隐藏文件夹
            raw_dir = data.get("user_data_dir", ".xhs_profile")
            
            # 安全路径解析：如果是相对路径或指向根目录的隐藏路径，则纠正到用户家目录
            if not Path(raw_dir).is_absolute() or raw_dir.startswith("/."):
                user_data_dir = Path.home() / ".xhs_auto_poster" / Path(raw_dir).name
            else:
                user_data_dir = Path(raw_dir).resolve()
            
            # 确保目录存在
            user_data_dir.parent.mkdir(parents=True, exist_ok=True)
            
            import base64
            import tempfile
            processed_images = []
            for idx, img in enumerate(data.get("images", [])):
                img = str(img).strip()
                if not img:
                    continue
                if img.startswith("data:image/"):
                    try:
                        header, encoded = img.split(",", 1)
                        ext = header.split(";")[0].split("/")[1]
                        if ext == "jpeg":
                            ext = "jpg"
                        temp_dir = Path(tempfile.mkdtemp(prefix="xhs_images_"))
                        file_path = temp_dir / f"image_{idx}.{ext}"
                        with open(file_path, "wb") as f:
                            f.write(base64.b64decode(encoded))
                        processed_images.append(file_path)
                    except Exception as e:
                        print(f"Failed to parse base64 image: {e}")
                else:
                    processed_images.append(Path(img))
            
            config = PublishConfig(
                title=data.get("title", ""),
                content=data.get("content", ""),
                images=processed_images,
                topics=data.get("topics", []),
                user_data_dir=user_data_dir,
                headless=data.get("headless", False),
                slow_mo_ms=80,
                wait_login_timeout_seconds=300,
                dry_run=data.get("dry_run", False),
                browser_channel=None,
                browser_executable_path=None,
            )
            
            print(f"[桌面端] 准备发布笔记: {config.title} (存储目录: {user_data_dir})")
            run(config)
            return {"status": "success", "message": "发布流程已完成", "duration": 0}
        except Exception as e:
            print(f"[错误] {str(e)}")
            return {"status": "error", "message": str(e)}

def start_app():
    # 检查静态资源目录是否存在
    if not WEB_DIST_DIR.exists():
        print(f"找不到前端构建文件: {WEB_DIST_DIR}，请先运行 `cd web && pnpm build`")
        return

    # 创建 API 实例
    api = API()
    
    # 创建 webview 窗口
    # 设置 index.html 的路径
    index_path = WEB_DIST_DIR / "index.html"
    
    window = webview.create_window(
        title="小红书自动发布助手",
        url=str(index_path.resolve().as_uri()), # 加载本地文件夹
        js_api=api, # 将 API 注入到 window.pywebview 中
        width=1000,
        height=800,
        resizable=True
    )
    
    # 启动应用
    webview.start(debug=True)

if __name__ == "__main__":
    start_app()
