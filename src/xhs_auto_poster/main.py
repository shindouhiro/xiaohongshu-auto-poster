from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Error, Page, TimeoutError, sync_playwright

PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"


@dataclass
class PublishConfig:
    title: str
    content: str
    images: list[Path]
    topics: list[str]
    user_data_dir: Path
    headless: bool
    slow_mo_ms: int
    wait_login_timeout_seconds: int
    dry_run: bool
    browser_channel: str | None
    browser_executable_path: str | None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("配置文件根节点必须是 JSON 对象")
    return data


def _resolve_images(base_dir: Path, values: Any) -> list[Path]:
    if not isinstance(values, list) or not values:
        raise ValueError("`images` 必须是非空数组")

    result: list[Path] = []
    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("`images` 中每个元素都必须是非空字符串")
        p = Path(raw)
        if not p.is_absolute():
            p = (base_dir / p).resolve()
        if not p.exists():
            raise FileNotFoundError(f"图片不存在: {p}")
        result.append(p)
    return result


def _normalize_topics(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("`topics` 必须是数组")

    topics: list[str] = []
    for topic in values:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("`topics` 中每个元素都必须是非空字符串")
        topics.append(topic.strip())
    return topics


def _build_config_from_raw(raw: dict[str, Any], base_dir: Path) -> PublishConfig:
    if not isinstance(raw, dict):
        raise ValueError("配置内容必须是 JSON 对象")

    title = raw.get("title", "")
    content = raw.get("content", "")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("`title` 必须是非空字符串")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("`content` 必须是非空字符串")

    topics = _normalize_topics(raw.get("topics", []))
    images = _resolve_images(base_dir, raw.get("images"))

    user_data_dir_raw = raw.get("user_data_dir", ".xhs_profile")
    if not isinstance(user_data_dir_raw, str) or not user_data_dir_raw.strip():
        raise ValueError("`user_data_dir` 必须是非空字符串")

    user_data_dir = Path(user_data_dir_raw)
    if not user_data_dir.is_absolute():
        user_data_dir = (base_dir / user_data_dir).resolve()

    headless = bool(raw.get("headless", False))
    slow_mo_ms = int(raw.get("slow_mo_ms", 80))
    wait_login_timeout_seconds = int(raw.get("wait_login_timeout_seconds", 300))
    dry_run = bool(raw.get("dry_run", False))
    browser_channel_raw = raw.get("browser_channel")
    browser_executable_path_raw = raw.get("browser_executable_path")

    browser_channel: str | None = None
    if browser_channel_raw is not None:
        if not isinstance(browser_channel_raw, str) or not browser_channel_raw.strip():
            raise ValueError("`browser_channel` 必须是非空字符串或 null")
        browser_channel = browser_channel_raw.strip()

    browser_executable_path: str | None = None
    if browser_executable_path_raw is not None:
        if not isinstance(browser_executable_path_raw, str) or not browser_executable_path_raw.strip():
            raise ValueError("`browser_executable_path` 必须是非空字符串或 null")
        raw_path = Path(browser_executable_path_raw)
        if not raw_path.is_absolute():
            raw_path = (base_dir / raw_path).resolve()
        browser_executable_path = str(raw_path)

    return PublishConfig(
        title=title.strip(),
        content=content.strip(),
        images=images,
        topics=topics,
        user_data_dir=user_data_dir,
        headless=headless,
        slow_mo_ms=slow_mo_ms,
        wait_login_timeout_seconds=wait_login_timeout_seconds,
        dry_run=dry_run,
        browser_channel=browser_channel,
        browser_executable_path=browser_executable_path,
    )


def build_config_from_file(config_path: Path) -> PublishConfig:
    raw = _load_json(config_path)
    return _build_config_from_raw(raw, base_dir=config_path.parent.resolve())


def build_config_from_dict(raw: dict[str, Any], base_dir: Path) -> PublishConfig:
    return _build_config_from_raw(raw, base_dir=base_dir.resolve())


def _format_content(config: PublishConfig) -> str:
    if not config.topics:
        return config.content
    hashtags = " ".join(f"#{topic}" for topic in config.topics)
    return f"{config.content}\n\n{hashtags}"


def _has_any_visible(page: Page, selectors: list[str], timeout_ms: int = 600) -> bool:
    for selector in selectors:
        try:
            if page.locator(selector).first.is_visible(timeout=timeout_ms):
                return True
        except Error:
            continue
        except TimeoutError:
            continue
    return False


def _is_image_file_input_accept(accept: str) -> bool:
    value = accept.lower()
    return (
        "image" in value
        or ".jpg" in value
        or ".jpeg" in value
        or ".png" in value
        or ".webp" in value
    )


def _find_image_file_input(page: Page) -> Any:
    locator = page.locator("input[type='file']")
    try:
        count = locator.count()
    except Error:
        count = 0

    for i in range(count):
        candidate = locator.nth(i)
        try:
            accept = candidate.get_attribute("accept") or ""
        except Error:
            continue
        if _is_image_file_input_accept(accept):
            return candidate
    return None


def _click_first_available(page: Page, selectors: list[str], field_name: str) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=1_500)
            locator.click()
            print(f"[状态] 已点击{field_name}，命中选择器: {selector}")
            return True
        except TimeoutError:
            continue
        except Error:
            continue
    return False


def _click_upload_image_tab(page: Page) -> bool:
    title_tabs = page.locator("span.title:has-text('上传图文')")
    try:
        count = title_tabs.count()
    except Error:
        count = 0

    for i in range(count):
        tab = title_tabs.nth(i)
        try:
            tab.wait_for(state="visible", timeout=1_500)
            box = tab.bounding_box()
            if not box or box["x"] < 0 or box["y"] < 0:
                continue
            tab.evaluate(
                "el => (el.closest('.creator-tab') || el.closest('button,[role=button],div,span') || el).click()"
            )
            print("[状态] 已点击上传图文入口，命中选择器: span.title:has-text('上传图文')")
            return True
        except TimeoutError:
            continue
        except Error:
            continue

    # 兜底：使用 text 节点，始终点击其可点击父级。
    text_nodes = page.locator("text=上传图文")
    try:
        text_count = text_nodes.count()
    except Error:
        text_count = 0
    for i in range(text_count):
        node = text_nodes.nth(i)
        try:
            node.wait_for(state="visible", timeout=1_200)
            box = node.bounding_box()
            if not box or box["x"] < 0 or box["y"] < 0:
                continue
            node.evaluate(
                "el => (el.closest('.creator-tab') || el.closest('button,[role=button],li,div,span') || el).click()"
            )
            print("[状态] 已点击上传图文入口，命中选择器: text=上传图文")
            return True
        except TimeoutError:
            continue
        except Error:
            continue

    return False


def _debug_editable_elements(page: Page) -> None:
    try:
        items = page.evaluate(
            """
            () => {
              const nodes = Array.from(
                document.querySelectorAll("input, textarea, div[contenteditable='true'], [role='textbox']")
              );
              const visible = nodes.filter((el) => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
              });
              return visible.slice(0, 12).map((el) => ({
                tag: el.tagName.toLowerCase(),
                placeholder: el.getAttribute("placeholder") || "",
                dataPlaceholder: el.getAttribute("data-placeholder") || "",
                ariaLabel: el.getAttribute("aria-label") || "",
                role: el.getAttribute("role") || "",
                className: (el.getAttribute("class") || "").slice(0, 120),
                text: (el.innerText || "").slice(0, 50),
              }));
            }
            """
        )
    except Error:
        return

    if not isinstance(items, list):
        return

    print(f"[调试] 可编辑控件数量(截断): {len(items)}")
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        print(
            "[调试] "
            f"#{idx} tag={item.get('tag','')} "
            f"placeholder={item.get('placeholder','')!r} "
            f"data-placeholder={item.get('dataPlaceholder','')!r} "
            f"aria-label={item.get('ariaLabel','')!r} "
            f"role={item.get('role','')!r} "
            f"class={item.get('className','')!r} "
            f"text={item.get('text','')!r}"
        )


def _is_publish_surface_ready(page: Page) -> bool:
    return _has_any_visible(
        page,
        selectors=[
            "input[type='file']",
            "input[placeholder*='标题']",
            "textarea[placeholder*='标题']",
            "div[contenteditable='true'][data-placeholder*='标题']",
            "textarea[placeholder*='描述']",
            "div[contenteditable='true'][data-placeholder*='描述']",
            "text=/发布图文|图文笔记|发布笔记|上传图片/",
        ],
    )


def _ensure_image_publish_mode(page: Page) -> None:
    # 新版发布页默认常驻“上传视频”，需要显式切换到“上传图文”。
    _click_first_available(
        page,
        selectors=[
            "span.btn-text:has-text('发布笔记')",
            "button:has-text('发布笔记')",
            "text=/发布笔记/",
        ],
        field_name="发布笔记入口",
    )
    page.wait_for_timeout(800)

    deadline = time.time() + 15
    while time.time() < deadline:
        if _find_image_file_input(page) is not None:
            return

        _click_upload_image_tab(page)
        time.sleep(0.8)

    accepts = page.locator("input[type='file']").evaluate_all(
        "els => els.map(e => e.getAttribute('accept') || '')"
    )
    raise RuntimeError(f"未切换到图文上传模式，当前 file accept: {accepts}")


def _wait_until_editor_controls_ready(page: Page, timeout_seconds: int = 30) -> None:
    selectors = [
        "div.d-input input",
        "div.d-input-wrapper input",
        "input[placeholder*='标题']",
        "textarea[placeholder*='标题']",
        "div[contenteditable='true'][data-placeholder*='标题']",
        "div[contenteditable='true'][placeholder*='标题']",
        "textarea[placeholder*='描述']",
        "textarea[placeholder*='正文']",
        "div[contenteditable='true'][data-placeholder*='描述']",
        "div[contenteditable='true'][placeholder*='描述']",
        "input:visible",
        "textarea:visible",
        "div[contenteditable='true']:visible",
        "[role='textbox']:visible",
    ]
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _has_any_visible(page, selectors, timeout_ms=800):
            return
        time.sleep(1)

    _debug_editable_elements(page)
    raise TimeoutError("上传后等待编辑区输入控件超时")


def _fill_body_with_keyboard_fallback(page: Page, text: str) -> None:
    sample = text.strip().replace("\n", " ")
    if not sample:
        raise RuntimeError("正文为空，无法进行键盘兜底输入")

    snippet = sample[:10]
    page.keyboard.press("Tab")
    page.keyboard.type(text, delay=10)
    page.wait_for_timeout(500)

    if page.locator(f"text={snippet}").count() > 0:
        print("[状态] 已通过键盘 Tab 兜底填写正文。")
        return

    # 第二层兜底：靠近正文工具栏左侧区域点击后输入。
    topic_btn = page.locator("#topicBtn").first
    try:
        box = topic_btn.bounding_box()
    except Error:
        box = None

    if box:
        x = max(16, box["x"] - 220)
        y = max(16, box["y"] - 40)
        page.mouse.click(x, y)
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type(text, delay=10)
        page.wait_for_timeout(500)
        if page.locator(f"text={snippet}").count() > 0:
            print("[状态] 已通过坐标点击兜底填写正文。")
            return

    raise RuntimeError("正文键盘兜底填写失败，页面结构可能已变化")


def _ensure_graphic_editor_ready(page: Page) -> None:
    if _has_any_visible(page, ["input[type='file']"]):
        return

    _click_first_available(
        page,
        selectors=[
            "button:has-text('发布图文')",
            "button:has-text('图文笔记')",
            "button:has-text('图文')",
            "div:has-text('发布图文')",
            "div:has-text('图文笔记')",
            "text=/发布图文|图文笔记|图文/",
        ],
        field_name="图文发布入口",
    )


def _wait_until_login_done(page: Page, timeout_seconds: int) -> None:
    print("[步骤 1/3] 正在等待你完成登录...")
    print("请在弹出的浏览器中登录小红书账号，登录完成后将自动继续。")

    page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30_000)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if "creator.xiaohongshu.com" in page.url:
            if _is_publish_surface_ready(page):
                print("[状态] 已检测到登录态。")
                return

        time.sleep(2)

    raise TimeoutError("等待登录超时，请检查网络或扫码状态")


def _fill_locator_text(locator: Any, text: str) -> None:
    locator.click()
    try:
        locator.fill(text)
    except Error:
        # contenteditable 结构通常不支持 fill，这里降级为键盘输入。
        locator.press("ControlOrMeta+A")
        locator.type(text, delay=10)


def _try_fill_input(
    page: Page,
    selectors: list[str],
    text: str,
    field_name: str,
    fallback_index: int = 0,
) -> None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=4_000)
            _fill_locator_text(locator, text)
            print(f"[状态] 已填写{field_name}，命中选择器: {selector}")
            return
        except TimeoutError:
            continue
        except Error:
            continue

    # 兜底：页面结构变化时，按可见输入框顺序尝试填写。
    fallback_groups = [
        "input:visible",
        "textarea:visible",
        "div[contenteditable='true']:visible",
        "[role='textbox']:visible",
    ]
    candidates: list[Any] = []
    for group in fallback_groups:
        locator = page.locator(group)
        try:
            count = locator.count()
        except Error:
            continue
        for i in range(min(count, 6)):
            candidates.append(locator.nth(i))

    if len(candidates) > fallback_index:
        try:
            _fill_locator_text(candidates[fallback_index], text)
            print(f"[状态] 已填写{field_name}，命中兜底输入框序号: {fallback_index + 1}")
            return
        except Error:
            pass

    _debug_editable_elements(page)
    raise RuntimeError(f"未找到可用的{field_name}输入框，页面结构可能已变化")


def _publish_note(page: Page, config: PublishConfig) -> None:
    print("[步骤 2/3] 进入发布页并填写内容...")
    page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=30_000)
    _ensure_graphic_editor_ready(page)
    _ensure_image_publish_mode(page)

    file_input = _find_image_file_input(page)
    if file_input is None:
        _click_first_available(
            page,
            selectors=[
                "span:has-text('上传图文')",
                "button:has-text('发布图文')",
                "div:has-text('发布图文')",
                "button:has-text('上传图片')",
                "div:has-text('上传图片')",
                "text=/发布图文|上传图文|上传图片/",
            ],
            field_name="图文/上传入口",
        )
        page.wait_for_timeout(1000)
        file_input = _find_image_file_input(page)

    if file_input is None:
        accepts = page.locator("input[type='file']").evaluate_all(
            "els => els.map(e => e.getAttribute('accept') || '')"
        )
        raise RuntimeError(f"未找到图文上传文件框，当前 file accept: {accepts}")

    file_input.set_input_files([str(p) for p in config.images])
    print(f"[状态] 已上传图片 {len(config.images)} 张")
    _wait_until_editor_controls_ready(page, timeout_seconds=30)

    _try_fill_input(
        page,
        selectors=[
            "div.d-input input",
            "div.d-input-wrapper input",
            "input[placeholder*='标题']",
            "textarea[placeholder*='标题']",
            "div[contenteditable='true'][data-placeholder*='标题']",
            "div[contenteditable='true'][placeholder*='标题']",
        ],
        text=config.title,
        field_name="标题",
        fallback_index=0,
    )

    body_text = _format_content(config)
    try:
        _try_fill_input(
            page,
            selectors=[
                "div[role='textbox']",
                "div.tiptap.ProseMirror",
                "div.ProseMirror[role='textbox']",
                "div[contenteditable='true'][data-placeholder*='描述']",
                "div[contenteditable='true'][placeholder*='描述']",
                "textarea[placeholder*='描述']",
                "textarea[placeholder*='正文']",
            ],
            text=body_text,
            field_name="正文",
            fallback_index=1,
        )
    except RuntimeError:
        _fill_body_with_keyboard_fallback(page, body_text)

    if config.dry_run:
        print("[步骤 3/3] dry_run=true，已跳过点击发布。")
        return

    print("[步骤 3/3] 点击发布...")
    publish_selectors = [
        "button:has-text('发布')",
        "button:has-text('发布笔记')",
        "span.btn-text:has-text('发布笔记')",
        "text=/发布笔记|发布/",
        "button[type='submit']",
    ]

    for selector in publish_selectors:
        button = page.locator(selector).first
        try:
            button.wait_for(state="visible", timeout=2_000)
            button.click()
            print(f"[状态] 已触发发布，命中选择器: {selector}")
            break
        except TimeoutError:
            continue
        except Error:
            try:
                button.evaluate("el => (el.closest('button,[role=button],div') || el).click()")
                print(f"[状态] 已通过父节点触发发布，命中选择器: {selector}")
                break
            except Error:
                continue
    else:
        raise RuntimeError("未找到发布按钮，页面结构可能已变化")

    try:
        page.wait_for_selector("text=/发布成功|发布中|审核中/", timeout=10_000)
    except TimeoutError:
        # 某些账号不会立即出现提示文案，不阻断流程。
        pass

    print("[完成] 发布流程已执行完成。")


def run(config: PublishConfig) -> None:
    config.user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(config.user_data_dir),
            "headless": config.headless,
            "slow_mo": config.slow_mo_ms,
            "viewport": {"width": 1440, "height": 900},
        }

        if config.browser_channel:
            launch_kwargs["channel"] = config.browser_channel
        if config.browser_executable_path:
            launch_kwargs["executable_path"] = config.browser_executable_path

        try:
            context = p.chromium.launch_persistent_context(**launch_kwargs)
        except Error as e:
            if "Executable doesn't exist" not in str(e):
                raise
            if config.browser_channel or config.browser_executable_path:
                raise
            print("[状态] 未检测到 Playwright 自带 Chromium，自动回退到系统 Chrome。")
            launch_kwargs["channel"] = "chrome"
            context = p.chromium.launch_persistent_context(**launch_kwargs)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            _wait_until_login_done(page, config.wait_login_timeout_seconds)
            _publish_note(page, config)
        finally:
            context.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="小红书登录后自动发布")
    parser.add_argument(
        "--config",
        default="examples/post.json",
        help="配置文件路径，默认 examples/post.json",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    try:
        config = build_config_from_file(Path(args.config).resolve())
        run(config)
        return 0
    except Exception as e:
        print(f"[错误] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
