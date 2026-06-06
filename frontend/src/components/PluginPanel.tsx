import { useState } from 'react';
import { listPlugins, runPlugin } from '../api';

interface PluginResult {
  plugin_name: string;
  result_data: Record<string, unknown>;
}

interface Props {
  projectId: string;
  existingResults: PluginResult[];
  onResultsChange: () => void;
}

export default function PluginPanel({ projectId, existingResults, onResultsChange }: Props) {
  const [pluginList, setPluginList] = useState<Array<{ name: string; label: string; description: string }>>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);

  const loadPlugins = async () => {
    try {
      const list = await listPlugins();
      setPluginList(list);
    } catch { /* ignore */ }
  };

  const handleRun = async (pluginName: string) => {
    setLoading(pluginName);
    try {
      await runPlugin(projectId, pluginName);
      onResultsChange();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : '运行失败');
    } finally {
      setLoading(null);
    }
  };

  if (!showPanel) {
    return (
      <button
        onClick={() => { setShowPanel(true); loadPlugins(); }}
        className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
      >
        + 运行扩展插件
      </button>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-slate-700">扩展插件</h3>
        <button onClick={() => setShowPanel(false)} className="text-xs text-slate-400 hover:text-slate-600">收起</button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {pluginList.map(pl => {
          const existing = existingResults.find(r => r.plugin_name === pl.name);
          return (
            <div key={pl.name} className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="text-sm font-semibold text-slate-800">{pl.label}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{pl.description}</p>
                </div>
              </div>

              {existing ? (
                <details className="mt-2">
                  <summary className="text-xs text-indigo-600 cursor-pointer hover:text-indigo-700">查看结果</summary>
                  <pre className="mt-2 bg-slate-50 rounded p-2 text-xs max-h-40 overflow-auto text-slate-600">
                    {JSON.stringify(existing.result_data, null, 2)}
                  </pre>
                </details>
              ) : (
                <button
                  onClick={() => handleRun(pl.name)}
                  disabled={loading === pl.name}
                  className="mt-2 px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-medium hover:bg-indigo-100 disabled:opacity-50 transition-colors"
                >
                  {loading === pl.name ? '运行中...' : '运行'}
                </button>
              )}

              {existing && (
                <button
                  onClick={() => handleRun(pl.name)}
                  disabled={loading === pl.name}
                  className="mt-2 ml-2 px-3 py-1.5 text-xs text-slate-400 hover:text-indigo-600 transition-colors"
                >
                  {loading === pl.name ? '运行中...' : '重新运行'}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
