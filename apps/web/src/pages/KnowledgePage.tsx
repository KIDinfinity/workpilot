import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import {
  api,
  deleteDoc,
  uploadDoc,
  type KBChunk,
  type KBDocument,
} from "../api/client";

const ACCEPT = ".md,.pdf,.html,.txt";

function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
}

// 状态值直接沿用后端枚举（pending/processing/ready/failed），与 E2E 断言 `ready` 对齐。
const STATUS_LABEL: Record<KBDocument["status"], string> = {
  pending: "pending",
  processing: "processing",
  ready: "ready",
  failed: "failed",
};

const STATUS_CLS: Record<KBDocument["status"], string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [viewing, setViewing] = useState<KBDocument | null>(null);
  const [chunks, setChunks] = useState<KBChunk[] | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await api.listDocs());
    } catch {
      /* 拉取失败不打断页面，保留旧列表 */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!docs.some((d) => d.status === "pending" || d.status === "processing"))
      return;
    const t = setInterval(() => void refresh(), 2000);
    return () => clearInterval(t);
  }, [docs, refresh]);

  async function handleFiles(files: FileList | null) {
    const list = Array.from(files ?? []);
    if (list.length === 0) return;
    setBusy(true);
    setError(null);
    for (const f of list) {
      try {
        await uploadDoc(f);
      } catch (e) {
        setError(`${f.name}：${(e as Error).message}`);
      }
    }
    setBusy(false);
    await refresh();
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    void handleFiles(e.dataTransfer.files);
  }

  async function onDelete(d: KBDocument) {
    if (!window.confirm(`确定删除「${d.filename}」？其向量与对象存储文件将一并删除。`))
      return;
    try {
      await deleteDoc(d.id);
      if (viewing?.id === d.id) setViewing(null);
    } catch (e) {
      setError(`${d.filename}：${(e as Error).message}`);
    }
    await refresh();
  }

  async function onViewChunks(d: KBDocument) {
    setViewing(d);
    setChunks(null);
    try {
      setChunks(await api.listChunks(d.id));
    } catch (e) {
      setChunks([]);
      setError(`${d.filename}：${(e as Error).message}`);
    }
  }

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-800">知识库文档</h1>
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          disabled={busy}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? "上传中…" : "上传文档"}
        </button>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`mb-3 flex min-h-20 cursor-pointer flex-col items-center justify-center rounded border-2 border-dashed p-4 text-sm text-gray-500 ${
          dragActive ? "border-blue-400 bg-blue-50" : "border-gray-300"
        }`}
        onClick={() => fileInput.current?.click()}
      >
        <p>拖拽文件到此处，或点击选择文件上传</p>
        <p className="mt-1 text-xs text-gray-400">
          支持 .md / .pdf / .html / .txt，单文件 ≤ 10MB
        </p>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept={ACCEPT}
          data-testid="file-input"
          className="hidden"
          onChange={(e) => {
            void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-400">
              <th className="py-2 pr-2 font-medium">文件名</th>
              <th className="py-2 pr-2 font-medium">大小</th>
              <th className="py-2 pr-2 font-medium">状态</th>
              <th className="py-2 pr-2 font-medium">分块数</th>
              <th className="py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-400">
                  暂无文档，上传一个试试。
                </td>
              </tr>
            )}
            {docs.map((d) => (
              <tr
                key={d.id}
                data-testid="doc-row"
                className="border-b border-gray-100"
              >
                <td className="py-2 pr-2 text-gray-800">{d.filename}</td>
                <td className="py-2 pr-2 text-gray-500">{formatBytes(d.size)}</td>
                <td className="py-2 pr-2">
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-xs ${STATUS_CLS[d.status]}`}
                    title={d.status === "failed" ? d.error ?? "" : undefined}
                  >
                    {STATUS_LABEL[d.status]}
                  </span>
                </td>
                <td className="py-2 pr-2 text-gray-500">{d.chunks}</td>
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => void onViewChunks(d)}
                    disabled={d.status !== "ready"}
                    className="mr-2 text-blue-600 hover:underline disabled:cursor-not-allowed disabled:text-gray-300"
                  >
                    查看分块
                  </button>
                  <button
                    type="button"
                    onClick={() => void onDelete(d)}
                    className="text-red-600 hover:underline"
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {viewing && (
        <div className="fixed inset-0 z-10 flex justify-end bg-black/20">
          <div className="flex h-full w-[480px] flex-col bg-white p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-medium text-gray-800">
                {viewing.filename} · 分块
              </h2>
              <button
                type="button"
                onClick={() => setViewing(null)}
                className="rounded px-2 py-1 text-gray-500 hover:bg-gray-100"
              >
                关闭
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {chunks === null ? (
                <p className="text-sm text-gray-400">加载中…</p>
              ) : chunks.length === 0 ? (
                <p className="text-sm text-gray-400">暂无分块。</p>
              ) : (
                chunks.map((c) => (
                  <div
                    key={c.chunk_index}
                    className="mb-2 rounded border border-gray-100 bg-gray-50 p-2"
                  >
                    <p className="mb-1 text-xs text-gray-400">
                      第 {c.chunk_index + 1} 块
                      {c.section ? ` · ${c.section}` : ""}
                    </p>
                    <p className="whitespace-pre-wrap text-sm text-gray-700">
                      {c.text}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
