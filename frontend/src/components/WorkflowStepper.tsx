interface Props {
  step: number;
  total: number;
  stepName: string;
  message: string;
  status: string;
  steps?: string[];
}

const DEFAULT_STEPS = ['文本清洗', '章节检测', '角色提取', '剧情分析', '场景规划', '剧本生成', '世界观分析', '校验'];

export default function WorkflowStepper({ step, total, stepName, message, status, steps }: Props) {
  const allSteps = steps?.length ? steps : DEFAULT_STEPS;
  const isDone = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-slate-700">
          {isDone ? '✓ 工作流完成' : isFailed ? '✗ 工作流失败' : 'AI 工作流'}
        </span>
        <span className="text-xs text-slate-400">{step}/{total}</span>
      </div>

      <div className="flex items-center gap-1 mb-3 flex-wrap">
        {allSteps.map((name, i) => {
          const stepNum = i + 1;
          const isCurrent = stepNum === step && !isDone && !isFailed;
          const isComplete = stepNum < step || (isDone && stepNum <= total);
          return (
            <div key={name} className="flex items-center">
              <span className={`w-2 h-2 rounded-full ${
                isComplete ? 'bg-emerald-500' : isCurrent ? 'bg-indigo-500 animate-pulse' : 'bg-slate-200'
              }`} title={name} />
              {stepNum < allSteps.length && (
                <span className={`w-3 h-px ${stepNum < step ? 'bg-emerald-300' : 'bg-slate-200'}`} />
              )}
            </div>
          );
        })}
      </div>

      {!isDone && !isFailed && message && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-indigo-600">{stepName}</span>
          <span className="text-xs text-slate-500">{message}</span>
        </div>
      )}

      <div className="mt-2 bg-slate-100 rounded-full h-1">
        <div
          className={`h-full rounded-full transition-all duration-500 ${isFailed ? 'bg-red-400' : 'bg-indigo-500'}`}
          style={{ width: `${isDone ? 100 : (step / total) * 100}%` }}
        />
      </div>
    </div>
  );
}
