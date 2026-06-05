export interface ProgressEvent {
  step: number;
  total: number;
  step_name: string;
  message: string;
  status: string;
  error?: string;
}

export interface Meta {
  title: string;
  chapter_count: number;
  scene_count: number;
  character_count: number;
}

export interface ConversionResult {
  yaml: string;
  meta: Meta;
}

const API_BASE = '/api';

export async function startConversion(text: string): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
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
  const es = new EventSource(`${API_BASE}/convert/${taskId}/progress`);

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

export async function fetchResult(taskId: string): Promise<ConversionResult> {
  const res = await fetch(`${API_BASE}/convert/${taskId}/result`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '获取结果失败');
  }

  return res.json();
}
