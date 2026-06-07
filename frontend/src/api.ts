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

export interface Meta {
  title: string;
  genre: string;
  chapter_count: number;
  scene_count: number;
  character_count: number;
  characters: string[];
  character_details: CharacterDetail[];
  validation?: ValidationInfo;
  schema_validation?: SchemaValidationInfo;
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
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
}

const API_BASE = '/api';

function getToken(): string {
  return localStorage.getItem('auth_token') || '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

// Auth

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
  const data = await handleResponse<AuthUser>(res);
  localStorage.setItem('auth_token', data.token);
  return data;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await handleResponse<AuthUser>(res);
  localStorage.setItem('auth_token', data.token);
  return data;
}

export async function fetchCurrentUser(): Promise<{ username: string } | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    return await handleResponse<{ username: string }>(res);
  } catch {
    localStorage.removeItem('auth_token');
    return null;
  }
}

export function logout() {
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
}

export function subscribeProgress(
  taskId: string,
  onProgress: (e: ProgressEvent) => void,
  onComplete: () => void,
  onError: (err: string) => void,
): () => void {
  const token = getToken();
  const es = new EventSource(`${API_BASE}/convert/${taskId}/progress?token=${encodeURIComponent(token)}`);

  let receivedData = false;

  es.onmessage = (event) => {
    receivedData = true;
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
    if (!receivedData) {
      onError('连接被拒绝，请检查登录状态');
    } else {
      onError('连接中断，请重试');
    }
    es.close();
  };

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

export async function updateCharacter(
  projectId: string, charId: string, field: string, value: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/characters/${charId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ field, value }),
  });
  await handleResponse(res);
}

export async function updatePlotField(
  projectId: string, field: string, value: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/plot`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ field, value }),
  });
  await handleResponse(res);
}

export async function updateScenePlanItem(
  projectId: string, planId: string, field: string, value: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/scene-plan/${planId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ field, value }),
  });
  await handleResponse(res);
}

// Versions
export interface VersionItem {
  version_id: string;
  label: string;
  feedback: string;
  timestamp_ms: number;
}

export interface VersionSnapshot {
  label: string;
  snapshot: Record<string, unknown>;
}

export async function saveVersion(projectId: string, feedback: string): Promise<{ label: string }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/versions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ feedback }),
  });
  return handleResponse(res);
}

export async function listVersions(projectId: string): Promise<VersionItem[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/versions`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function getVersion(projectId: string, versionId: string): Promise<VersionSnapshot> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/versions/${versionId}`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function restoreVersion(projectId: string, versionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/versions/${versionId}/restore`, {
    method: 'POST',
    headers: authHeaders(),
  });
  await handleResponse(res);
}

// Genres

export async function fetchGenres(): Promise<GenreItem[]> {
  const res = await fetch(`${API_BASE}/genres`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function addGenre(item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
  return handleResponse(res);
}

export async function updateGenre(index: number, item: GenreItem): Promise<GenreItem> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(item),
  });
  return handleResponse(res);
}

export async function deleteGenre(index: number): Promise<void> {
  const res = await fetch(`${API_BASE}/genres/${index}`, {
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
}

export async function regenerateScript(
  projectId: string, feedback: string,
): Promise<{ scenes: Array<Record<string, unknown>> }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ feedback }),
  });
  return handleResponse(res);
}

export async function requerySection(
  projectId: string, feedback: string, target: string,
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/requery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ feedback, target }),
  });
  return handleResponse(res);
}

export async function deepReview(
  projectId: string, feedback: string, versionAId: string, versionBId: string,
): Promise<{ version_id: string; label: string; scenes: unknown[]; yaml: string }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/deep-review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ feedback, version_a_id: versionAId, version_b_id: versionBId }),
  });
  return handleResponse(res);
}
