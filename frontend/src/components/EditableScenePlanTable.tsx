import { useState } from 'react';
import { updateScenePlanItem } from '../api';

interface ScenePlanItem {
  id: string;
  purpose: string;
  location: string;
  time_of_day: string;
  conflict_level: string;
  event_refs: string[];
}

interface Props {
  items: ScenePlanItem[];
  projectId: string;
  onUpdate: () => void;
}

interface EditingCell {
  planId: string;
  field: string;
}

const COLUMNS = [
  { key: 'id', label: 'ID', width: 'w-16' },
  { key: 'purpose', label: '目的', width: '' },
  { key: 'location', label: '地点', width: 'w-24' },
  { key: 'time_of_day', label: '时间', width: 'w-16' },
  { key: 'conflict_level', label: '冲突', width: 'w-16' },
  { key: 'event_refs', label: '关联事件', width: 'w-28' },
] as const;

export default function EditableScenePlanTable({ items, projectId, onUpdate }: Props) {
  const [editing, setEditing] = useState<EditingCell | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saveMsg, setSaveMsg] = useState('');

  if (!items.length) return null;

  const showMsg = (msg: string) => {
    setSaveMsg(msg);
    setTimeout(() => setSaveMsg(''), 2500);
  };

  const startEdit = (planId: string, field: string, currentValue: string) => {
    setEditing({ planId, field });
    setEditValue(currentValue);
  };

  const saveEdit = async () => {
    if (!editing) return;
    const { planId, field } = editing;
    const value = editValue.trim();
    try {
      await updateScenePlanItem(projectId, planId, field, value);
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

  const getConflictBadge = (level: string) => {
    const base = 'text-xs px-1.5 py-0.5 rounded';
    if (level === '高' || level === '极高') return `${base} bg-red-100 text-red-700`;
    if (level === '中') return `${base} bg-amber-100 text-amber-700`;
    return `${base} bg-slate-100 text-slate-600`;
  };

  const getCellValue = (item: ScenePlanItem, field: string): string => {
    if (field === 'event_refs') return (item.event_refs || []).join(', ');
    if (field === 'id') return item.id;
    if (field === 'purpose') return item.purpose;
    if (field === 'location') return item.location;
    if (field === 'time_of_day') return item.time_of_day;
    if (field === 'conflict_level') return item.conflict_level;
    return '';
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-slate-700">场景规划</h3>
          <span className="text-xs text-slate-400">双击单元格编辑</span>
        </div>
        {saveMsg && <span className="text-xs text-emerald-600 animate-pulse">{saveMsg}</span>}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {COLUMNS.map(col => (
                <th key={col.key} className={`px-3 py-2 text-left text-xs font-medium text-slate-500 ${col.width}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(sp => (
              <tr key={sp.id} className="border-b border-slate-100 last:border-0 group">
                {COLUMNS.map(col => {
                  const isEditing = editing?.planId === sp.id && editing?.field === col.key;
                  const value = getCellValue(sp, col.key);

                  if (col.key === 'id') {
                    return (
                      <td key={col.key} className="px-3 py-2.5 font-mono text-xs text-indigo-500">
                        {sp.id}
                      </td>
                    );
                  }

                  if (isEditing) {
                    return (
                      <td key={col.key} className="px-3 py-2.5">
                        <input
                          className="w-full px-2 py-0.5 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onBlur={saveEdit}
                          onKeyDown={handleKeyDown}
                          autoFocus
                        />
                      </td>
                    );
                  }

                  if (col.key === 'conflict_level') {
                    return (
                      <td
                        key={col.key}
                        className="px-3 py-2.5 cursor-pointer hover:bg-indigo-50/30 transition-colors relative"
                        onDoubleClick={() => startEdit(sp.id, col.key, value)}
                        title="双击编辑冲突等级"
                      >
                        <span className={getConflictBadge(value)}>{value || '—'}</span>
                        <span className="absolute right-1 top-1/2 -translate-y-1/2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px]">✎</span>
                      </td>
                    );
                  }

                  return (
                    <td
                      key={col.key}
                      className="px-3 py-2.5 cursor-pointer hover:bg-indigo-50/30 transition-colors relative text-slate-700"
                      onDoubleClick={() => startEdit(sp.id, col.key, value)}
                      title={`双击编辑${col.label}`}
                    >
                      {value || <span className="text-slate-300 italic">—</span>}
                      <span className="absolute right-1 top-1/2 -translate-y-1/2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px]">✎</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
