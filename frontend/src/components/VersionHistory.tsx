import { useState, useEffect } from 'react';
import { listVersions, getVersion, restoreVersion, VersionItem, VersionSnapshot, saveVersion, deepReview } from '../api';

interface Props {
  projectId: string;
  visible: boolean;
  onClose: () => void;
  onRestored: () => void;
  feedbackText?: string;
}

export default function VersionHistory({ projectId, visible, onClose, onRestored, feedbackText }: Props) {
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [diffData, setDiffData] = useState<{ a: VersionSnapshot | null; b: VersionSnapshot | null }>({ a: null, b: null });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [showDeepReview, setShowDeepReview] = useState(false);
  const [deepFeedback, setDeepFeedback] = useState('');
  const [deepLoading, setDeepLoading] = useState(false);

  const load = async () => {
    try { setVersions(await listVersions(projectId)); } catch { /* ignore */ }
  };

  useEffect(() => { if (visible) load(); }, [visible, projectId]);

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
    setDiffData({ a: null, b: null });
    setShowDeepReview(false);
    setDeepFeedback('');
  };

  const handleCompare = async () => {
    if (selected.length !== 2) return;
    setLoading(true);
    setShowDeepReview(false);
    setDeepFeedback('');
    try {
      const [a, b] = await Promise.all([
        getVersion(projectId, selected[0]),
        getVersion(projectId, selected[1]),
      ]);
      setDiffData({ a, b });

      const snapA = a.snapshot as Record<string, unknown>;
      const snapB = b.snapshot as Record<string, unknown>;
      const yamlA = (typeof snapA?.['yaml_content'] === 'string' ? snapA['yaml_content'] : '') as string;
      const yamlB = (typeof snapB?.['yaml_content'] === 'string' ? snapB['yaml_content'] : '') as string;
      const linesA = yamlA ? yamlA.split('\n').length : 0;
      const linesB = yamlB ? yamlB.split('\n').length : 0;
      if (Math.abs(linesA - linesB) > 30) {
        setShowDeepReview(true);
      }
    } catch { setMsg('获取版本失败'); }
    finally { setLoading(false); }
  };

  const handleDeepReview = async () => {
    if (!deepFeedback.trim() || selected.length !== 2) return;
    setDeepLoading(true);
    try {
      const result = await deepReview(projectId, deepFeedback.trim(), selected[0], selected[1]);
      setMsg(`深度审阅完成: ${result.label}`);
      setTimeout(() => setMsg(''), 5000);
      setShowDeepReview(false);
      setDeepFeedback('');
      onRestored();
      await load();
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : '深度审阅失败');
      setTimeout(() => setMsg(''), 5000);
    }
    setDeepLoading(false);
  };

  const handleRestore = async (versionId: string) => {
    if (!confirm('确认恢复此版本？当前数据将被替换。')) return;
    try {
      await restoreVersion(projectId, versionId);
      setMsg('版本已恢复');
      setTimeout(() => setMsg(''), 3000);
      onRestored();
    } catch { setMsg('恢复失败'); }
  };

  const handleSaveCurrent = async () => {
    try {
      const result = await saveVersion(projectId, feedbackText || '手动保存');
      setMsg(`已保存: ${result.label}`);
      setTimeout(() => setMsg(''), 3000);
      await load();
    } catch { setMsg('保存失败'); }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 bg-black/30">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 w-full max-w-5xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-900">版本历史</h3>
          <div className="flex items-center gap-2">
            {msg && <span className="text-xs text-emerald-600">{msg}</span>}
            <button onClick={handleSaveCurrent} className="px-3 py-1.5 text-xs font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50">+ 保存当前版本</button>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg">&times;</button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="w-64 border-r border-slate-200 overflow-auto p-3 space-y-1 shrink-0">
            {versions.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-8">暂无版本记录</p>
            )}
            {versions.map(v => (
              <div
                key={v.version_id}
                className={`p-2 rounded-lg cursor-pointer transition-colors border ${
                  selected.includes(v.version_id)
                    ? 'border-indigo-400 bg-indigo-50'
                    : 'border-transparent hover:bg-slate-50'
                }`}
                onClick={() => toggleSelect(v.version_id)}
              >
                <div className="text-xs font-medium text-slate-700">{v.label}</div>
                {v.feedback && (
                  <div className="text-xs text-slate-400 mt-0.5 truncate">{v.feedback.slice(0, 40)}</div>
                )}
                <button
                  onClick={e => { e.stopPropagation(); handleRestore(v.version_id); }}
                  className="text-xs text-indigo-500 hover:text-indigo-700 mt-1"
                >
                  恢复此版本
                </button>
              </div>
            ))}
          </div>

          <div className="flex-1 overflow-auto p-4">
            {!diffData.a ? (
              <div className="text-center text-sm text-slate-400 mt-20">
                {selected.length < 2
                  ? `请选择两个版本进行对比（已选 ${selected.length}/2）`
                  : (
                    <button onClick={handleCompare} disabled={loading}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50">
                      {loading ? '加载中...' : '对比选中的两个版本'}
                    </button>
                  )}
              </div>
            ) : (
              <>
                <VersionDiff a={diffData.a!} b={diffData.b!} />

                {showDeepReview && (
                  <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-amber-800">
                        剧本行数差异超过 30 行，是否需要 AI 深度审阅并重新生成？
                      </h4>
                      <button
                        onClick={() => setShowDeepReview(false)}
                        className="text-amber-500 hover:text-amber-700 text-sm"
                      >
                        放弃生成
                      </button>
                    </div>
                    <p className="text-xs text-amber-600 mb-3">
                      AI 将审视您的补充意见和两个版本的差异，重新阅读原文，综合生成新剧本。新剧本会自动保存为一个新版本。
                    </p>
                    <textarea
                      value={deepFeedback}
                      onChange={(e) => setDeepFeedback(e.target.value)}
                      placeholder="请输入补充意见，例如：B版本的场景划分更合理但A版本的对白更自然，请综合两者优点..."
                      rows={3}
                      className="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm
                                 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-y"
                      disabled={deepLoading}
                    />
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={handleDeepReview}
                        disabled={deepLoading || !deepFeedback.trim()}
                        className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg
                                   hover:bg-amber-700 disabled:opacity-50 transition-colors"
                      >
                        {deepLoading ? '正在审阅并生成...' : 'AI 深度审阅并生成新剧本'}
                      </button>
                      <button
                        onClick={() => { setShowDeepReview(false); setDeepFeedback(''); }}
                        disabled={deepLoading}
                        className="px-4 py-2 text-sm text-slate-500 border border-slate-300 rounded-lg
                                   hover:bg-slate-50 disabled:opacity-50 transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function VersionDiff({ a, b }: { a: VersionSnapshot; b: VersionSnapshot }) {
  const snapA = a.snapshot as Record<string, unknown>;
  const snapB = b.snapshot as Record<string, unknown>;

  const yamlA = (typeof snapA?.['yaml_content'] === 'string' ? snapA['yaml_content'] : '') as string;
  const yamlB = (typeof snapB?.['yaml_content'] === 'string' ? snapB['yaml_content'] : '') as string;

  const [showYamlPreview, setShowYamlPreview] = useState(false);

  const sections: Array<{ key: string; label: string; render: (val: unknown) => string }> = [
    {
      key: 'characters', label: '角色分析',
      render: (val) => (val as Array<Record<string, unknown>>)?.map(c => `${c.name}(${c.role})`).join(', ') || '—',
    },
    {
      key: 'plot', label: '剧情分析',
      render: (val) => {
        const p = val as Record<string, unknown> || {};
        return `主线:${p.main_line || '—'}, 主题:${p.theme || '—'}, 冲突:${p.conflict || '—'}`;
      },
    },
    {
      key: 'events', label: '关键事件',
      render: (val) => (val as Array<Record<string, unknown>>)?.map(e => `${e.id}:${e.name}`).join('; ') || '—',
    },
    {
      key: 'scene_plan', label: '场景规划',
      render: (val) => `${(val as Array<unknown>)?.length || 0} 个场景`,
    },
    {
      key: 'script_scenes', label: '剧本场景',
      render: (val) => `${(val as Array<unknown>)?.length || 0} 个场景`,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-stretch gap-4 text-xs">
        <div className="flex-1 p-2 bg-slate-50 rounded text-slate-500 font-medium">版本 A: {a.label}</div>
        <div className="flex-1 p-2 bg-slate-50 rounded text-slate-500 font-medium">版本 B: {b.label}</div>
      </div>
      {sections.map(({ key, label, render }) => {
        const valA = snapA[key];
        const valB = snapB[key];
        const strA = render(valA);
        const strB = render(valB);
        const isDiff = strA !== strB;

        return (
          <div key={key} className={`rounded-lg border p-3 ${isDiff ? 'border-amber-300 bg-amber-50/30' : 'border-slate-200'}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-slate-700">{label}</span>
              {isDiff && <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">有差异</span>}
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className={`p-2 rounded ${isDiff ? 'bg-red-50 text-red-700 line-through' : 'bg-slate-50 text-slate-600'}`}>
                {strA}
              </div>
              <div className={`p-2 rounded ${isDiff ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-50 text-slate-600'}`}>
                {strB}
              </div>
            </div>
          </div>
        );
      })}

      {/* YAML section with preview toggle */}
      <div className="rounded-lg border border-slate-200 p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700">YAML 剧本</span>
            {(() => {
              const linesA = yamlA ? yamlA.split('\n').length : 0;
              const linesB = yamlB ? yamlB.split('\n').length : 0;
              if (linesA !== linesB) {
                return <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">有差异</span>;
              }
              return null;
            })()}
          </div>
          <button
            onClick={() => setShowYamlPreview(!showYamlPreview)}
            className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
          >
            {showYamlPreview ? '收起预览' : '展开 YAML 预览'}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-2 rounded bg-slate-50 text-slate-600">
            {yamlA ? `${yamlA.split('\n').length} 行, ${(yamlA.length / 1024).toFixed(1)} KB` : '—'}
          </div>
          <div className="p-2 rounded bg-slate-50 text-slate-600">
            {yamlB ? `${yamlB.split('\n').length} 行, ${(yamlB.length / 1024).toFixed(1)} KB` : '—'}
          </div>
        </div>

        {showYamlPreview && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-slate-500 mb-1">版本 A YAML</div>
              <pre className="bg-slate-900 text-xs leading-relaxed p-3 rounded-lg max-h-[500px] overflow-auto font-mono">
                {yamlA ? highlightYaml(yamlA) : <span className="text-slate-500">暂无内容</span>}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">版本 B YAML</div>
              <pre className="bg-slate-900 text-xs leading-relaxed p-3 rounded-lg max-h-[500px] overflow-auto font-mono">
                {yamlB ? highlightYaml(yamlB) : <span className="text-slate-500">暂无内容</span>}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function highlightYaml(yaml: string) {
  return yaml.split('\n').map((line, i) => {
    const trimmed = line.trimStart();
    let color = 'text-slate-400';
    if (trimmed.startsWith('#')) {
      color = 'text-slate-500 italic';
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('  - ')) {
      color = 'text-indigo-400';
    } else if (trimmed.includes(':')) {
      const keyPart = trimmed.split(':')[0];
      if (keyPart.match(/^[\w\u4e00-\u9fff]+$/)) {
        color = 'text-emerald-400';
      }
    }
    return (
      <div key={i} className="flex">
        <span className="select-none text-slate-600 w-8 text-right pr-2 shrink-0 text-[10px] leading-5">
          {i + 1}
        </span>
        <span className={`${color} whitespace-pre-wrap break-all leading-5`}>{line || ' '}</span>
      </div>
    );
  });
}
