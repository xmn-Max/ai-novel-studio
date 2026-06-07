interface WorldItem {
  name?: string;
  time?: string;
  description?: string;
  event?: string;
}

interface Props {
  wb: Record<string, unknown> | null;
  isComplete: boolean;
  onReAnalyze: () => void;
}

const SECTIONS = [
  { key: 'realms', label: '界域/地点', color: 'text-indigo-600' },
  { key: 'factions', label: '势力/宗门', color: 'text-emerald-600' },
  { key: 'techniques', label: '功法/技能', color: 'text-amber-600' },
  { key: 'items', label: '法宝/物品', color: 'text-rose-600' },
  { key: 'timeline', label: '时间线', color: 'text-slate-600' },
  { key: 'rules', label: '规则', color: 'text-slate-600' },
];

export default function WorldSection({ wb, isComplete, onReAnalyze }: Props) {
  if (!wb) {
    if (isComplete) {
      return (
        <div className="text-center py-2">
          <button onClick={onReAnalyze} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            + 运行世界观分析
          </button>
        </div>
      );
    }
    return null;
  }

  const hasContent = SECTIONS.some(({ key }) => {
    const items = wb[key];
    return Array.isArray(items) && items.length > 0;
  });

  if (!hasContent) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-slate-700">世界观</h3>
        <button onClick={onReAnalyze} className="text-xs text-indigo-600 hover:text-indigo-700">重新分析</button>
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-4">
        {SECTIONS.map(({ key, label, color }) => {
          const items = wb[key];
          if (!Array.isArray(items) || items.length === 0) return null;
          return (
            <div key={key}>
              <h4 className={`text-xs font-semibold ${color} mb-2`}>{label}</h4>
              {typeof items[0] === 'string' ? (
                <ul className="space-y-1">
                  {(items as string[]).map((item, i) => (
                    <li key={i} className="text-sm text-slate-600">{item}</li>
                  ))}
                </ul>
              ) : (
                <div className="space-y-2">
                  {(items as WorldItem[]).map((item, i) => (
                    <div key={i} className="text-sm">
                      <span className="font-medium text-slate-700">{item.name || item.time}</span>
                      {item.description || item.event ? (
                        <span className="text-slate-500 ml-2">{item.description || item.event}</span>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
