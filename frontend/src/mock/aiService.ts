interface PlotData {
  main_line: string;
  theme: string;
  conflict: string;
  climax: string;
  ending: string;
  pacing: string;
  [key: string]: string;
}

interface KeyEvent {
  id: string;
  name: string;
  description?: string;
  significance: string;
  chapter_refs?: number[];
  characters_involved?: string[];
}

interface ImprovementResult {
  plot: PlotData;
  events: KeyEvent[];
  message: string;
}

const FIELD_ALIASES: Record<string, keyof PlotData> = {
  '主线': 'main_line',
  '主题': 'theme',
  '冲突': 'conflict',
  '高潮': 'climax',
  '结局': 'ending',
  '节奏': 'pacing',
  'pacing': 'pacing',
  'main line': 'main_line',
  'mainLine': 'main_line',
};

const SIGNIFICANCE_OPTIONS = ['重大转折', '推进主线', '人物成长', '背景铺垫'];

function parseFieldUpdates(feedback: string): { updates: Record<string, string>; matched: boolean } {
  const updates: Record<string, string> = {};
  let matched = false;

  for (const [alias, field] of Object.entries(FIELD_ALIASES)) {
    const patterns = [
      new RegExp(`${alias}[：:是为改\\s]*[：:]*\\s*(.+)`, 'is'),
      new RegExp(`${alias}\\s*改为\\s*(.+)`, 'i'),
      new RegExp(`${alias}\\s*改成\\s*(.+)`, 'i'),
      new RegExp(`${alias}\\s*设定为\\s*(.+)`, 'i'),
      new RegExp(`${alias}\\s*是\\s*(.+)`, 'i'),
      new RegExp(`把${alias}[：:]*\\s*(.+)`, 'i'),
      new RegExp(`修改${alias}[：:]*\\s*(.+)`, 'i'),
    ];

    for (const pat of patterns) {
      const match = feedback.match(pat);
      if (match?.[1]) {
        let value = match[1].trim();
        value = value.replace(/[，。！？；、\n].*$/, '').trim();
        if (value.length > 1) {
          updates[field] = value;
          matched = true;
          break;
        }
      }
    }
  }

  return { updates, matched };
}

function parseEventOperations(feedback: string, events: KeyEvent[]): { events: KeyEvent[]; matched: boolean } {
  const newEvents = [...events];
  let matched = false;

  const addPatterns = [
    /(?:增加|添加|新增|加一个)\s*关键事件[：:]*\s*([A-Za-z]*\d+[：:]*\s*.+)/i,
    /(E\d+)[：:]*\s*([^-—]+?)(?:[-—]\s*(.+))?\s*(?=$|。|\n)/i,
    /关键事件[：:]*\s*(.+?)[：:]*?\s*[-—]\s*([^-—\n]+)/i,
  ];

  for (const pat of addPatterns) {
    const match = feedback.match(pat);
    if (match) {
      let name = '';
      let significance = '推进主线';
      let id = '';

      if (match[1]?.match(/^E\d+$/i)) {
        id = match[1].toUpperCase();
        name = match[2]?.trim() || '';
        significance = match[3]?.trim() || '推进主线';
      } else {
        name = match[1]?.trim() || match[2]?.trim() || '';
        id = `E${String(events.length + 1).padStart(3, '0')}`;
        significance = match[2]?.trim() || '推进主线';
      }

      if (name) {
        const existingIdx = newEvents.findIndex(e => e.id === id);
        if (existingIdx >= 0) {
          newEvents[existingIdx] = { ...newEvents[existingIdx], name, significance };
        } else {
          newEvents.push({ id, name, significance });
        }
        matched = true;
        break;
      }
    }
  }

  const deletePattern = /(?:删除|去掉|移除)\s*(?:关键事件\s*)?(E\d+)/i;
  const delMatch = feedback.match(deletePattern);
  if (delMatch?.[1]) {
    const idx = newEvents.findIndex(e => e.id.toUpperCase() === delMatch[1].toUpperCase());
    if (idx >= 0) {
      newEvents.splice(idx, 1);
      matched = true;
    }
  }

  const modifyPattern = /(E\d+)\s*(?:的)?\s*(?:类型|类别)[：:]*\s*(重大转折|推进主线|人物成长|背景铺垫)/i;
  const modMatch = feedback.match(modifyPattern);
  if (modMatch) {
    const idx = newEvents.findIndex(e => e.id.toUpperCase() === modMatch[1].toUpperCase());
    if (idx >= 0 && SIGNIFICANCE_OPTIONS.includes(modMatch[2])) {
      newEvents[idx] = { ...newEvents[idx], significance: modMatch[2] };
      matched = true;
    }
  }

  return { events: newEvents, matched };
}

function generateMessage(plotMatched: boolean, eventMatched: boolean, targetFields: string[]): string {
  const parts: string[] = [];
  if (plotMatched) {
    if (targetFields.length === 0) {
      parts.push('已根据意见微调主线');
    } else {
      const labels = targetFields.map(f => {
        const entry = Object.entries(FIELD_ALIASES).find(([, v]) => v === f);
        return entry?.[0] || f;
      });
      parts.push(`已更新: ${labels.join('、')}`);
    }
  }
  if (eventMatched) {
    parts.push('已更新关键事件');
  }
  if (!plotMatched && !eventMatched) {
    parts.push('已根据意见微调（意见不够明确，仅做了小幅优化）');
  }
  return parts.join('；');
}

export async function improvePlot(
  feedback: string,
  currentPlot: PlotData,
  currentEvents: KeyEvent[],
): Promise<ImprovementResult> {
  await new Promise(resolve => setTimeout(resolve, 1500));

  const plot = { ...currentPlot };
  const { updates, matched: plotMatched } = parseFieldUpdates(feedback);
  const targetFields: string[] = [];

  for (const [field, value] of Object.entries(updates)) {
    plot[field] = value;
    targetFields.push(field);
  }

  const { events, matched: eventMatched } = parseEventOperations(feedback, currentEvents);

  if (!plotMatched && !eventMatched) {
    plot.main_line = (plot.main_line || '') + '（已根据意见微调）';
  }

  const message = generateMessage(plotMatched, eventMatched, targetFields);

  return { plot, events, message };
}
