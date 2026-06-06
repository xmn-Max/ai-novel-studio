import { useState } from 'react';
import { updatePlotField } from '../api';

interface EventItem {
  id: string;
  name: string;
  description?: string;
  significance: string;
}

interface Props {
  plot: Record<string, unknown> | null;
  projectId: string;
  isComplete: boolean;
  onUpdate: () => void;
  onOpenFeedback: (prefill: string) => void;
}

interface EditingCell {
  field: string;
  eventIndex?: number;
  eventSubField?: 'name' | 'significance' | 'description';
}

const PLOT_FIELDS = [
  { key: 'main_line', label: '主线', span: 'full' },
  { key: 'theme', label: '主题', span: 'half' },
  { key: 'conflict', label: '冲突', span: 'half' },
  { key: 'climax', label: '高潮', span: 'half' },
  { key: 'ending', label: '结局', span: 'half' },
  { key: 'pacing', label: '节奏', span: 'half' },
] as const;

export default function EditablePlotSection({ plot, projectId, isComplete, onUpdate, onOpenFeedback }: Props) {
  const [editing, setEditing] = useState<EditingCell | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saveMsg, setSaveMsg] = useState('');

  if (!plot && !isComplete) return null;
  if (!plot) {
    return (
      <div className="text-center py-2">
        <button onClick={() => onOpenFeedback('请重新生成剧情分析')} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
          + 运行剧情分析
        </button>
      </div>
    );
  }

  const showMsg = (msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2500);
  };

  const startEdit = (field: string, currentValue: string, eventIndex?: number, eventSubField?: 'name' | 'significance' | 'description') => {
    setEditing({ field, eventIndex, eventSubField });
    setEditValue(currentValue);
  };

  const saveEdit = async () => {
    if (!editing) return;
    const { field, eventIndex, eventSubField } = editing;
    const value = editValue.trim();

    if (eventSubField && eventIndex !== undefined) {
      // Editing an event sub-field - update locally then sync events JSON
      try {
        const events = (plot.events as EventItem[]) || [];
        const ev = events[eventIndex];
        if (!ev) return;
        ev[eventSubField] = value;
        await updatePlotField(projectId, 'events', JSON.stringify(events));
        setEditing(null);
        showMsg('已保存');
        onUpdate();
      } catch (err: unknown) {
        showMsg(err instanceof Error ? err.message : '保存失败');
      }
      return;
    }

    try {
      await updatePlotField(projectId, field, value);
      setEditing(null);
      showMsg('已保存');
      onUpdate();
    } catch (err: unknown) {
      showMsg(err instanceof Error ? err.message : '保存失败');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
    else if (e.key === 'Escape') { setEditing(null); }
  };

  const getFieldValue = (field: string): string => {
    return String((plot as Record<string, unknown>)[field] ?? '');
  };

  const events = (plot.events ?? []) as EventItem[];

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-slate-700">剧情分析</h3>
          <span className="text-xs text-slate-400">双击字段编辑</span>
        </div>
        <div className="flex items-center gap-2">
          {saveMsg && <span className="text-xs text-emerald-600 animate-pulse">{saveMsg}</span>}
          <button onClick={() => onOpenFeedback('请改进剧情分析：')} className="text-xs text-indigo-600 hover:text-indigo-700">AI 重新分析</button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
        {PLOT_FIELDS.map(({ key, label }) => {
          const value = getFieldValue(key);
          const isEditing = editing?.field === key && editing.eventIndex === undefined;

          return (
            <div key={key} className={key === 'main_line' ? '' : 'inline-block w-1/2 pr-3 align-top'}>
              <span className="text-xs font-medium text-slate-500">{label}</span>
              {isEditing ? (
                <input
                  className="ml-2 px-2 py-0.5 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50 w-[calc(100%-3rem)]"
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                  onBlur={saveEdit}
                  onKeyDown={handleKeyDown}
                  autoFocus
                />
              ) : (
                <span
                  className="ml-2 text-sm text-slate-700 cursor-pointer hover:bg-indigo-50/30 rounded px-1 -mx-1 transition-colors relative group inline-block"
                  onDoubleClick={() => startEdit(key, value)}
                  title="双击编辑"
                >
                  {value || <span className="text-slate-300 italic">—</span>}
                  <span className="absolute -right-1 -top-0.5 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px]">✎</span>
                </span>
              )}
            </div>
          );
        })}

        {events.length > 0 && (
          <div className="pt-2 border-t border-slate-100">
            <span className="text-xs font-medium text-slate-500 mb-2 block">关键事件（双击编辑）</span>
            <div className="space-y-1.5">
              {events.map((ev, i) => {
                const isEditingName = editing?.field === 'events' && editing.eventIndex === i && editing.eventSubField === 'name';
                const isEditingSig = editing?.field === 'events' && editing.eventIndex === i && editing.eventSubField === 'significance';

                return (
                  <div key={ev.id || i} className="flex items-start gap-2 text-sm group">
                    <span className="text-xs font-mono text-indigo-500 min-w-fit pt-0.5">{ev.id}</span>

                    {isEditingName ? (
                      <input
                        className="px-2 py-0.5 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50 flex-1"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        onBlur={saveEdit}
                        onKeyDown={handleKeyDown}
                        autoFocus
                      />
                    ) : (
                      <span
                        className="font-medium text-slate-700 cursor-pointer hover:bg-indigo-50/30 rounded px-1 -mx-1 transition-colors min-w-0"
                        onDoubleClick={() => startEdit('events', ev.name, i, 'name')}
                        title="双击编辑事件名"
                      >
                        {ev.name}
                        <span className="inline-block text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] ml-0.5">✎</span>
                      </span>
                    )}

                    {isEditingSig ? (
                      <input
                        className="px-2 py-0.5 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50 w-24"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        onBlur={saveEdit}
                        onKeyDown={handleKeyDown}
                        autoFocus
                      />
                    ) : (
                      <span
                        className="text-xs text-slate-400 cursor-pointer hover:bg-indigo-50/30 rounded px-1 -mx-1 transition-colors"
                        onDoubleClick={() => startEdit('events', ev.significance, i, 'significance')}
                        title="双击编辑事件类型"
                      >
                        {ev.significance}
                        <span className="inline-block text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] ml-0.5">✎</span>
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
