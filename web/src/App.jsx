import * as Switch from '@radix-ui/react-switch';
import { useMemo, useState, useEffect } from 'react';

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
  const [isSelectingLocal, setIsSelectingLocal] = useState(false);
  const [uploadImages, setUploadImages] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [availableAccounts, setAvailableAccounts] = useState([]);

  useEffect(() => {
    async function fetchAccounts() {
      try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.get_accounts) {
          const res = await window.pywebview.api.get_accounts();
          if (res.status === 'success') {
            setAvailableAccounts(res.accounts);
          }
        } else {
          const response = await fetch(`${API_BASE}/api/accounts`);
          const data = await response.json();
          if (data.accounts) setAvailableAccounts(data.accounts);
        }
      } catch (error) {
        console.error('获取账号列表失败', error);
      }
    }
    fetchAccounts();
  }, []);

  const requestPayload = useMemo(
    () => ({
      title: form.title,
      content: form.content,
      topics: splitLines(form.topics).map((topic) => topic.replace(/^#/, '')),
      images: [...splitLines(form.images), ...uploadImages.map((img) => img.data)],
      user_data_dir: form.userDataDir,
      base_dir: form.baseDir || null,
      browser_channel: form.browserChannel || null,
      browser_executable_path: form.browserExecutablePath || null,
      slow_mo_ms: Number(form.slowMoMs),
      wait_login_timeout_seconds: Number(form.waitLoginTimeoutSeconds),
      headless: form.headless,
      dry_run: form.dryRun,
    }),
    [form, uploadImages],
  );

  function onInputChange(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setUploadImages((prev) => [
          ...prev,
          { id: Math.random().toString(36).slice(2), name: file.name, data: evt.target.result },
        ]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = null;
  };

  const removeUploadImage = (id) => {
    setUploadImages((prev) => prev.filter((img) => img.id !== id));
  };

  const handleNativeSelect = async () => {
    setIsSelectingLocal(true);
    try {
      let paths = [];
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.select_images();
        if (res.status === 'success') {
          paths = res.paths;
        }
      } else {
        const response = await fetch(`${API_BASE}/api/select_images`);
        const data = await response.json();
        if (data.paths) {
          paths = data.paths;
        }
      }
      
      if (paths.length > 0) {
        onInputChange('images', prev => {
          const current = splitLines(prev);
          return [...new Set([...current, ...paths])].join('\n');
        });
      }
    } catch (error) {
      console.error('选择图片失败', error);
      alert('无法唤起本地文件选择，请手动粘贴图片路径');
    } finally {
      setIsSelectingLocal(false);
    }
  };

  async function onSubmit(event) {
    event.preventDefault();
    if (requestPayload.images.length === 0) {
      alert('请至少上传一张图片或输入图片路径！');
      return;
    }
    setIsSubmitting(true);
    setResult(null);

    // --- 新增：兼容桌面应用模式 ---
    if (window.pywebview && window.pywebview.api) {
      try {
        console.log('检测到桌面应用环境，正在通过 Bridge 调用后端...');
        const data = await window.pywebview.api.publish_note(requestPayload);
        
        // 统一接口返回格式
        setResult({
          success: data.status === 'success',
          message: data.message,
          logs: data.logs || [],
          duration_seconds: data.duration || 0,
        });
      } catch (error) {
        setResult({
          success: false,
          message: `桌面端调用异常: ${error.message}`,
          logs: [],
          duration_seconds: 0,
        });
      } finally {
        setIsSubmitting(false);
      }
      return;
    }
    // --- 桌面模式结束 ---

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

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">笔记图片</label>
                <button
                  type="button"
                  onClick={handleNativeSelect}
                  disabled={isSelectingLocal}
                  className="rounded-lg bg-brand-100 px-3 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-200 disabled:opacity-50"
                  title="唤起系统的原生文件选择对话框获取绝对路径"
                >
                  {isSelectingLocal ? '正在唤起对话框...' : '浏览本地图片获取路径'}
                </button>
              </div>
              
              <div className="relative flex cursor-pointer flex-col items-center justify-center space-y-2 overflow-hidden rounded-xl border-2 border-dashed border-brand-200 bg-brand-50/50 p-6 text-center transition hover:border-brand-400 hover:bg-brand-50">
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                />
                <div className="text-brand-600">
                  <svg className="mb-1 h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-brand-700">点击或拖拽上传多张图片</p>
                <p className="text-xs text-brand-400">支持 JPG, PNG 等常见格式</p>
              </div>

              {uploadImages.length > 0 && (
                <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-brand-200">
                  {uploadImages.map((img) => (
                    <div key={img.id} className="group relative h-28 w-28 shrink-0 snap-center overflow-hidden rounded-lg border border-brand-100 bg-white shadow-sm">
                      <img src={img.data} alt="preview" className="h-full w-full object-cover transition group-hover:scale-105" />
                      <button
                        type="button"
                        onClick={() => removeUploadImage(img.id)}
                        className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-white opacity-0 backdrop-blur-sm transition hover:bg-rose-500 group-hover:opacity-100"
                        title="移除图片"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                      <div className="absolute bottom-0 left-0 right-0 truncate bg-black/40 px-1.5 py-1 text-[10px] text-white">
                        {img.name}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <details className="group">
                <summary className="mt-1 cursor-pointer text-xs text-brand-500 hover:text-brand-600">
                  使用本地绝对路径 (高级)
                </summary>
                <textarea
                  id="publish-images-textarea"
                  className="mt-2 min-h-24 w-full rounded-xl border border-brand-200 bg-white px-3 py-2 font-mono text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  placeholder="如果图片已在电脑上，可直接输入绝对路径（每行一个）&#10;/Users/you/Desktop/demo-1.jpg"
                  value={form.images}
                  onChange={(event) => onInputChange('images', event.target.value)}
                />
              </details>
            </div>
          </div>

          <div className="space-y-5 rounded-2xl border border-brand-100 bg-white/80 p-5 shadow-sm">
            <h3 className="font-display text-xl font-semibold text-brand-800">运行配置</h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <label htmlFor="publish-user-data-dir-input" className="text-sm font-medium text-slate-700">
                  登录账号缓存标识 (可下拉选择或自定义新名称)
                </label>
                <input
                  id="publish-user-data-dir-input"
                  list="accounts-list"
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-300"
                  value={form.userDataDir}
                  onChange={(event) => onInputChange('userDataDir', event.target.value)}
                  placeholder=".xhs_profile_my_account"
                  required
                />
                <datalist id="accounts-list">
                  {availableAccounts.map(acc => (
                    <option key={acc} value={acc} />
                  ))}
                </datalist>
                <p className="text-[11px] text-slate-400">切换不同的缓存文件夹名，即可实现多账号登录状态分离。若输入全新的名称，首次执行时会要求扫码登录。</p>
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
