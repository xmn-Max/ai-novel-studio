import { useState } from 'react';
import { updateScriptScene } from '../api';

interface DialogueItem {
  character: string;
  line: string;
  parenthetical?: string;
}

interface SceneItem {
  scene_id: number;
  scene_heading: string;
  location: string;
  time_of_day: string;
  characters_present: string[];
  action: string[];
  dialogues: DialogueItem[];
  transition: string;
}

interface Props {
  scenes: SceneItem[];
  projectId: string;
  onUpdate?: () => void;
}

export default function ScriptViewer({ scenes, projectId, onUpdate }: Props) {
  const [tab, setTab] = useState<'view' | 'yaml'>('view');
  const [editingScene, setEditingScene] = useState<number | null>(null);
  const [editData, setEditData] = useState<SceneItem | null>(null);

  const handleCopy = () => {
    const text = scenes.map(s => {
      const lines = [s.scene_heading || `第${s.scene_id}场  ${s.location}  ${s.time_of_day}`];
      lines.push('');
      if (s.action?.length) { lines.push(...s.action); lines.push(''); }
      if (s.dialogues?.length) {
        s.dialogues.forEach(d => {
          const prefix = d.parenthetical ? `${d.character} (${d.parenthetical})` : d.character;
          lines.push(`${prefix}: ${d.line}`);
        });
        lines.push('');
      }
      if (s.transition) lines.push(`[${s.transition}]`);
      return lines.join('\n');
    }).join('\n---\n\n');
    navigator.clipboard.writeText(text).catch(() => {});
  };

  const startEdit = (scene: SceneItem) => {
    setEditingScene(scene.scene_id);
    setEditData({ ...scene });
  };

  const saveEdit = async () => {
    if (!editData || editingScene === null) return;
    try {
      await updateScriptScene(projectId, editingScene, {
        scene_heading: editData.scene_heading,
        location: editData.location,
        time_of_day: editData.time_of_day,
        characters_present: editData.characters_present,
        action: editData.action,
        dialogues: editData.dialogues,
        transition: editData.transition,
      });
      setEditingScene(null);
      setEditData(null);
      onUpdate?.();
    } catch { alert('保存失败'); }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-slate-700">剧本</h3>
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${tab === 'view' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`}
              onClick={() => setTab('view')}
            >结构化</button>
            <button
              className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${tab === 'yaml' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`}
              onClick={() => setTab('yaml')}
            >YAML</button>
          </div>
          <button onClick={handleCopy} className="px-3 py-1 text-xs font-medium text-slate-500 hover:text-indigo-600 border border-slate-200 rounded-lg hover:border-indigo-300 transition-colors">
            复制
          </button>
          <span className="text-xs text-slate-400">{scenes.length} 场</span>
        </div>
      </div>

      {tab === 'view' ? (
        <div className="space-y-3">
          {scenes.map((scene, idx) => (
            <details key={scene.scene_id || idx} className="bg-white rounded-lg border border-slate-200 group">
              <summary className="px-4 py-3 cursor-pointer flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-indigo-500">S{scene.scene_id}</span>
                  <span className="text-sm font-medium text-slate-800">
                    {scene.location || '未指定地点'}
                  </span>
                  <span className="text-xs text-slate-400">{scene.time_of_day}</span>
                  {scene.characters_present?.length > 0 && (
                    <span className="text-xs text-slate-400">
                      {scene.characters_present.join('、')}
                    </span>
                  )}
                </div>
                <button
                  onClick={e => { e.preventDefault(); startEdit(scene); }}
                  className="text-xs text-slate-300 hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-all"
                >
                  编辑
                </button>
              </summary>
              <div className="px-4 pb-4 border-t border-slate-100 pt-3">
                {scene.action?.length > 0 && (
                  <div className="mb-3">
                    {scene.action.map((a, i) => (
                      <p key={i} className="text-sm text-slate-600 leading-relaxed mb-1 italic">{a}</p>
                    ))}
                  </div>
                )}
                {scene.dialogues?.length > 0 && (
                  <div className="space-y-2">
                    {scene.dialogues.map((d, i) => (
                      <div key={i} className="flex gap-2 text-sm">
                        <span className="font-semibold text-indigo-600 min-w-fit">{d.character}:</span>
                        <span className="text-slate-700">{d.line}</span>
                        {d.parenthetical && (
                          <span className="text-xs text-slate-400 italic">({d.parenthetical})</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {scene.transition && (
                  <p className="text-xs text-slate-400 mt-3">转场: {scene.transition}</p>
                )}
              </div>
            </details>
          ))}
        </div>
      ) : (
        <pre className="bg-slate-900 text-slate-100 rounded-lg p-4 text-xs font-mono overflow-auto max-h-[500px] leading-relaxed">
          {scenes.map((s, i) => (
            <div key={i} className="mb-4">
              <span className="text-indigo-400">scene_{s.scene_id}:</span>{'\n'}
              <span className="text-emerald-400">  location:</span> <span className="text-slate-300">"{s.location}"</span>{'\n'}
              <span className="text-emerald-400">  time:</span> <span className="text-slate-300">"{s.time_of_day}"</span>{'\n'}
              {s.characters_present?.length > 0 && (
                <><span className="text-emerald-400">  characters:</span>{'\n'}{s.characters_present.map(c => `    - "${c}"`).join('\n')}{'\n'}</>
              )}
              {s.action?.length > 0 && (
                <><span className="text-emerald-400">  action:</span>{'\n'}{s.action.map(a => `    - "${a}"`).join('\n')}{'\n'}</>
              )}
              {s.dialogues?.length > 0 && (
                <><span className="text-emerald-400">  dialogue:</span>{'\n'}{s.dialogues.map(d => (
                  `    - character: "${d.character}"\n      line: "${d.line}"${d.parenthetical ? `\n      parenthetical: "${d.parenthetical}"` : ''}`
                )).join('\n')}{'\n'}</>
              )}
              {s.transition && <><span className="text-emerald-400">  transition:</span> <span className="text-slate-300">"{s.transition}"</span>{'\n'}</>}
            </div>
          ))}
        </pre>
      )}

      {/* Edit Modal */}
      {editingScene !== null && editData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-xl max-h-[85vh] overflow-auto">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">编辑场景 S{editData.scene_id}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">场景标题</label>
                <input className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" value={editData.scene_heading} onChange={e => setEditData({ ...editData, scene_heading: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">地点</label>
                  <input className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" value={editData.location} onChange={e => setEditData({ ...editData, location: e.target.value })} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">时间</label>
                  <input className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" value={editData.time_of_day} onChange={e => setEditData({ ...editData, time_of_day: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">出场角色（逗号分隔）</label>
                <input className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" value={editData.characters_present.join(', ')} onChange={e => setEditData({ ...editData, characters_present: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">动作描述（每行一条）</label>
                <textarea className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm h-20 font-mono" value={editData.action.join('\n')} onChange={e => setEditData({ ...editData, action: e.target.value.split('\n').filter(Boolean) })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">对白（格式：角色名:台词）</label>
                <textarea className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm h-28 font-mono" value={editData.dialogues.map(d => `${d.character}: ${d.line}${d.parenthetical ? ` (${d.parenthetical})` : ''}`).join('\n')} onChange={e => {
                  const lines = e.target.value.split('\n').filter(Boolean);
                  const dialogues = lines.map(line => {
                    const colonIdx = line.indexOf(':');
                    if (colonIdx === -1) return { character: '', line: line, parenthetical: '' };
                    const character = line.slice(0, colonIdx).trim();
                    const rest = line.slice(colonIdx + 1).trim();
                    const parenMatch = rest.match(/\(([^)]+)\)\s*$/);
                    return parenMatch
                      ? { character, line: rest.slice(0, parenMatch.index).trim(), parenthetical: parenMatch[1] }
                      : { character, line: rest, parenthetical: '' };
                  });
                  setEditData({ ...editData, dialogues });
                }} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">转场</label>
                <input className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" value={editData.transition} onChange={e => setEditData({ ...editData, transition: e.target.value })} />
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={() => { setEditingScene(null); setEditData(null); }} className="flex-1 py-2 border border-slate-300 rounded-lg text-sm text-slate-600">取消</button>
                <button onClick={saveEdit} className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700">保存</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
