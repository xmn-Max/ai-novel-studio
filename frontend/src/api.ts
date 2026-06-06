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

<<<<<<< HEAD
=======
export interface CharacterDetail {
  id: string;
  name: string;
  gender: string;
  age: string;
  role: string;
  traits: string[];
  description: string;
  aliases: string[];
  relationships: Array<{ target: string; relation: string }>;
}

>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
export interface Meta {
  title: string;
  genre: string;
  chapter_count: number;
  scene_count: number;
  character_count: number;
  characters: string[];
<<<<<<< HEAD
  character_details: Array<{ id: string; name: string; role: string; description: string }>;
=======
  character_details: CharacterDetail[];
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
  validation?: ValidationInfo;
  schema_validation?: SchemaValidationInfo;
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
<<<<<<< HEAD
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
=======
  characters?: CharacterDetail[];
  plot?: Record<string, unknown>;
  scene_plan?: Array<Record<string, unknown>>;
  world_building?: Record<string, unknown>;
  chapters?: Array<Record<string, unknown>>;
}

export interface ProjectSummary {
  id: string;
  user_id: string;
  title: string;
  genre: string;
  state: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectFull {
  project: ProjectSummary;
  chapters: Array<Record<string, unknown>>;
  characters: CharacterDetail[];
  plot: Record<string, unknown> | null;
  scene_plan: Array<Record<string, unknown>>;
  script_scenes: Array<Record<string, unknown>>;
  world_building: Record<string, unknown> | null;
  yaml_data: { yaml_content: string } | null;
  plugin_results: Array<{ plugin_name: string; result_data: Record<string, unknown> }>;
  fsm: { state: string; label: string };
}

export interface PluginResult {
  plugin_name: string;
  result_data: Record<string, unknown>;
}

export interface GenreItem {
  name: string;
  guidance: string;
  keywords: string[];
  readonly?: boolean;
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}

const API_BASE = '/api';

function getToken(): string {
<<<<<<< HEAD
  return sessionStorage.getItem('auth_token') || '';
=======
  return localStorage.getItem('auth_token') || '';
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

<<<<<<< HEAD
// --- Auth ---
=======
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

// Auth
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57

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
<<<<<<< HEAD
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '注册失败');
  }
  const data = await res.json();
  sessionStorage.setItem('auth_token', data.token);
=======
  const data = await handleResponse<AuthUser>(res);
  localStorage.setItem('auth_token', data.token);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
  return data;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
<<<<<<< HEAD
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '登录失败');
  }
  const data = await res.json();
  sessionStorage.setItem('auth_token', data.token);
=======
  const data = await handleResponse<AuthUser>(res);
  localStorage.setItem('auth_token', data.token);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
  return data;
}

export async function fetchCurrentUser(): Promise<{ username: string } | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
<<<<<<< HEAD
    if (!res.ok) {
      sessionStorage.removeItem('auth_token');
      return null;
    }
    return res.json();
  } catch {
=======
    return await handleResponse<{ username: string }>(res);
  } catch {
    localStorage.removeItem('auth_token');
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
    return null;
  }
}

export function logout() {
<<<<<<< HEAD
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
=======
  localStorage.removeItem('auth_token');
}

// Projects

export async function createProject(title: string, genre: string): Promise<{ project_id: string }> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ title, genre }),
  });
  return handleResponse(res);
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${API_BASE}/projects`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function getProject(projectId: string): Promise<ProjectFull> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: 'DELETE', headers: authHeaders(),
  });
  await handleResponse(res);
}

// Upload

export async function uploadFile(file: File): Promise<{ filename: string; text: string; char_count: number }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST', headers: authHeaders(), body: form,
  });
  return handleResponse(res);
}

// Conversion

export async function startProjectConversion(
  projectId: string, text?: string, file?: File,
): Promise<{ task_id: string }> {
  const form = new FormData();
  if (text) form.append('text', text);
  if (file) form.append('file', file);
  const res = await fetch(`${API_BASE}/projects/${projectId}/convert`, {
    method: 'POST', headers: authHeaders(), body: form,
  });
  return handleResponse(res);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
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
<<<<<<< HEAD
      console.log('[SSE] received:', data);
      onProgress(data);

      if (data.status === 'completed') {
        console.log('[SSE] task completed');
        onComplete();
        es.close();
      } else if (data.status === 'failed') {
        console.log('[SSE] task failed:', data.error);
=======
      onProgress(data);
      if (data.status === 'completed') {
        onComplete();
        es.close();
      } else if (data.status === 'failed') {
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
        onError(data.error || '转换失败');
        es.close();
      }
    } catch {
<<<<<<< HEAD
      console.error('[SSE] parse error');
=======
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
      onError('解析进度数据失败');
      es.close();
    }
  };

  es.onerror = () => {
<<<<<<< HEAD
    console.error('[SSE] connection error');
=======
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
    onError('连接中断，请重试');
    es.close();
  };

<<<<<<< HEAD
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
=======
  return () => {
    es.close();
  };
}

export async function fetchResult(taskId: string): Promise<ConversionResult> {
  const res = await fetch(`${API_BASE}/convert/${taskId}/result`, { headers: authHeaders() });
  return handleResponse(res);
}

// Standalone analysis

export async function runPlotAnalysis(projectId: string, text: string): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('text', text);
  const res = await fetch(`${API_BASE}/projects/${projectId}/plot`, {
    method: 'POST', headers: authHeaders(), body: form,
  });
  return handleResponse(res);
}

export async function runWorldBuilding(projectId: string, text: string): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append('text', text);
  const res = await fetch(`${API_BASE}/projects/${projectId}/world`, {
    method: 'POST', headers: authHeaders(), body: form,
  });
  return handleResponse(res);
}

// Plugins

export async function listPlugins(): Promise<Array<{ name: string; label: string; description: string }>> {
  const res = await fetch(`${API_BASE}/plugins`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function runPlugin(
  projectId: string, pluginName: string,
): Promise<{ plugin: string; result: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/plugins/${pluginName}`, {
    method: 'POST', headers: authHeaders(),
  });
  return handleResponse(res);
}

// Script Editor

export async function updateScriptScene(
  projectId: string, sceneId: number, updates: Record<string, unknown>,
): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/script/${sceneId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(updates),
  });
  await handleResponse(res);
}

// Genres

export async function fetchGenres(): Promise<GenreItem[]> {
  const res = await fetch(`${API_BASE}/genres`, { headers: authHeaders() });
  return handleResponse(res);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}

export async function addGenre(item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
<<<<<<< HEAD
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '添加失败');
  }
  return res.json();
=======
  return handleResponse(res);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}

export async function updateGenre(index: number, item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
<<<<<<< HEAD
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '修改失败');
  }
  return res.json();
=======
  return handleResponse(res);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}

export async function deleteGenre(index: number): Promise<void> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
<<<<<<< HEAD
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

export interface ConversionSummary {
  id: string;
  title: string;
  genre: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function fetchConversions(): Promise<ConversionSummary[]> {
  const res = await fetch(`${API_BASE}/conversions`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取历史记录失败');
  return res.json();
}

export async function deleteConversion(taskId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversions/${taskId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '删除失败');
  }
}

export async function editConversion(taskId: string, yaml: string): Promise<ConversionResult> {
  const res = await fetch(`${API_BASE}/conversions/${taskId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ yaml }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '保存失败');
  }
  return res.json();
=======
    method: 'DELETE', headers: authHeaders(),
  });
  await handleResponse(res);
}

// State

export async function getProjectState(projectId: string): Promise<{ state: string; label: string }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/state`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function fetchSteps(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/steps`, { headers: authHeaders() });
  return handleResponse(res);
>>>>>>> 63ce69f6a2c1e575377a37604d227d7053933c57
}
