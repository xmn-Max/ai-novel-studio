import { useState, useEffect, useRef } from 'react';

const TARGET_OPTIONS = [
  { value: 'script', label: '剧本', desc: '重新生成剧本场景和对白' },
  { value: 'plot', label: '剧情', desc: '重新分析剧情主线和结构' },
  { value: 'world', label: '世界观', desc: '重新分析世界观设定' },
  { value: 'characters', label: '角色', desc: '重新提取和调整角色' },
] as const;

interface Props {
  onRegenerate: (feedback: string) => Promise<void>;
  disabled?: boolean;
  prefillText?: string;
  visible: boolean;
  onVisibilityChange: (visible: boolean) => void;
  target?: string;
}

export default function FeedbackPanel({ onRegenerate, disabled, prefillText, visible, onVisibilityChange, target = 'script' }: Props) {
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [selectedTarget, setSelectedTarget] = useState(target);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefillText) {
      setFeedback(prefillText);
    }
  }, [prefillText]);

  useEffect(() => {
    setSelectedTarget(target);
  }, [target]);

  useEffect(() => {
    if (visible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [visible]);

  if (!visible) return null;

  const handleSubmit = async () => {
    const trimmed = feedback.trim();
    if (!trimmed) return;
    setLoading(true);
    try {
      await onRegenerate(trimmed);
      setHistory(prev => [...prev, `[${TARGET_OPTIONS.find(t => t.value === selectedTarget)?.label || selectedTarget}] ${trimmed}`]);
      setFeedback('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-slate-700">AI 重新询问</h3>
        <button onClick={() => onVisibilityChange(false)} className="text-xs text-slate-400 hover:text-slate-600">收起</button>
      </div>
      <p className="text-xs text-slate-500 mb-3">
        选择目标并描述你希望改进的地方，AI 将根据你的意见重新生成。
      </p>
      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
        {/* Target selector */}
        <div className="flex gap-2 flex-wrap">
          {TARGET_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setSelectedTarget(opt.value);
                const prefillMap: Record<string, string> = {
                  script: '请改进剧本：',
                  plot: '请改进剧情分析：',
                  world: '请改进世界观分析：',
                  characters: '请改进角色设定：',
                };
                setFeedback(prefillMap[opt.value] || '');
              }}
              disabled={disabled || loading}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                selectedTarget === opt.value
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              } disabled:opacity-50`}
              title={opt.desc}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <textarea
          ref={inputRef}
          className="w-full h-24 px-4 py-3 border border-slate-300 rounded-lg text-sm leading-relaxed focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none resize-y"
          value={feedback}
          onChange={e => setFeedback(e.target.value)}
          placeholder="例如：让主角的台词更有气势、增加一场打斗戏、把结局改成开放式..."
          disabled={disabled || loading}
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              handleSubmit();
            }
          }}
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">Ctrl+Enter 发送</span>
          <button
            onClick={handleSubmit}
            disabled={disabled || loading || !feedback.trim()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                AI 重新生成中...
              </span>
            ) : '提交意见'}
          </button>
        </div>
      </div>
      {history.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
            历史反馈 ({history.length})
          </summary>
          <ul className="mt-2 space-y-1">
            {history.map((h, i) => (
              <li key={i} className="text-xs text-slate-500 bg-slate-50 rounded px-3 py-1.5">{h}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
