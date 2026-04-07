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
    def publish_note(self, data):
        """前端点击发布按钮时调用"""
        try:
            # 数据转换 (根据你的 Web 前端传来的 JSON 结构映射)
            config = PublishConfig(
                title=data.get("title"),
                content=data.get("content"),
                images=[Path(p) for p in data.get("images", [])],
                topics=data.get("topics", []),
                user_data_dir=Path(data.get("user_data_dir", ".xhs_profile")).resolve(),
                headless=data.get("headless", False),
                slow_mo_ms=80,
                wait_login_timeout_seconds=300,
                dry_run=data.get("dry_run", False),
                browser_channel=None,
                browser_executable_path=None,
            )
            
            print(f"[桌面端] 准备发布笔记: {config.title}")
            run(config)
            return {"status": "success", "message": "发布流程已完成"}
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
