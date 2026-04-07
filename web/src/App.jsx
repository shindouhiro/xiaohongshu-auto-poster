import * as Switch from '@radix-ui/react-switch';
import { useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || '';
const API_ENDPOINT_LABEL = API_BASE || '同源代理 /api (Vite -> 127.0.0.1:8000)';

const INITIAL_FORM = {
  title: '',
  content: '',
  topics: '',
  images: '',
  userDataDir: '.xhs_profile',
  baseDir: '',
  browserChannel: 'chrome',
  browserExecutablePath: '',
  slowMoMs: '80',
  waitLoginTimeoutSeconds: '300',
  headless: false,
  dryRun: false,
};

function splitLines(value) {
  return value
    .split(/\n|,/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

function App() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const requestPayload = useMemo(
    () => ({
      title: form.title,
      content: form.content,
      topics: splitLines(form.topics).map((topic) => topic.replace(/^#/, '')),
      images: splitLines(form.images),
      user_data_dir: form.userDataDir,
      base_dir: form.baseDir || null,
      browser_channel: form.browserChannel || null,
      browser_executable_path: form.browserExecutablePath || null,
      slow_mo_ms: Number(form.slowMoMs),
      wait_login_timeout_seconds: Number(form.waitLoginTimeoutSeconds),
      headless: form.headless,
      dry_run: form.dryRun,
    }),
    [form],
  );

  function onInputChange(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/publish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      });
      const data = await response.json();
      if (!response.ok) {
        setResult({
          success: false,
          message: data.detail || `请求失败：HTTP ${response.status}`,
          logs: [],
          duration_seconds: 0,
        });
        return;
      }
      setResult(data);
    } catch (error) {
      const isNetworkError = error instanceof TypeError && /Failed to fetch/i.test(error.message);
      setResult({
        success: false,
        message: isNetworkError
          ? '无法连接发布后端，请先启动：uv run xhs-auto-post-ui --host 127.0.0.1 --port 8000 --reload'
          : error instanceof Error
            ? error.message
            : '请求失败，请检查后端服务',
        logs: [],
        duration_seconds: 0,
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-10">
      <section className="mx-auto w-full max-w-6xl animate-fade-up rounded-3xl border border-brand-100/70 bg-white/70 p-6 shadow-glass backdrop-blur-xl sm:p-8">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 inline-flex rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-brand-700">
              XHS Automation Console
            </p>
            <h1 className="font-display text-3xl font-semibold text-brand-800 sm:text-4xl">小红书一键发布控制台</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 sm:text-base">
              配置标题、正文和图片路径后，点击一次按钮即可触发发布流程。首次使用请先登录小红书账号。
            </p>
          </div>
          <div className="rounded-2xl border border-brand-100 bg-white/85 px-4 py-3 text-sm text-slate-600">
            <h2 className="font-display text-base font-semibold text-brand-700">API 端点</h2>
            <p id="api-base-url-text" className="mt-1 break-all text-xs text-slate-500">
              {API_ENDPOINT_LABEL}
            </p>
          </div>
        </header>

        <form className="grid gap-6 lg:grid-cols-2" onSubmit={onSubmit}>
          <div className="space-y-5 rounded-2xl border border-brand-100 bg-white/80 p-5 shadow-sm">
            <h3 className="font-display text-xl font-semibold text-brand-800">内容配置</h3>

            <div className="space-y-2">
              <label htmlFor="publish-title-input" className="text-sm font-medium text-slate-700">
                文本标题
              </label>
              <input
                id="publish-title-input"
                className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                placeholder="输入笔记标题"
                value={form.title}
                onChange={(event) => onInputChange('title', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="publish-content-textarea" className="text-sm font-medium text-slate-700">
                正文内容
              </label>
              <textarea
                id="publish-content-textarea"
                className="min-h-32 w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                placeholder="输入正文..."
                value={form.content}
                onChange={(event) => onInputChange('content', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="publish-topics-textarea" className="text-sm font-medium text-slate-700">
                话题（逗号或换行分隔）
              </label>
              <textarea
                id="publish-topics-textarea"
                className="min-h-20 w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                placeholder="#AI工具, 自动化"
                value={form.topics}
                onChange={(event) => onInputChange('topics', event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="publish-images-textarea" className="text-sm font-medium text-slate-700">
                图片路径（每行一个）
              </label>
              <textarea
                id="publish-images-textarea"
                className="min-h-24 w-full rounded-xl border border-brand-200 bg-white px-3 py-2 font-mono text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                placeholder="/Users/you/Desktop/demo-1.jpg"
                value={form.images}
                onChange={(event) => onInputChange('images', event.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-5 rounded-2xl border border-brand-100 bg-white/80 p-5 shadow-sm">
            <h3 className="font-display text-xl font-semibold text-brand-800">运行配置</h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <label htmlFor="publish-user-data-dir-input" className="text-sm font-medium text-slate-700">
                  登录态目录
                </label>
                <input
                  id="publish-user-data-dir-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  value={form.userDataDir}
                  onChange={(event) => onInputChange('userDataDir', event.target.value)}
                  required
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <label htmlFor="publish-base-dir-input" className="text-sm font-medium text-slate-700">
                  工作目录（可选）
                </label>
                <input
                  id="publish-base-dir-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  placeholder="默认当前启动目录"
                  value={form.baseDir}
                  onChange={(event) => onInputChange('baseDir', event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="publish-browser-channel-input" className="text-sm font-medium text-slate-700">
                  浏览器通道
                </label>
                <input
                  id="publish-browser-channel-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  value={form.browserChannel}
                  onChange={(event) => onInputChange('browserChannel', event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="publish-browser-exec-input" className="text-sm font-medium text-slate-700">
                  浏览器路径（可选）
                </label>
                <input
                  id="publish-browser-exec-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  value={form.browserExecutablePath}
                  onChange={(event) => onInputChange('browserExecutablePath', event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="publish-slowmo-input" className="text-sm font-medium text-slate-700">
                  慢动作毫秒
                </label>
                <input
                  id="publish-slowmo-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  type="number"
                  min="0"
                  value={form.slowMoMs}
                  onChange={(event) => onInputChange('slowMoMs', event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="publish-wait-timeout-input" className="text-sm font-medium text-slate-700">
                  登录超时（秒）
                </label>
                <input
                  id="publish-wait-timeout-input"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  type="number"
                  min="30"
                  value={form.waitLoginTimeoutSeconds}
                  onChange={(event) => onInputChange('waitLoginTimeoutSeconds', event.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4 rounded-xl border border-brand-100 bg-brand-50/60 p-4">
              <div className="flex items-center justify-between">
                <label htmlFor="publish-headless-switch" className="text-sm font-medium text-slate-700">
                  无头模式
                </label>
                <Switch.Root
                  id="publish-headless-switch"
                  className="relative h-6 w-11 rounded-full border border-brand-300 bg-white transition data-[state=checked]:bg-brand-500"
                  checked={form.headless}
                  onCheckedChange={(checked) => onInputChange('headless', checked)}
                >
                  <Switch.Thumb className="block h-5 w-5 translate-x-0.5 rounded-full bg-brand-200 shadow transition-transform data-[state=checked]:translate-x-[22px] data-[state=checked]:bg-white" />
                </Switch.Root>
              </div>

              <div className="flex items-center justify-between">
                <label htmlFor="publish-dryrun-switch" className="text-sm font-medium text-slate-700">
                  仅演练（不点击发布）
                </label>
                <Switch.Root
                  id="publish-dryrun-switch"
                  className="relative h-6 w-11 rounded-full border border-brand-300 bg-white transition data-[state=checked]:bg-brand-500"
                  checked={form.dryRun}
                  onCheckedChange={(checked) => onInputChange('dryRun', checked)}
                >
                  <Switch.Thumb className="block h-5 w-5 translate-x-0.5 rounded-full bg-brand-200 shadow transition-transform data-[state=checked]:translate-x-[22px] data-[state=checked]:bg-white" />
                </Switch.Root>
              </div>
            </div>

            <button
              id="publish-submit-button"
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-xl bg-gradient-to-r from-brand-500 to-brand-700 px-4 py-3 font-display text-base font-semibold text-white shadow-lg transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? '发布执行中，请稍候...' : '一键发布到小红书'}
            </button>
          </div>
        </form>

        <section className="mt-6 animate-fade-up rounded-2xl border border-brand-100 bg-white/85 p-5" style={{ animationDelay: '120ms' }}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-display text-xl font-semibold text-brand-800">执行结果</h3>
            {result ? (
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  result.success ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                }`}
              >
                {result.success ? '成功' : '失败'} · {result.duration_seconds}s
              </span>
            ) : (
              <span className="inline-flex animate-pulse-soft items-center rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500">
                等待执行
              </span>
            )}
          </div>

          <p id="publish-message-text" className="mb-3 text-sm text-slate-600">
            {result?.message || '尚未执行发布任务。'}
          </p>

          <pre
            id="publish-log-output"
            className="max-h-80 overflow-auto rounded-xl border border-brand-100 bg-slate-900 p-4 font-mono text-xs leading-6 text-slate-100"
          >
            {result?.logs?.length ? result.logs.join('\n') : '执行日志会展示在这里。'}
          </pre>
        </section>
      </section>
    </main>
  );
}

export default App;
