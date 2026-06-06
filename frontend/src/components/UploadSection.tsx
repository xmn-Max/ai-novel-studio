import { ChangeEvent } from 'react';

interface Props {
  text: string;
  onTextChange: (text: string) => void;
  fileName: string;
  chapterCount: number;
  converting: boolean;
  uploading: boolean;
  error: string;
  onFileUpload: (e: ChangeEvent<HTMLInputElement>) => void;
  onConvert: () => void;
  onClearError: () => void;
}

export default function UploadSection({
  text, onTextChange, fileName, chapterCount, converting, uploading,
  error, onFileUpload, onConvert, onClearError,
}: Props) {
  return (
    <section>
      <h3 className="text-base font-semibold text-slate-700 mb-3">导入小说</h3>
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={onClearError} className="text-red-400 hover:text-red-600">&times;</button>
        </div>
      )}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <label className="px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm cursor-pointer hover:bg-slate-50 transition-colors">
            {uploading ? '上传中...' : '上传文件'}
            <input type="file" accept=".txt,.docx,.pdf" onChange={onFileUpload} className="hidden" disabled={uploading} />
          </label>
          {fileName && <span className="text-xs text-slate-500">{fileName}</span>}
          <span className="text-xs text-slate-400">支持 TXT / DOCX / PDF</span>
        </div>
        <textarea
          className="w-full h-48 px-4 py-3 border border-slate-300 rounded-lg text-sm font-mono leading-relaxed focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none resize-y"
          value={text}
          onChange={e => onTextChange(e.target.value)}
          placeholder="粘贴小说正文（至少100字，建议3章以上）..."
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className={`text-xs ${chapterCount >= 3 ? 'text-emerald-600' : 'text-amber-600'}`}>
              已识别 {chapterCount} 个章节（需 ≥3）
            </span>
            <span className="text-xs text-slate-400">字数: {text.length}</span>
          </div>
          <button
            onClick={onConvert}
            disabled={converting || text.trim().length < 100}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors ${
              converting ? 'bg-slate-200 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {converting ? '转换中...' : '开始转换'}
          </button>
        </div>
      </div>
    </section>
  );
}
