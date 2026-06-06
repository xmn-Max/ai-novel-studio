import { useState, useEffect } from 'react';
import { fetchGenres, addGenre, updateGenre, deleteGenre, GenreItem } from '../api';

interface Props {
  show: boolean;
  onClose: () => void;
  onUpdate: () => void;
}

export default function GenreManager({ show, onClose, onUpdate }: Props) {
  const [genres, setGenres] = useState<GenreItem[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState({ name: '', guidance: '', keywords: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      setGenres(await fetchGenres());
    } catch { /* ignore */ }
  };

  useEffect(() => { if (show) load(); }, [show]);

  const resetForm = () => {
    setForm({ name: '', guidance: '', keywords: '' });
    setEditing(null);
    setError('');
  };

  const handleAdd = async () => {
    if (!form.name.trim()) { setError('请输入类型名称'); return; }
    setLoading(true);
    setError('');
    try {
      await addGenre({
        name: form.name.trim(),
        guidance: form.guidance.trim(),
        keywords: form.keywords.split(/[,，\s]+/).filter(Boolean),
      });
      resetForm();
      await load();
      onUpdate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '添加失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (index: number) => {
    if (!form.name.trim()) { setError('请输入类型名称'); return; }
    setLoading(true);
    setError('');
    try {
      await updateGenre(index, {
        name: form.name.trim(),
        guidance: form.guidance.trim(),
        keywords: form.keywords.split(/[,，\s]+/).filter(Boolean),
      });
      resetForm();
      await load();
      onUpdate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '修改失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (index: number) => {
    if (!confirm('确认删除该类型？')) return;
    try {
      await deleteGenre(index);
      await load();
      onUpdate();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : '删除失败');
    }
  };

  const startEdit = (index: number) => {
    const g = genres[index];
    if (g.readonly) return;
    setEditing(index);
    setForm({
      name: g.name,
      guidance: g.guidance || '',
      keywords: (g.keywords || []).join(', '),
    });
    setError('');
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-900">管理小说类型</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg leading-none">&times;</button>
        </div>

        <div className="flex-1 overflow-auto px-6 py-4 space-y-4">
          {/* List */}
          <div className="space-y-2">
            {genres.map((g, i) => (
              <div key={i} className={`rounded-lg border p-3 ${g.readonly ? 'bg-slate-50 border-slate-100' : 'bg-white border-slate-200'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-800">{g.name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${g.readonly ? 'bg-slate-200 text-slate-500' : 'bg-indigo-100 text-indigo-700'}`}>
                      {g.readonly ? '系统' : '自定义'}
                    </span>
                  </div>
                  {!g.readonly && (
                    <div className="flex items-center gap-2">
                      <button onClick={() => startEdit(i)} className="text-xs text-indigo-600 hover:text-indigo-700">编辑</button>
                      <button onClick={() => handleDelete(i)} className="text-xs text-red-500 hover:text-red-600">删除</button>
                    </div>
                  )}
                </div>
                {g.guidance && (
                  <p className="text-xs text-slate-500 mt-1.5 line-clamp-2">{g.guidance}</p>
                )}
                {g.keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {g.keywords.map((kw, j) => (
                      <span key={j} className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">{kw}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add/Edit Form */}
          <div className="border-t border-slate-200 pt-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">
              {editing !== null ? '编辑类型' : '添加自定义类型'}
            </h4>
            {error && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">{error}</div>
            )}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">类型名称 *</label>
                <input
                  className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="如：悬疑、历史、军事"
                  maxLength={20}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">AI 指引</label>
                <textarea
                  className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm h-16 focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none resize-y"
                  value={form.guidance}
                  onChange={e => setForm({ ...form, guidance: e.target.value })}
                  placeholder="告诉 AI 这个类型的分析重点，如：请重点关注悬疑氛围、线索铺设和反转设计"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">关键词（逗号分隔）</label>
                <input
                  className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                  value={form.keywords}
                  onChange={e => setForm({ ...form, keywords: e.target.value })}
                  placeholder="如：侦探, 凶手, 密室, 反转"
                />
              </div>
              <div className="flex gap-2">
                <button onClick={resetForm} className="flex-1 py-2 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                  {editing !== null ? '取消编辑' : '清空'}
                </button>
                <button
                  onClick={() => editing !== null ? handleUpdate(editing) : handleAdd()}
                  disabled={loading}
                  className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? '保存中...' : editing !== null ? '保存修改' : '添加类型'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
