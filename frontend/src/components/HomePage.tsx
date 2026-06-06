import { useState, useEffect } from 'react';
import { listProjects, createProject, deleteProject, fetchGenres, ProjectSummary } from '../api';

interface Props {
  username: string;
  onLogout: () => void;
  onOpenProject: (projectId: string) => void;
}

export default function HomePage({ username, onLogout, onOpenProject }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [genres, setGenres] = useState<Array<{ name: string }>>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newGenre, setNewGenre] = useState('叙事');
  const [loading, setLoading] = useState(false);

  const loadProjects = async () => {
    try {
      const list = await listProjects();
      setProjects(list);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadProjects();
    fetchGenres().then(setGenres).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setLoading(true);
    try {
      const { project_id } = await createProject(newTitle.trim(), newGenre);
      setShowCreate(false);
      setNewTitle('');
      onOpenProject(project_id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除该项目？所有数据将永久丢失。')) return;
    try {
      await deleteProject(id);
      loadProjects();
    } catch { alert('删除失败'); }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-900">AI Novel Studio</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">{username}</span>
          <button onClick={onLogout} className="text-sm text-slate-400 hover:text-slate-600">退出</button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="mb-10">
          <h2 className="text-3xl font-bold text-slate-900">从小说到影视的智能创作平台</h2>
          <p className="mt-2 text-slate-500">上传小说，自动生成角色、剧情、剧本与影视方案</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors"
          >
            + 开始创作
          </button>
        </div>

        {/* Create Modal */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
            <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">新建项目</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">项目名称</label>
                  <input
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                    value={newTitle}
                    onChange={e => setNewTitle(e.target.value)}
                    placeholder="如：凡人修仙传"
                    onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">小说类型</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                    value={newGenre}
                    onChange={e => setNewGenre(e.target.value)}
                  >
                    {(genres.length ? genres : [{ name: '叙事' }]).map(g => (
                      <option key={g.name} value={g.name}>{g.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2 pt-2">
                  <button onClick={() => setShowCreate(false)} className="flex-1 py-2 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50">取消</button>
                  <button onClick={handleCreate} disabled={loading} className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">{loading ? '创建中...' : '创建'}</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Project List */}
        <section>
          <h3 className="text-base font-semibold text-slate-700 mb-3">我的项目</h3>
          {projects.length === 0 ? (
            <p className="text-sm text-slate-400">暂无项目，点击上方按钮开始创作</p>
          ) : (
            <div className="space-y-2">
              {projects.map(p => (
                <div
                  key={p.id}
                  className="bg-white rounded-lg border border-slate-200 px-4 py-3 flex items-center justify-between hover:shadow-sm transition-shadow cursor-pointer group"
                  onClick={() => onOpenProject(p.id)}
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-800">{p.title}</div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-slate-400">{p.genre}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        p.state === 'COMPLETED' ? 'bg-emerald-100 text-emerald-700' :
                        p.state === 'FAILED' ? 'bg-red-100 text-red-700' :
                        p.state === 'IDLE' ? 'bg-slate-100 text-slate-500' :
                        'bg-indigo-100 text-indigo-700'
                      }`}>{p.state}</span>
                      <span className="text-xs text-slate-400">{p.updated_at?.slice(0, 10)}</span>
                    </div>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); handleDelete(p.id); }}
                    className="text-xs text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
