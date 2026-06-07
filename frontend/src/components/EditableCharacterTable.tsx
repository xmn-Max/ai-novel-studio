import { useState } from 'react';
import { updateCharacter } from '../api';

interface CharacterItem {
  id: string;
  name: string;
  role: string;
  traits?: string[];
  description: string;
  gender?: string;
  age?: string;
}

interface EditingCell {
  charId: string;
  field: string;
}

interface Props {
  characters: CharacterItem[];
  projectId: string;
  onUpdate: () => void;
}

const ROLE_OPTIONS = [
  { value: 'protagonist', label: '主角' },
  { value: 'supporting', label: '配角' },
  { value: 'minor', label: '次要' },
] as const;

export default function EditableCharacterTable({ characters, projectId, onUpdate }: Props) {
  const [editing, setEditing] = useState<EditingCell | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saveMsg, setSaveMsg] = useState('');
  const [msgType, setMsgType] = useState<'success' | 'error'>('success');

  if (!characters.length) return null;

  const protagonistCount = characters.filter(c => c.role === 'protagonist').length;

  const showMsg = (msg: string, type: 'success' | 'error') => {
    setSaveMsg(msg);
    setMsgType(type);
    setTimeout(() => setSaveMsg(''), 3000);
  };

  const startEdit = (charId: string, field: string, currentValue: string) => {
    setEditing({ charId, field });
    setEditValue(currentValue);
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditValue('');
  };

  const saveEdit = async () => {
    if (!editing) return;
    const { charId, field } = editing;
    const value = editValue.trim();

    if (field === 'role') {
      if (value === 'protagonist') {
        if (!confirm('将此角色设为主角后，当前主角将自动降为配角。确认吗？')) {
          cancelEdit();
          return;
        }
      } else {
        // Not protagonist — check if this is the only protagonist being demoted
        const char = characters.find(c => c.id === charId);
        if (char?.role === 'protagonist' && protagonistCount <= 1) {
          showMsg('必须保留一个主角！已自动将第一个角色设为主角', 'error');
          return;
        }
      }
    }

    try {
      await updateCharacter(projectId, charId, field, value);
      setEditing(null);
      setEditValue('');
      showMsg('已保存', 'success');
      onUpdate();
    } catch (err: unknown) {
      showMsg(err instanceof Error ? err.message : '保存失败', 'error');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  const getRoleLabel = (role: string) => {
    const found = ROLE_OPTIONS.find(r => r.value === role);
    return found?.label || role;
  };

  const getRoleBadge = (role: string) => {
    const base = 'text-xs px-1.5 py-0.5 rounded';
    if (role === 'protagonist') return `${base} bg-indigo-100 text-indigo-700`;
    if (role === 'supporting') return `${base} bg-slate-100 text-slate-600`;
    return `${base} bg-slate-50 text-slate-500`;
  };

  const COLUMNS = [
    { key: 'name', label: '名称', width: 'w-24' },
    { key: 'role', label: '角色', width: 'w-20' },
    { key: 'traits', label: '性格特征', width: '' },
    { key: 'description', label: '描述', width: '' },
  ];

  const getCellValue = (c: CharacterItem, field: string): string => {
    if (field === 'traits') return (c.traits || []).join(', ');
    if (field === 'name') return c.name;
    if (field === 'role') return c.role;
    if (field === 'description') return c.description;
    return '';
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-slate-700">角色分析</h3>
          <span className="text-xs text-slate-400">双击单元格编辑 | 主角：{characters.filter(c => c.role === 'protagonist').map(c => c.name).join(', ') || '无'}</span>
        </div>
        {saveMsg && (
          <span className={`text-xs px-2 py-0.5 rounded animate-pulse ${msgType === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
            {saveMsg}
          </span>
        )}
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {COLUMNS.map(col => (
                <th key={col.key} className={`px-4 py-2 text-left text-xs font-medium text-slate-500 ${col.width}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {characters.map(c => (
              <tr key={c.id} className="border-b border-slate-100 last:border-0 group">
                {COLUMNS.map(col => {
                  const isEditing = editing?.charId === c.id && editing?.field === col.key;
                  const value = getCellValue(c, col.key);

                  if (isEditing) {
                    // Edit mode
                    if (col.key === 'role') {
                      return (
                        <td key={col.key} className={`px-4 py-2.5 ${col.width}`}>
                          <select
                            className="w-full px-2 py-1 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50"
                            value={editValue}
                            onChange={e => setEditValue(e.target.value)}
                            onBlur={saveEdit}
                            onKeyDown={handleKeyDown}
                            autoFocus
                          >
                            {ROLE_OPTIONS.map(r => (
                              <option key={r.value} value={r.value}>{r.label}</option>
                            ))}
                          </select>
                        </td>
                      );
                    }
                    return (
                      <td key={col.key} className={`px-4 py-2.5 ${col.width}`}>
                        <input
                          className="w-full px-2 py-1 border-2 border-indigo-400 rounded text-sm outline-none bg-indigo-50"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onBlur={saveEdit}
                          onKeyDown={handleKeyDown}
                          autoFocus
                        />
                      </td>
                    );
                  }

                  // Display mode
                  if (col.key === 'role') {
                    return (
                      <td
                        key={col.key}
                        className={`px-4 py-2.5 cursor-pointer hover:bg-indigo-50/30 transition-colors relative ${col.width}`}
                        onDoubleClick={() => startEdit(c.id, col.key, c.role)}
                        title="双击编辑角色类型"
                      >
                        <span className={getRoleBadge(value)}>{getRoleLabel(value)}</span>
                        <span className="absolute right-1 top-1/2 -translate-y-1/2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px]">✎</span>
                      </td>
                    );
                  }
                  if (col.key === 'traits') {
                    return (
                      <td
                        key={col.key}
                        className="px-4 py-2.5 cursor-pointer hover:bg-indigo-50/30 transition-colors relative"
                        onDoubleClick={() => startEdit(c.id, col.key, value)}
                        title="双击编辑性格特征"
                      >
                        <div className="flex flex-wrap gap-1">
                          {value.split(',').filter(Boolean).map((t, j) => (
                            <span key={j} className="text-xs px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded">{t.trim()}</span>
                          ))}
                          {!value && <span className="text-slate-300 italic">—</span>}
                        </div>
                        <span className="absolute right-1 top-1/2 -translate-y-1/2 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity text-[10px]">✎</span>
                      </td>
                    );
                  }
                  return (
                    <td
                      key={col.key}
                      className={`px-4 py-2.5 cursor-pointer hover:bg-indigo-50/30 transition-colors relative ${col.key === 'name' ? 'font-medium text-slate-800' : 'text-slate-500'} ${col.width}`}
                      onDoubleClick={() => startEdit(c.id, col.key, value)}
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
