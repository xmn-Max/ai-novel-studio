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
  genre?: string;
}

const GENRE_LABELS: Record<string, { key: string; label: string; color: string }[]> = {
  叙事: [
    { key: 'realms', label: '地点/环境', color: 'text-indigo-600' },
    { key: 'factions', label: '人物/群体', color: 'text-emerald-600' },
    { key: 'techniques', label: '能力/经历', color: 'text-amber-600' },
    { key: 'items', label: '物品/符号', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规则/制度', color: 'text-slate-600' },
  ],
  玄幻: [
    { key: 'realms', label: '界域/地点', color: 'text-indigo-600' },
    { key: 'factions', label: '势力/宗门', color: 'text-emerald-600' },
    { key: 'techniques', label: '功法/技能', color: 'text-amber-600' },
    { key: 'items', label: '法宝/物品', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规则', color: 'text-slate-600' },
  ],
  科幻: [
    { key: 'realms', label: '空间/星域', color: 'text-indigo-600' },
    { key: 'factions', label: '群体/组织', color: 'text-emerald-600' },
    { key: 'techniques', label: '科技/能力', color: 'text-amber-600' },
    { key: 'items', label: '物品/载具', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规则/原理', color: 'text-slate-600' },
  ],
  言情: [
    { key: 'realms', label: '地点/空间', color: 'text-indigo-600' },
    { key: 'factions', label: '人物/群体', color: 'text-emerald-600' },
    { key: 'techniques', label: '情感/技能', color: 'text-amber-600' },
    { key: 'items', label: '物品/象征', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规则/社会约束', color: 'text-slate-600' },
  ],
  魔幻: [
    { key: 'realms', label: '奇幻空间', color: 'text-indigo-600' },
    { key: 'factions', label: '势力/种族', color: 'text-emerald-600' },
    { key: 'techniques', label: '魔法/技能', color: 'text-amber-600' },
    { key: 'items', label: '神器/道具', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规则/魔法法则', color: 'text-slate-600' },
  ],
  武侠: [
    { key: 'realms', label: '江湖地点', color: 'text-indigo-600' },
    { key: 'factions', label: '势力/门派', color: 'text-emerald-600' },
    { key: 'techniques', label: '武功/技能', color: 'text-amber-600' },
    { key: 'items', label: '兵器/道具', color: 'text-rose-600' },
    { key: 'timeline', label: '时间线', color: 'text-slate-600' },
    { key: 'rules', label: '规矩/侠义准则', color: 'text-slate-600' },
  ],
};

const DEFAULT_SECTIONS = GENRE_LABELS['玄幻'];

export default function WorldSection({ wb, isComplete, onReAnalyze, genre }: Props) {
  const sections = genre ? (GENRE_LABELS[genre] || DEFAULT_SECTIONS) : DEFAULT_SECTIONS;

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

  const hasContent = sections.some(({ key }) => {
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
        {sections.map(({ key, label, color }) => {
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
