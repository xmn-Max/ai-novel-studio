export interface ProgressEvent {
  step: number;
  total: number;
  step_name: string;
  message: string;
  status: string;
  error?: string;
}

export interface ValidationInfo {
  main_character: string;
  count: number;
  status: string;
  retried: boolean;
}

export interface SchemaValidationInfo {
  passed: boolean;
  warnings: string[];
  errors: string[];
}

export interface Meta {
  title: string;
  genre: string;
  chapter_count: number;
  scene_count: number;
  character_count: number;
  characters: string[];
  character_details: Array<{ id: string; name: string; role: string; description: string }>;
  validation?: ValidationInfo;
  schema_validation?: SchemaValidationInfo;
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
}

const API_BASE = '/api';

function getToken(): string {
  return sessionStorage.getItem('auth_token') || '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Auth ---

export interface AuthUser {
  username: string;
  token: string;
  created_at?: string;
}

export async function register(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '注册失败');
  }
  const data = await res.json();
  sessionStorage.setItem('auth_token', data.token);
  return data;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '登录失败');
  }
  const data = await res.json();
  sessionStorage.setItem('auth_token', data.token);
  return data;
}

export async function fetchCurrentUser(): Promise<{ username: string } | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    if (!res.ok) {
      sessionStorage.removeItem('auth_token');
      return null;
    }
    return res.json();
  } catch {
    return null;
  }
}

export function logout() {
  sessionStorage.removeItem('auth_token');
}

export async function startConversion(text: string, genre: string, title: string): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ text, genre, title }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '启动转换失败');
  }

  return res.json();
}

export function subscribeProgress(
  taskId: string,
  onProgress: (e: ProgressEvent) => void,
  onComplete: () => void,
  onError: (err: string) => void,
): () => void {
  const token = getToken();
  const es = new EventSource(`${API_BASE}/convert/${taskId}/progress?token=${encodeURIComponent(token)}`);

  es.onmessage = (event) => {
    try {
      const data: ProgressEvent = JSON.parse(event.data);
      onProgress(data);

      if (data.status === 'completed') {
        onComplete();
        es.close();
      } else if (data.status === 'failed') {
        onError(data.error || '转换失败');
        es.close();
      }
    } catch {
      onError('解析进度数据失败');
      es.close();
    }
  };

  es.onerror = () => {
    onError('连接中断，请重试');
    es.close();
  };

  return () => es.close();
}

export interface GenreItem {
  name: string;
  guidance: string;
  keywords: string[];
  readonly?: boolean;
}

export async function fetchGenres(): Promise<GenreItem[]> {
  const res = await fetch(`${API_BASE}/genres`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取类型列表失败');
  return res.json();
}

export async function addGenre(item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '添加失败');
  }
  return res.json();
}

export async function updateGenre(index: number, item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '修改失败');
  }
  return res.json();
}

export async function deleteGenre(index: number): Promise<void> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '删除失败');
  }
}

export async function fetchResult(taskId: string): Promise<ConversionResult> {
  const res = await fetch(`${API_BASE}/convert/${taskId}/result`, { headers: authHeaders() });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '获取结果失败');
  }

  return res.json();
}

export async function regenerate(taskId: string, hints: string): Promise<ConversionResult> {
  const res = await fetch(`${API_BASE}/convert/${taskId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ hints }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '重新生成失败');
  }
  return res.json();
}
