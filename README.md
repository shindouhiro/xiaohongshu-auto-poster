# 小红书登录后自动发布

一个基于 Playwright 的自动化工具，支持两种使用方式：

- CLI 配置文件发布
- Web UI 一键发布（可直接配置标题/正文/图片路径）

## 1. 环境准备

```bash
uv sync
uv run playwright install chromium
```

## 2. 准备发布配置

复制 `examples/post.json` 并按需修改：

- `title`: 标题
- `content`: 正文
- `images`: 图片路径数组（支持相对路径，基于配置文件目录）
- `topics`: 话题数组，会自动拼接为 `#话题`
- `user_data_dir`: 浏览器登录态目录（首次登录后会复用）
- `browser_channel`: 浏览器通道（推荐 `chrome`，可避免 Playwright 浏览器下载失败）
- `browser_executable_path`: 指定浏览器可执行文件路径（可选）
- `dry_run`: `true` 时只填充不点击发布，建议先联调

> 提示：`examples/post.json` 默认引用 `./demo-1.jpg`，请替换成你真实存在的图片。

## 3. CLI 运行

```bash
uv run xhs-auto-post --config examples/post.json
```

运行后：

1. 脚本会拉起浏览器并等待你登录。
2. 登录状态检测成功后，自动进入发布页。
3. 自动上传图片、填写标题和正文。
4. `dry_run=false` 时自动点击发布。

若本机未安装 Playwright Chromium，脚本会自动尝试回退到系统 Chrome（前提是本机已安装）。

## 4. Web UI 运行

### 4.1 启动后端 API

```bash
uv run xhs-auto-post-ui --host 127.0.0.1 --port 8000 --reload
```

### 4.2 启动前端页面

```bash
cd web
pnpm install
pnpm dev
```

`pnpm dev` 会同时启动：

- Web 前端（Vite）
- 小红书发布后端 API（若检测到 `8000` 已有服务会自动复用）

浏览器打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)（若端口占用会自动切换到下一个端口，终端会显示实际地址）。

页面支持配置：

- 文本标题
- 正文内容
- 话题
- 图片路径（每行一个）
- 登录态目录、浏览器参数、dry_run 等运行选项

点击「一键发布到小红书」后，会在页面下方展示执行日志。

> 注意：Web UI 仍会拉起本地浏览器并复用登录态；首次使用需要扫码登录。

## 5. 常见问题

- 页面元素找不到：小红书页面结构可能升级，需更新选择器。
- 登录超时：增大 `wait_login_timeout_seconds`。
- 首次无法复用登录：检查 `user_data_dir` 是否可写。
- Web UI 显示 `Failed to fetch`：通常是后端 API 未启动。先运行 `uv run xhs-auto-post-ui --host 127.0.0.1 --port 8000 --reload`，再执行发布。

## 6. 合规提醒

自动化发布前请确认符合平台规则与账号安全要求，避免触发风控。
