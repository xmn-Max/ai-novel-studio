<<<<<<< HEAD
import { useState, useCallback, useEffect, useRef } from 'react';
import {
  startConversion,
  subscribeProgress,
  fetchResult,
  fetchGenres,
  addGenre,
  updateGenre,
  deleteGenre,
  register,
  login,
  fetchCurrentUser,
  logout,
  regenerate,
  fetchConversions,
  deleteConversion,
  editConversion,
  ProgressEvent,
  ConversionResult,
  GenreItem,
  ConversionSummary,
} from './api';

type Phase = 'idle' | 'converting' | 'done';

const STEP_LABELS = ['文本清洗', '章节检测', '角色提取', '场景切分', '剧本转换', '主角验证', 'Schema校验'];

const CHAPTER_RE = /第[一二三四五六七八九十百千万\d]+章/g;

function countChapters(text: string): number {
  const matches = text.match(CHAPTER_RE);
  return matches ? matches.length : 0;
}

interface ChapterData {
  name: string;
  scenes: SceneData[];
}

interface SceneData {
  heading: string;
  actions: string[];
  dialogues: DialogueData[];
}

interface DialogueData {
  character: string;
  line: string;
}

function parseYamlToStructure(yaml: string): ChapterData[] {
  const chapters: ChapterData[] = [];
  const lines = yaml.split('\n');
  let currentChapter: ChapterData | null = null;
  let currentScene: SceneData | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line) continue;

    const indent = rawLine.length - rawLine.trimStart().length;

    if (indent === 0 && line.startsWith('- chapter:')) {
      const name = line.slice('- chapter:'.length).trim();
      currentChapter = { name, scenes: [] };
      currentScene = null;
      chapters.push(currentChapter);
    } else if (indent === 2 && line.startsWith('- scene:')) {
      const heading = line.slice('- scene:'.length).trim();
      currentScene = { heading, actions: [], dialogues: [] };
      if (currentChapter) {
        currentChapter.scenes.push(currentScene);
      }
    } else if (indent === 4 && line.startsWith('- ') && currentScene) {
      const body = line.slice(2).trim();
      if (body.startsWith('[') && body.endsWith(']')) {
        currentScene.actions.push(body.slice(1, -1).trim());
      }
    } else if (indent === 6 && line.startsWith('- ') && currentScene) {
      const body = line.slice(2).trim();
      const match = body.match(/^\[(.*?)\]\s*(.+)/);
      if (match) {
        currentScene.dialogues.push({
          character: match[1].trim(),
          line: match[2].trim(),
        });
      }
    }
  }

  return chapters;
}

function highlightYaml(yaml: string) {
  return yaml.split('\n').map((line, i) => {
    const trimmed = line.trimStart();
    let cls = 'text-slate-500';
    if (trimmed.startsWith('#')) {
      cls = 'text-slate-400 italic';
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('  - ')) {
      cls = 'text-indigo-700';
    } else if (trimmed.includes(':')) {
      const keyPart = trimmed.split(':')[0];
      if (keyPart.match(/^[\w\u4e00-\u9fff]+$/)) {
        cls = 'text-emerald-700';
      }
    }
    return (
      <div key={i} className="flex">
        <span className="select-none text-slate-300 w-10 text-right pr-3 shrink-0 text-xs leading-6">
          {i + 1}
        </span>
        <span className={cls + ' whitespace-pre-wrap break-all leading-6'}>{line || ' '}</span>
      </div>
    );
  });
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function downloadYaml(yaml: string) {
  const blob = new Blob([yaml], { type: 'application/x-yaml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'script.yaml';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function App() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('叙事');
  const [genres, setGenres] = useState<GenreItem[]>([]);
  const [showGenreModal, setShowGenreModal] = useState(false);
  const [editGenreIndex, setEditGenreIndex] = useState<number | null>(null);
  const [editGenreName, setEditGenreName] = useState('');
  const [editGenreGuidance, setEditGenreGuidance] = useState('');
  const [editGenreKeywords, setEditGenreKeywords] = useState('');
  const [genreError, setGenreError] = useState('');

  const [username, setUsername] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');

  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [activeTab, setActiveTab] = useState<'yaml' | 'structured'>('yaml');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hints, setHints] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [hintsError, setHintsError] = useState('');
  const [hintsSkipped, setHintsSkipped] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [conversions, setConversions] = useState<ConversionSummary[]>([]);
  const [conversionsLoading, setConversionsLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedYaml, setEditedYaml] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const msgRef = useRef<HTMLDivElement>(null);

  const chapterCount = countChapters(text);
  const canConvert = text.length > 100 && chapterCount >= 3;

  useEffect(() => {
    if (phase === 'converting' && taskId) {
      const unsub = subscribeProgress(
        taskId,
        (e) => setProgress(e),
        async () => {
          try {
            const res = await fetchResult(taskId);
            setResult(res);
            setPhase('done');
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : '获取结果失败');
          }
        },
        (err) => setError(err),
      );
      return unsub;
    }
  }, [phase, taskId]);

  const handleConvert = useCallback(async () => {
    if (!canConvert) return;
    setError(null);
    setPhase('converting');
    setProgress(null);
    setResult(null);
    try {
      const { task_id } = await startConversion(text, genre, title);
      setTaskId(task_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '启动失败');
      setPhase('idle');
    }
  }, [text, canConvert]);

  const handleReset = useCallback(() => {
    setPhase('idle');
    setText('');
    setTaskId(null);
    setProgress(null);
    setResult(null);
    setError(null);
    setEditing(false);
    setEditedYaml('');
    setEditError('');
    setHints('');
    setHintsSkipped(false);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const user = await fetchCurrentUser();
        if (user) {
          setUsername(user.username);
          setLoggedIn(true);
        }
      } catch {
        // not logged in
      }
      setAuthLoading(false);
    })();
  }, []);

  const loadGenres = useCallback(async () => {
    try {
      const list = await fetchGenres();
      setGenres(list);
      if (list.length > 0 && !list.find((g) => g.name === genre)) {
        setGenre(list[0].name);
      }
    } catch {
      // keep defaults
    }
  }, []);

  const handleRegister = useCallback(async () => {
    setAuthError('');
    try {
      const user = await register(authUsername, authPassword);
      setUsername(user.username);
      setLoggedIn(true);
      await loadGenres();
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : '注册失败');
    }
  }, [authUsername, authPassword, loadGenres]);

  const handleLogin = useCallback(async () => {
    setAuthError('');
    try {
      const user = await login(authUsername, authPassword);
      setUsername(user.username);
      setLoggedIn(true);
      await loadGenres();
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : '登录失败');
    }
  }, [authUsername, authPassword, loadGenres]);

  const handleLogout = useCallback(() => {
    logout();
    setLoggedIn(false);
    setUsername('');
    setPhase('idle');
    setText('');
    setResult(null);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        authMode === 'login' ? handleLogin() : handleRegister();
      }
    },
    [authMode, handleLogin, handleRegister]
  );

  const handleRegenerate = useCallback(async () => {
    if (!taskId || !hints.trim()) {
      setHintsError('请输入补充信息');
      return;
    }
    setRegenerating(true);
    setHintsError('');
    try {
      const updated = await regenerate(taskId, hints.trim());
      setResult(updated);
      setHints('');
    } catch (err: unknown) {
      setHintsError(err instanceof Error ? err.message : '重新生成失败');
    }
    setRegenerating(false);
  }, [taskId, hints]);

  const handleSkipRevalidate = useCallback(() => {
    setHints('');
    setHintsSkipped(true);
  }, []);

  const loadConversions = useCallback(async () => {
    setConversionsLoading(true);
    try {
      const list = await fetchConversions();
      setConversions(list);
    } catch {
      // silently fail
    }
    setConversionsLoading(false);
  }, []);

  const viewConversion = useCallback(async (convId: string) => {
    setShowHistory(false);
    setError(null);
    setProgress(null);
    try {
      const res = await fetchResult(convId);
      setResult(res);
      setTaskId(convId);
      setPhase('done');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载失败');
    }
  }, []);

  const handleDeleteConversion = useCallback(async (convId: string) => {
    try {
      await deleteConversion(convId);
      setConversions((prev) => prev.filter((c) => c.id !== convId));
      if (taskId === convId) {
        setPhase('idle');
        setResult(null);
        setTaskId(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  }, [taskId]);

  const handleStartEdit = useCallback(() => {
    if (!result) return;
    setEditedYaml(result.yaml);
    setEditing(true);
    setEditError('');
  }, [result]);

  const handleCancelEdit = useCallback(() => {
    setEditing(false);
    setEditedYaml('');
    setEditError('');
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!taskId) return;
    setEditSaving(true);
    setEditError('');
    try {
      const updated = await editConversion(taskId, editedYaml);
      setResult(updated);
      setEditing(false);
      setEditedYaml('');
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : '保存失败');
    }
    setEditSaving(false);
  }, [taskId, editedYaml]);

  const handleSaveGenre = useCallback(async () => {
    setGenreError('');
    if (!editGenreName.trim()) {
      setGenreError('类型名称不能为空');
      return;
    }
    const item: GenreItem = {
      name: editGenreName.trim(),
      guidance: editGenreGuidance.trim(),
      keywords: editGenreKeywords.split(/[,，]/).map((k) => k.trim()).filter(Boolean),
    };
    try {
      if (editGenreIndex !== null) {
        await updateGenre(editGenreIndex, item);
      } else {
        await addGenre(item);
      }
      await loadGenres();
      setShowGenreModal(false);
    } catch (err: unknown) {
      setGenreError(err instanceof Error ? err.message : '保存失败');
    }
  }, [editGenreName, editGenreGuidance, editGenreKeywords, editGenreIndex, loadGenres]);

  const handleDeleteGenre = useCallback(async (index: number) => {
    setGenreError('');
    try {
      await deleteGenre(index);
      await loadGenres();
    } catch (err: unknown) {
      setGenreError(err instanceof Error ? err.message : '删除失败');
    }
  }, [loadGenres]);

  const handleEditGenre = useCallback((index: number) => {
    const g = genres[index];
    setEditGenreIndex(index);
    setEditGenreName(g.name);
    setEditGenreGuidance(g.guidance);
    setEditGenreKeywords(g.keywords.join(', '));
    setGenreError('');
  }, [genres]);

  useEffect(() => {
    loadGenres();
  }, []);

  useEffect(() => {
    if (msgRef.current) {
      msgRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [progress?.message]);

  return (
    <div className="min-h-screen py-6 px-4">
      {authLoading ? (
        <div className="flex items-center justify-center h-64">
          <p className="text-slate-400">加载中...</p>
        </div>
      ) : !loggedIn ? (
        /* Login / Register */
        <div className="max-w-sm mx-auto mt-16">
          <header className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-800 tracking-wide">
              AI 剧本创作助手
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              登录后开始使用
            </p>
          </header>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex mb-5 border-b border-slate-200">
              <button
                onClick={() => { setAuthMode('login'); setAuthError(''); }}
                className={`flex-1 pb-2.5 text-sm font-medium border-b-2 transition-colors ${
                  authMode === 'login'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                登录
              </button>
              <button
                onClick={() => { setAuthMode('register'); setAuthError(''); }}
                className={`flex-1 pb-2.5 text-sm font-medium border-b-2 transition-colors ${
                  authMode === 'register'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                注册
              </button>
            </div>

            {authError && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                {authError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">用户名</label>
                <input
                  value={authUsername}
                  onChange={(e) => setAuthUsername(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入用户名"
                  className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">密码</label>
                <input
                  type="password"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入密码"
                  className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <button
                onClick={authMode === 'login' ? handleLogin : handleRegister}
                className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg
                           hover:bg-indigo-700 transition-colors"
              >
                {authMode === 'login' ? '登录' : '注册'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Main App */
      <>
      <header className="text-center mb-8">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <div />
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-wide">
              AI 剧本创作助手
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              将小说章节一键转换为标准剧本格式
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadConversions(); }}
              className="text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
            >
              历史
            </button>
            <span className="text-sm text-slate-500">{username}</span>
            <button
              onClick={handleLogout}
              className="text-xs text-slate-400 hover:text-red-500 transition-colors"
            >
              退出
            </button>
          </div>
        </div>
      </header>

      {/* History Panel */}
      {showHistory && (
        <section className="max-w-4xl mx-auto mb-6 bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-700">历史记录</h2>
            <button
              onClick={() => setShowHistory(false)}
              className="text-slate-400 hover:text-slate-600 text-xl leading-none"
            >
              ✕
            </button>
          </div>
          {conversionsLoading ? (
            <p className="text-sm text-slate-400 text-center py-4">加载中...</p>
          ) : conversions.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-4">暂无历史记录</p>
          ) : (
            <div className="max-h-64 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">标题</th>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">类型</th>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">状态</th>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">时间</th>
                    <th className="text-center px-3 py-2 text-slate-500 font-medium w-28">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {conversions.map((c) => (
                    <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 text-slate-700 max-w-[200px] truncate">
                        {c.title || '未命名'}
                      </td>
                      <td className="px-3 py-2 text-slate-500">{c.genre}</td>
                      <td className="px-3 py-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          c.status === 'completed' ? 'bg-emerald-50 text-emerald-600' :
                          c.status === 'failed' ? 'bg-red-50 text-red-500' :
                          'bg-amber-50 text-amber-600'
                        }`}>
                          {c.status === 'completed' ? '完成' :
                           c.status === 'failed' ? '失败' :
                           c.status === 'processing' ? '处理中' : c.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-400 text-xs">
                        {c.updated_at ? new Date(c.updated_at).toLocaleString('zh-CN') : '-'}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {c.status === 'completed' && (
                          <button
                            onClick={() => viewConversion(c.id)}
                            className="text-indigo-500 hover:text-indigo-700 text-xs mr-2"
                          >
                            查看
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteConversion(c.id)}
                          className="text-red-400 hover:text-red-600 text-xs"
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <main className="max-w-4xl mx-auto space-y-6">
        {/* Input Section */}
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-slate-700">输入小说文本</h2>
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-500">小说类型：</label>
              <select
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                disabled={phase === 'converting'}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white
                           focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
              >
                {genres.map((g) => (
                  <option key={g.name} value={g.name}>{g.name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => {
                  setGenreError('');
                  setEditGenreIndex(null);
                  setEditGenreName('');
                  setEditGenreGuidance('');
                  setEditGenreKeywords('');
                  setShowGenreModal(true);
                }}
                disabled={phase === 'converting'}
                className="px-2 py-1.5 text-xs text-indigo-600 border border-indigo-200 rounded-lg
                           hover:bg-indigo-50 disabled:opacity-50 transition-colors"
              >
                管理类型
              </button>
            </div>
          </div>
          <div className="mb-3">
            <label className="text-sm text-slate-500 mr-2">剧本标题：</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入剧本标题（留空则使用第一章标题）"
              disabled={phase === 'converting'}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm w-72
                         focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
            />
          </div>
          <textarea
            className="w-full h-64 p-4 border border-slate-300 rounded-lg resize-y text-sm leading-relaxed
                       focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
                       placeholder:text-slate-400 disabled:opacity-50"
            placeholder={"请粘贴小说文本（至少3个章节，通过\"第X章\"标记章节）..."}
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={phase === 'converting'}
          />
          <div className="flex items-center justify-between mt-3">
            <span className={`text-sm font-medium ${chapterCount >= 3 ? 'text-emerald-600' : 'text-red-500'}`}>
              检测到 {chapterCount} 个章节{chapterCount < 3 ? '（至少需要3个章节）' : ''}
            </span>
            <button
              onClick={handleConvert}
              disabled={!canConvert || phase === 'converting'}
              className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg
                         hover:bg-indigo-700 active:bg-indigo-800
                         disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed
                         transition-colors"
            >
              开始转换
            </button>
          </div>
        </section>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <span className="text-red-500 shrink-0 mt-0.5">⚠</span>
            <div className="flex-1">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-600 shrink-0"
            >
              ✕
            </button>
          </div>
        )}

        {/* Progress Section */}
        {phase === 'converting' && progress && (
          <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-700 mb-4">转换进度</h2>

            <div className="flex items-center justify-between mb-2">
              {STEP_LABELS.map((label, i) => {
                const stepNum = i + 1;
                const isCompleted = stepNum < progress.step;
                const isActive = stepNum === progress.step;
                return (
                  <div key={i} className="flex flex-col items-center flex-1">
                    <div className="flex items-center w-full">
                      {i > 0 && (
                        <div
                          className={`flex-1 h-0.5 -mr-2 -ml-2 ${
                            isCompleted || isActive ? 'bg-indigo-500' : 'bg-slate-200'
                          }`}
                        />
                      )}
                      <div
                        className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                          ${isCompleted ? 'bg-indigo-600 text-white' : ''}
                          ${isActive ? 'bg-indigo-500 text-white ring-4 ring-indigo-100' : ''}
                          ${!isCompleted && !isActive ? 'bg-slate-100 text-slate-400' : ''}
                        `}
                      >
                        {isCompleted ? '✓' : stepNum}
                      </div>
                      {i < STEP_LABELS.length - 1 && (
                        <div
                          className={`flex-1 h-0.5 -mr-2 -ml-2 ${
                            isCompleted ? 'bg-indigo-500' : 'bg-slate-200'
                          }`}
                        />
                      )}
                    </div>
                    <span
                      className={`text-xs mt-1.5 text-center ${
                        isActive ? 'text-indigo-600 font-semibold' : ''
                      } ${isCompleted ? 'text-indigo-500' : ''} ${
                        !isCompleted && !isActive ? 'text-slate-400' : ''
                      }`}
                    >
                      {label}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="mt-5 text-center" ref={msgRef}>
              <p className="text-sm text-slate-600">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse-dot mr-2 align-middle" />
                {progress.message}
              </p>
            </div>

            <div className="mt-4 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${(progress.step / progress.total) * 100}%` }}
              />
            </div>
          </section>
        )}

        {/* Result Section */}
        {phase === 'done' && result && (
          <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-700">转换结果</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReset}
                  className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  重新开始
                </button>
                <button
                  onClick={() => downloadYaml(result.yaml)}
                  className="px-4 py-1.5 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors"
                >
                  下载 YAML
                </button>
              </div>
            </div>

            {/* Meta info */}
            <div className="flex flex-wrap gap-3 mb-4">
              <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                类型: {result.meta.genre || '叙事'}
              </span>
              <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                {result.meta.title}
              </span>
              <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                章节: {result.meta.chapter_count}
              </span>
              <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                场景: {result.meta.scene_count}
              </span>
              <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
                角色: {result.meta.character_count}
              </span>
            </div>

            {/* Validation info */}
            {result.meta.validation && (
              <div className={`mb-4 p-3 rounded-lg border text-sm ${
                result.meta.validation.count >= 2
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : 'bg-amber-50 border-amber-200 text-amber-700'
              }`}>
                <div className="flex items-center flex-wrap gap-x-3 gap-y-1">
                  <span className="font-semibold">主角验证</span>
                  <span>主角: {result.meta.validation.main_character || '未识别'}</span>
                  <span>评分: {result.meta.validation.count}/2</span>
                  <span>{result.meta.validation.status}</span>
                  {result.meta.validation.retried && <span className="text-xs">(已重试)</span>}
                </div>

                {result.meta.validation.count < 2 && !result.meta.validation.retried && !hintsSkipped && (
                  <div className="mt-3 pt-3 border-t border-amber-200">
                    <p className="text-xs mb-2">
                      主角验证未达标，是否添加补充信息帮助 AI 重新生成剧本？
                    </p>
                    <textarea
                      value={hints}
                      onChange={(e) => setHints(e.target.value)}
                      placeholder="例如：主角是林晓，是一名女程序员；故事主线是悬疑调查；场景应更偏重内心独白..."
                      rows={2}
                      className="w-full px-3 py-1.5 border border-amber-300 rounded-lg text-xs
                                 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-y"
                      disabled={regenerating}
                    />
                    {hintsError && (
                      <p className="text-xs text-red-500 mt-1">{hintsError}</p>
                    )}
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={handleRegenerate}
                        disabled={regenerating || !hints.trim()}
                        className="px-3 py-1 text-xs bg-amber-600 text-white rounded-md
                                   hover:bg-amber-700 disabled:opacity-50 transition-colors"
                      >
                        {regenerating ? '生成中...' : '提交信息重新生成'}
                      </button>
                      <button
                        onClick={handleSkipRevalidate}
                        disabled={regenerating}
                        className="px-3 py-1 text-xs text-amber-600 border border-amber-300 rounded-md
                                   hover:bg-amber-50 disabled:opacity-50 transition-colors"
                      >
                        跳过，直接使用当前结果
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {result.meta.schema_validation && result.meta.schema_validation.warnings.length > 0 && (
              <div className="mb-4 p-3 rounded-lg border text-sm bg-amber-50 border-amber-200 text-amber-700">
                <span className="font-semibold">Schema 校验警告</span>
                <ul className="mt-1 list-disc list-inside">
                  {result.meta.schema_validation.warnings.slice(0, 5).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                  {result.meta.schema_validation.warnings.length > 5 && (
                    <li>...等 {result.meta.schema_validation.warnings.length} 条</li>
                  )}
                </ul>
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-slate-200 mb-3">
              <button
                onClick={() => setActiveTab('yaml')}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === 'yaml'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                YAML 预览
              </button>
              <button
                onClick={() => setActiveTab('structured')}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === 'structured'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                结构化视图
              </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'yaml' && !editing && (
              <div className="relative">
                <div className="absolute top-2 right-2 flex gap-2 z-10">
                  <button
                    onClick={handleStartEdit}
                    className="px-3 py-1 text-xs bg-indigo-600 text-white rounded-md
                               hover:bg-indigo-700 transition-colors"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => {
                      copyToClipboard(result.yaml);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="px-3 py-1 text-xs bg-slate-700 text-white rounded-md
                               hover:bg-slate-800 transition-colors"
                  >
                    {copied ? '已复制!' : '复制'}
                  </button>
                </div>
                <pre className="bg-slate-900 rounded-lg p-4 max-h-[500px] overflow-auto text-xs leading-relaxed font-mono">
                  {highlightYaml(result.yaml)}
                </pre>
              </div>
            )}

            {activeTab === 'yaml' && editing && (
              <div className="space-y-3">
                {editError && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                    {editError}
                  </div>
                )}
                <textarea
                  value={editedYaml}
                  onChange={(e) => setEditedYaml(e.target.value)}
                  className="w-full h-[500px] p-4 bg-slate-900 text-emerald-400 font-mono text-xs leading-relaxed
                             rounded-lg border border-slate-600 resize-y
                             focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  spellCheck={false}
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveEdit}
                    disabled={editSaving}
                    className="px-4 py-1.5 bg-emerald-600 text-white text-sm font-medium rounded-lg
                               hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                  >
                    {editSaving ? '保存中...' : '保存'}
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    disabled={editSaving}
                    className="px-4 py-1.5 text-sm text-slate-500 border border-slate-300 rounded-lg
                               hover:bg-slate-50 disabled:opacity-50 transition-colors"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'structured' && (
              <StructuredView yaml={result.yaml} />
            )}
          </section>
        )}

        {/* Genre Management Modal */}
        {showGenreModal && (
          <section className="bg-white rounded-xl shadow-lg border border-slate-300 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-700">管理小说类型</h2>
              <button
                onClick={() => setShowGenreModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl leading-none"
              >
                ✕
              </button>
            </div>

            {genreError && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                {genreError}
              </div>
            )}

            {/* Existing genres table */}
            <div className="mb-4 max-h-48 overflow-auto border border-slate-200 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">名称</th>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">描述</th>
                    <th className="text-left px-3 py-2 text-slate-500 font-medium">关键词</th>
                    <th className="text-center px-3 py-2 text-slate-500 font-medium w-24">来源</th>
                    <th className="text-center px-3 py-2 text-slate-500 font-medium w-20">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {genres.map((g, i) => (
                    <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-700">{g.name}</td>
                      <td className="px-3 py-2 text-slate-500 max-w-[160px] truncate">{g.guidance}</td>
                      <td className="px-3 py-2 text-slate-400 text-xs">{g.keywords?.join(', ') || '-'}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${g.readonly ? 'bg-slate-100 text-slate-400' : 'bg-indigo-50 text-indigo-500'}`}>
                          {g.readonly ? '系统' : '自定义'}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        {!g.readonly ? (
                          <>
                            <button onClick={() => handleEditGenre(i)} className="text-indigo-500 hover:text-indigo-700 text-xs mr-1">编辑</button>
                            <button onClick={() => handleDeleteGenre(i)} className="text-red-400 hover:text-red-600 text-xs">删除</button>
                          </>
                        ) : (
                          <span className="text-slate-300 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Add / Edit form */}
            <div className="border-t border-slate-200 pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-600">
                  {editGenreIndex !== null ? `编辑: ${editGenreName}` : '新增类型'}
                </h3>
                <span className="text-xs text-slate-400">
                  自定义: {genres.filter((g) => !g.readonly).length}/10
                </span>
              </div>
              <div>
                <label className="text-xs text-slate-500">名称</label>
                <input
                  value={editGenreName}
                  onChange={(e) => setEditGenreName(e.target.value)}
                  placeholder="如: 悬疑"
                  className="w-full mt-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">AI 指引描述</label>
                <textarea
                  value={editGenreGuidance}
                  onChange={(e) => setEditGenreGuidance(e.target.value)}
                  placeholder="告诉 AI 这类小说的特点和分析重点..."
                  rows={2}
                  className="w-full mt-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-y"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">主角关键词</label>
                <input
                  value={editGenreKeywords}
                  onChange={(e) => setEditGenreKeywords(e.target.value)}
                  placeholder="用逗号分隔, 如: 侠, 掌门, 江湖"
                  className="w-full mt-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveGenre}
                  disabled={editGenreIndex === null && genres.filter((g) => !g.readonly).length >= 10}
                  className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg
                             hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed transition-colors"
                >
                  {editGenreIndex !== null ? '保存修改' : '添加类型'}
                </button>
                {editGenreIndex !== null && (
                  <button
                    onClick={() => {
                      setEditGenreIndex(null);
                      setEditGenreName('');
                      setEditGenreGuidance('');
                      setEditGenreKeywords('');
                      setGenreError('');
                    }}
                    className="px-4 py-1.5 text-sm text-slate-500 border border-slate-300 rounded-lg
                               hover:bg-slate-50 transition-colors"
                  >
                    取消编辑
                  </button>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
      </>
      )}
    </div>
  );
}

function StructuredView({ yaml }: { yaml: string }) {
  const data = parseYamlToStructure(yaml);

  if (data.length === 0) {
    return <p className="text-slate-400 text-sm py-8 text-center">暂无可解析的结构化数据</p>;
  }

  return (
    <div className="space-y-4 max-h-[600px] overflow-auto pr-1">
      {data.map((chapter, ci) => (
        <details key={ci} className="group" open>
          <summary className="cursor-pointer text-base font-semibold text-indigo-700 bg-indigo-50 px-3 py-2 rounded-lg hover:bg-indigo-100 transition-colors">
            {chapter.name || `第${ci + 1}章`}
          </summary>
          <div className="mt-2 space-y-3 pl-2">
            {chapter.scenes.map((scene, si) => (
              <div key={si} className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-bold text-slate-800 mb-2">
                  🎬 {scene.heading || `场景 ${si + 1}`}
                </h3>

                {scene.actions.length > 0 && (
                  <div className="mb-3 space-y-1">
                    {scene.actions.map((a, ai) => (
                      <p key={ai} className="text-sm text-slate-600 pl-2 border-l-2 border-slate-300">
                        {a}
                      </p>
                    ))}
                  </div>
                )}

                {scene.dialogues.length > 0 && (
                  <div className="space-y-2">
                    {scene.dialogues.map((d, di) => (
                      <div
                        key={di}
                        className="bg-white border border-indigo-100 rounded-md p-3 shadow-sm"
                      >
                        <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                          {d.character}
                        </span>
                        <p className="text-sm text-slate-700 mt-1.5 italic">
                          &ldquo;{d.line}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {scene.actions.length === 0 && scene.dialogues.length === 0 && (
                  <p className="text-xs text-slate-400 italic">暂无内容</p>
                )}
              </div>
            ))}
          </div>
        </details>
      ))}
    </div>
=======
import { useState, useEffect } from 'react';
import { fetchCurrentUser, logout } from './api';
import LoginPage from './components/LoginPage';
import HomePage from './components/HomePage';
import ProjectPage from './components/ProjectPage';

type Page = 'home' | 'project';

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [page, setPage] = useState<Page>('home');
  const [projectId, setProjectId] = useState('');
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    fetchCurrentUser().then(user => {
      if (user) {
        setLoggedIn(true);
        setUsername(user.username);
      }
      setChecking(false);
    });
  }, []);

  const handleLogin = (name: string) => {
    setUsername(name);
    setLoggedIn(true);
    setPage('home');
  };

  const handleLogout = () => {
    logout();
    setLoggedIn(false);
    setUsername('');
    setPage('home');
    setProjectId('');
  };

  const handleOpenProject = (id: string) => {
    setProjectId(id);
    setPage('project');
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-sm text-slate-400">加载中...</div>
      </div>
    );
  }

  if (!loggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  if (page === 'project' && projectId) {
    return <ProjectPage projectId={projectId} onBack={() => setPage('home')} />;
  }

  return (
    <HomePage
      username={username}
      onLogout={handleLogout}
      onOpenProject={handleOpenProject}
    />
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
  );
}
