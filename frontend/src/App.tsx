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
  );
}
