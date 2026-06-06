interface ScenePlanItem {
  id: string;
  purpose: string;
  location: string;
  time_of_day: string;
  conflict_level: string;
  event_refs: string[];
}

interface Props {
  items: ScenePlanItem[];
}

export default function ScenePlanTable({ items }: Props) {
  if (!items.length) return null;

  return (
    <section>
      <h3 className="text-base font-semibold text-slate-700 mb-3">场景规划</h3>
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">ID</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">目的</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">地点</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">时间</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">冲突</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">关联事件</th>
            </tr>
          </thead>
          <tbody>
            {items.map((sp, i) => (
              <tr key={sp.id || i} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2.5 font-mono text-xs text-indigo-500">{sp.id}</td>
                <td className="px-4 py-2.5 text-slate-700">{sp.purpose}</td>
                <td className="px-4 py-2.5 text-slate-500">{sp.location}</td>
                <td className="px-4 py-2.5 text-slate-500">{sp.time_of_day}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    sp.conflict_level === '高' ? 'bg-red-100 text-red-700' :
                    sp.conflict_level === '中' ? 'bg-amber-100 text-amber-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>{sp.conflict_level}</span>
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-400">
                  {(sp.event_refs || []).join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
