import type { Conversation } from "../api/client";

export function ConversationList({
  conversations,
  activeId,
  onNew,
  onSelect,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="flex h-full flex-col overflow-hidden rounded border border-gray-200 bg-gray-50">
      <div className="border-b border-gray-200 p-2">
        <button
          type="button"
          onClick={onNew}
          className="w-full rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          ＋ 新会话
        </button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {conversations.length === 0 && (
          <p className="p-2 text-xs text-gray-400">
            还没有历史会话，点「新会话」开始提问。
          </p>
        )}
        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => c.id && onSelect(c.id)}
            className={`block w-full rounded px-2 py-1.5 text-left text-sm ${
              c.id === activeId
                ? "bg-blue-100 text-blue-800"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <span className="block truncate">{c.title}</span>
            <span className="block truncate text-[11px] text-gray-400">
              {c.updated_at
                ? new Date(c.updated_at).toLocaleString("zh-CN", { hour12: false })
                : ""}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
