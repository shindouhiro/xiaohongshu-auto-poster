import asyncio
import sys
import threading
from pathlib import Path

import flet as ft
from xhs_auto_poster.main import PublishConfig, run


class Logger:
    def __init__(self, log_view: ft.ListView):
        self.log_view = log_view

    def write(self, message):
        if message.strip():
            self.log_view.controls.append(ft.Text(message.strip(), size=12, font_family="monospace"))
            self.log_view.update()
            # 自动滚动到底部
            self.log_view.scroll_to(offset=-1, duration=100)

    def flush(self):
        pass


def main(page: ft.Page):
    page.title = "小红书自动发布助手"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 800
    page.window_height = 900
    page.padding = 20

    # --- 状态变量 ---
    selected_images = []

    # --- UI 控件 ---
    title_input = ft.TextField(label="笔记标题", placeholder="输入吸引人的标题", variant=ft.TextFieldVariant.OUTLINED)
    content_input = ft.TextField(
        label="笔记正文", placeholder="输入正文内容...", multiline=True, min_lines=5, max_lines=10
    )
    topics_input = ft.TextField(label="话题标签", placeholder="用逗号分隔，例如：穿搭,好物分享", hint_text="不需要打#号")
    profile_input = ft.TextField(label="用户数据目录", value=".xhs_profile", expand=True)
    
    dry_run_switch = ft.Switch(label="预览模式 (不实际点击发布)", value=False)
    headless_switch = ft.Switch(label="无头模式 (隐藏浏览器窗口)", value=False)

    log_view = ft.ListView(expand=True, spacing=5, padding=10)
    log_container = ft.Container(
        content=log_view,
        border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
        border_radius=10,
        bgcolor=ft.colors.GREY_50,
        height=300,
    )

    image_grid = ft.Row(wrap=True, spacing=10)

    # --- 逻辑处理 ---
    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            nonlocal selected_images
            selected_images = [Path(f.path) for f in e.files]
            image_grid.controls.clear()
            for img in selected_images:
                image_grid.controls.append(
                    ft.Container(
                        content=ft.Image(src=str(img), width=100, height=100, fit=ft.ImageFit.COVER),
                        border_radius=5,
                        border=ft.border.all(1, ft.colors.OUTLINE),
                    )
                )
            image_grid.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)

    def start_publish(e):
        if not title_input.value or not content_input.value or not selected_images:
            page.show_snack_bar(ft.SnackBar(ft.Text("请填写完整信息（标题、正文和图片）")))
            return

        # 禁用按钮防止重复点击
        btn_run.disabled = True
        btn_run.text = "正在运行..."
        page.update()

        def worker():
            # 重定向 stdout 到界面
            old_stdout = sys.stdout
            sys.stdout = Logger(log_view)
            
            try:
                config = PublishConfig(
                    title=title_input.value.strip(),
                    content=content_input.value.strip(),
                    images=selected_images,
                    topics=[t.strip() for t in topics_input.value.split(",") if t.strip()],
                    user_data_dir=Path(profile_input.value).resolve(),
                    headless=headless_switch.value,
                    slow_mo_ms=80,
                    wait_login_timeout_seconds=300,
                    dry_run=dry_run_switch.value,
                    browser_channel=None,
                    browser_executable_path=None,
                )
                
                print(f"[开始] 准备发布笔记: {config.title}")
                run(config)
                print("[成功] 任务处理完成")
            except Exception as ex:
                print(f"[错误] 系统异常: {str(ex)}")
            finally:
                sys.stdout = old_stdout
                btn_run.disabled = False
                btn_run.text = "开始发布"
                page.update()

        threading.Thread(target=worker, daemon=True).start()

    btn_run = ft.ElevatedButton("开始发布", icon=ft.icons.SEND, on_click=start_publish, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))

    # --- 布局组合 ---
    page.add(
        ft.Text("小红书自动发布工具", size=28, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        title_input,
        content_input,
        topics_input,
        ft.Row([
            ft.Text("图片列表:", weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("选择图片", icon=ft.icons.ADD_PHOTO_ALTERNATE, on_click=lambda _: file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        image_grid,
        ft.Divider(),
        ft.Row([profile_input]),
        ft.Row([headless_switch, dry_run_switch], alignment=ft.MainAxisAlignment.START),
        ft.Container(height=10),
        ft.Row([btn_run], alignment=ft.MainAxisAlignment.CENTER),
        ft.Text("运行日志:", weight=ft.FontWeight.BOLD),
        log_container,
    )

if __name__ == "__main__":
    ft.app(target=main)
