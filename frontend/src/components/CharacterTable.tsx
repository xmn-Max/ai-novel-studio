interface CharacterItem {
  id?: string;
  name: string;
  role?: string;
  traits?: string[];
  description?: string;
}

interface Props {
  characters: CharacterItem[];
}

export default function CharacterTable({ characters }: Props) {
  if (!characters.length) return null;

  return (
    <section>
      <h3 className="text-base font-semibold text-slate-700 mb-3">角色分析</h3>
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">名称</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">角色</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">性格特征</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">描述</th>
            </tr>
          </thead>
          <tbody>
            {characters.map((c, i) => (
              <tr key={c.id || i} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2.5 font-medium text-slate-800">{c.name}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    c.role === 'protagonist' ? 'bg-indigo-100 text-indigo-700' :
                    c.role === 'supporting' ? 'bg-slate-100 text-slate-600' :
                    'bg-slate-50 text-slate-500'
                  }`}>
                    {c.role === 'protagonist' ? '主角' : c.role === 'supporting' ? '配角' : '次要'}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {(c.traits || []).map((t, j) => (
                      <span key={j} className="text-xs px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded">{t}</span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-slate-500">{c.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
