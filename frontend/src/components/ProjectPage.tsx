import { useState, useEffect, useCallback } from 'react';
import {
  getProject, startProjectConversion, subscribeProgress, fetchResult,
  uploadFile, fetchSteps,
  ProgressEvent, ConversionResult, ProjectFull,
} from '../api';
import WorkflowStepper from './WorkflowStepper';
import UploadSection from './UploadSection';
import EditableCharacterTable from './EditableCharacterTable';
import EditablePlotSection from './EditablePlotSection';
import WorldSection from './WorldSection';
import EditableScenePlanTable from './EditableScenePlanTable';
import ScriptViewer from './ScriptViewer';
import PluginPanel from './PluginPanel';
import FeedbackPanel from './FeedbackPanel';
import VersionHistory from './VersionHistory';
import { useProtagonistValidation } from './useProtagonistValidation';
import { requerySection, saveVersion } from '../api';

interface Props {
  projectId: string;
  onBack: () => void;
}

const CHAPTER_RE = /第[一二三四五六七八九十百千万\d]+[章节回]/;

function countChapters(text: string): number {
  const matches = text.match(new RegExp(CHAPTER_RE, 'g'));
  return matches ? matches.length : 0;
}

export default function ProjectPage({ projectId, onBack }: Props) {
  const [data, setData] = useState<ProjectFull | null>(null);
  const [text, setText] = useState('');
  const [fileName, setFileName] = useState('');
  const [converting, setConverting] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [uploading, setUploading] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [feedbackPrefill, setFeedbackPrefill] = useState('');
  const [versionVisible, setVersionVisible] = useState(false);
  const [lastFeedback, setLastFeedback] = useState('');
  const [feedbackTarget, setFeedbackTarget] = useState<string>('script');

  const chapterCount = countChapters(text);

  const loadProject = useCallback(async () => {
    try {
      setData(await getProject(projectId));
    } catch { /* ignore */ }
  }, [projectId]);

  useEffect(() => {
    loadProject();
    fetchSteps().then(setSteps).catch(() => {});
  }, [loadProject]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const result = await uploadFile(file);
      setText(result.text);
      setFileName(result.filename);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleConvert = async () => {
    if (text.trim().length < 100) { setError('文本过短，至少需要 100 个字符'); return; }
    setConverting(true);
    setError('');
    setResult(null);
    try {
      const { task_id } = await startProjectConversion(projectId, text);
      subscribeProgress(task_id,
        (e) => setProgress(e),
        async () => {
          try { const res = await fetchResult(task_id); setResult(res); setConverting(false); loadProject(); }
          catch (err: unknown) { setError(err instanceof Error ? err.message : '获取结果失败'); setConverting(false); }
        },
        (err) => { setError(err); setConverting(false); },
      );
    } catch (err: unknown) { setError(err instanceof Error ? err.message : '启动失败'); setConverting(false); }
  };

  const openFeedback = (prefill: string, target: string = 'script') => {
    setFeedbackPrefill(prefill);
    setFeedbackTarget(target);
    setFeedbackVisible(true);
  };

  const handleRegenerate = async (feedback: string) => {
    setError('');

    try {
      await saveVersion(projectId, feedback);

      await requerySection(projectId, feedback, feedbackTarget);

      const targetLabels: Record<string, string> = {
        script: '剧本',
        plot: '剧情分析',
        world: '世界观',
        characters: '角色设定',
      };
      const label = targetLabels[feedbackTarget] || feedbackTarget;
      setSuccessMsg(`${label}已根据反馈重新生成 ✓`);
      setTimeout(() => setSuccessMsg(''), 5000);
      setFeedbackVisible(false);
      setLastFeedback(feedback);

      await loadProject();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'AI 重新询问失败，请重试');
      setTimeout(() => setError(''), 5000);
    }
  };

  const project = data?.project;
  const isComplete = project?.state === 'COMPLETED';

  const characters = (data?.characters?.length ? data.characters : result?.meta?.character_details) || [];
  const protagonist = useProtagonistValidation(characters as Array<{ id?: string; name: string; role?: string }>);
  const plot = (result?.plot || data?.plot) as Record<string, unknown> | null;
  const wb = (result?.world_building || data?.world_building) as Record<string, unknown> | null;
  const scenePlan = ((result?.scene_plan || data?.scene_plan) || []) as Array<{
    id: string; purpose: string; location: string; time_of_day: string;
    conflict_level: string; event_refs: string[];
  }>;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-slate-400 hover:text-slate-600 text-sm">&larr; 返回</button>
          <h1 className="text-lg font-bold text-slate-900">{project?.title || '项目'}</h1>
          {project && (
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${
              project.state === 'COMPLETED' ? 'bg-emerald-100 text-emerald-700' :
              project.state === 'FAILED' ? 'bg-red-100 text-red-700' :
              project.state === 'IDLE' ? 'bg-slate-100 text-slate-500' :
              'bg-indigo-100 text-indigo-700'
            }`}>{project.state}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {protagonist.exists && (
            <span className={`text-xs px-2 py-0.5 rounded ${protagonist.isUnique ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
              主角: {protagonist.protagonistName} {protagonist.isUnique ? '✓' : '⚠'}
            </span>
          )}
          <button
            onClick={() => setVersionVisible(true)}
            className="text-xs px-2 py-0.5 text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 transition-colors"
          >
            版本历史
          </button>
          <span className="text-xs text-slate-400">{project?.genre}</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6 space-y-8">
        <UploadSection
          text={text} onTextChange={setText} fileName={fileName}
          chapterCount={chapterCount} converting={converting} uploading={uploading}
          error={error} onFileUpload={handleFileUpload} onConvert={handleConvert}
          onClearError={() => setError('')}
        />

        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700 flex justify-between items-center">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg('')} className="text-emerald-400 hover:text-emerald-600">&times;</button>
          </div>
        )}

        {(converting || progress) && (
          <section>
            <WorkflowStepper
              step={progress?.step || 0} total={progress?.total || 8}
              stepName={progress?.step_name || ''} message={progress?.message || ''}
              status={converting ? 'processing' : 'completed'} steps={steps}
            />
          </section>
        )}

        {/* Protagonist validation status */}
        {protagonist.exists && !protagonist.isUnique && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            <span className="font-medium">主角验证失败：</span>{protagonist.message}
          </div>
        )}

        {result?.meta?.schema_validation && result.meta.schema_validation.warnings.length > 0 && (
          <details className="text-xs text-slate-500">
            <summary>Schema 校验警告 ({result.meta.schema_validation.warnings.length})</summary>
            <ul className="mt-1 space-y-0.5">
              {result.meta.schema_validation.warnings.map((w, i) => (
                <li key={i} className="text-amber-600 pl-3">{w}</li>
              ))}
            </ul>
          </details>
        )}

        {result?.meta && (
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs px-3 py-1 bg-white border border-slate-200 rounded-full text-slate-600">{result.meta.genre}</span>
            <span className="text-xs px-3 py-1 bg-white border border-slate-200 rounded-full text-slate-600">{result.meta.chapter_count} 章</span>
            <span className="text-xs px-3 py-1 bg-white border border-slate-200 rounded-full text-slate-600">{result.meta.scene_count} 场景</span>
            <span className="text-xs px-3 py-1 bg-white border border-slate-200 rounded-full text-slate-600">{result.meta.character_count} 角色</span>
          </div>
        )}

        <EditableCharacterTable
          characters={characters}
          projectId={projectId}
          onUpdate={loadProject}
        />

        <EditablePlotSection
          plot={plot}
          projectId={projectId}
          isComplete={isComplete}
          onUpdate={loadProject}
          onOpenFeedback={(prefill: string) => openFeedback(prefill, 'plot')}
        />

        <WorldSection wb={wb} isComplete={isComplete} onReAnalyze={() => openFeedback('请改进世界观分析：', 'world')} />

        <EditableScenePlanTable
          items={scenePlan}
          projectId={projectId}
          onUpdate={loadProject}
        />

        {data?.script_scenes?.length ? (
          <section>
            <ScriptViewer
              scenes={data.script_scenes as Array<{
                scene_id: number; scene_heading: string; location: string;
                time_of_day: string; characters_present: string[];
                action: string[]; dialogues: Array<{ character: string; line: string; parenthetical?: string }>;
                transition: string;
              }>}
              projectId={projectId}
              onUpdate={loadProject}
            />
          </section>
        ) : null}

        {(result?.yaml || data?.yaml_data?.yaml_content) && (
          <div className="flex justify-center">
            <button
              onClick={() => {
                const yamlContent = data?.yaml_data?.yaml_content || result?.yaml || '';
                const blob = new Blob([yamlContent], { type: 'text/yaml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `${project?.title || 'script'}.yaml`; a.click();
                URL.revokeObjectURL(url);
              }}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition-colors"
            >下载 YAML 剧本</button>
          </div>
        )}

        {(isComplete || result) && (
          <section>
            <PluginPanel
              projectId={projectId}
              existingResults={(data?.plugin_results || []).map(pr => ({
                plugin_name: pr.plugin_name,
                result_data: pr.result_data as Record<string, unknown>,
              }))}
              onResultsChange={loadProject}
            />
          </section>
        )}

        <FeedbackPanel
          onRegenerate={handleRegenerate}
          disabled={converting}
          prefillText={feedbackPrefill}
          visible={feedbackVisible}
          onVisibilityChange={setFeedbackVisible}
          target={feedbackTarget}
        />

        {/* Floating re-analyze button when panel is hidden */}
        {(isComplete || result) && !feedbackVisible && (
          <div className="flex justify-center">
            <button
              onClick={() => openFeedback('请改进以下内容：角色设定、剧情结构、场景安排...', 'script')}
              className="px-6 py-3 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 shadow-lg hover:shadow-xl transition-all"
            >
              AI 改进反馈
            </button>
          </div>
        )}

        <div className="h-12" />

        <VersionHistory
          projectId={projectId}
          visible={versionVisible}
          onClose={() => setVersionVisible(false)}
          onRestored={loadProject}
          feedbackText={lastFeedback}
        />
      </main>
    </div>
  );
}
