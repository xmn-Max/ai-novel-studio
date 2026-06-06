interface EventItem {
  id: string;
  name: string;
  significance: string;
}

interface Props {
  plot: Record<string, unknown> | null;
  isComplete: boolean;
  onReAnalyze: () => void;
}

export default function PlotSection({ plot, isComplete, onReAnalyze }: Props) {
  if (!plot) {
    if (isComplete) {
      return (
        <div className="text-center py-2">
          <button onClick={onReAnalyze} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            + 运行剧情分析
          </button>
        </div>
      );
    }
    return null;
  }

  const ml = String(plot.main_line ?? '');
  const theme = String(plot.theme ?? '');
  const conflict = String(plot.conflict ?? '');
  const climax = String(plot.climax ?? '');
  const pacing = String(plot.pacing ?? '');
  const events = (plot.events ?? []) as EventItem[];

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-slate-700">剧情分析</h3>
        <button onClick={onReAnalyze} className="text-xs text-indigo-600 hover:text-indigo-700">重新分析</button>
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
        {ml && (
          <div>
            <span className="text-xs font-medium text-slate-500">主线</span>
            <p className="text-sm text-slate-700 mt-0.5">{ml}</p>
          </div>
        )}
        {theme && (
          <div>
            <span className="text-xs font-medium text-slate-500">主题</span>
            <p className="text-sm text-slate-700 mt-0.5">{theme}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          {conflict && (
            <div>
              <span className="text-xs font-medium text-slate-500">冲突</span>
              <p className="text-sm text-slate-700 mt-0.5">{conflict}</p>
            </div>
          )}
          {climax && (
            <div>
              <span className="text-xs font-medium text-slate-500">高潮</span>
              <p className="text-sm text-slate-700 mt-0.5">{climax}</p>
            </div>
          )}
        </div>
        {pacing && (
          <div>
            <span className="text-xs font-medium text-slate-500">节奏</span>
            <span className="text-sm text-slate-700 ml-2">{pacing}</span>
          </div>
        )}
        {events.length > 0 && (
          <div>
            <span className="text-xs font-medium text-slate-500">关键事件</span>
            <div className="mt-1 space-y-1">
              {events.map((ev, i) => (
                <div key={ev.id || i} className="flex items-start gap-2 text-sm">
                  <span className="text-xs font-mono text-indigo-500 min-w-fit">{ev.id}</span>
                  <span className="font-medium text-slate-700 min-w-fit">{ev.name}</span>
                  <span className="text-xs text-slate-400">{ev.significance}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
