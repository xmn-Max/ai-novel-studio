import { useState } from 'react';
import { register, login } from '../api';

interface Props {
  onLogin: (username: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const fn = tab === 'register' ? register : login;
      const user = await fn(username, password);
      onLogin(user.username);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900">AI Novel Studio</h1>
          <p className="text-sm text-slate-500 mt-1">AI 剧本创作助手</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex border-b border-slate-200 mb-5">
            <button
              className={`flex-1 pb-2.5 text-sm font-semibold border-b-2 transition-colors ${
                tab === 'login' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
              }`}
              onClick={() => setTab('login')}
            >
              登录
            </button>
            <button
              className={`flex-1 pb-2.5 text-sm font-semibold border-b-2 transition-colors ${
                tab === 'register' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
              }`}
              onClick={() => setTab('register')}
            >
              注册
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">用户名</label>
              <input
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="至少 2 个字符"
                minLength={2}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">密码</label>
              <input
                type="password"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="至少 4 个字符"
                minLength={4}
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {loading ? '处理中...' : tab === 'login' ? '登录' : '注册'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
