import type { components } from "../types/api";

// 名字以 `pnpm gen:api` 生成文件为准：FastAPI 用 Pydantic 模型类名作为 schema 名。
// 两个 AskReq（/v1/ask 与 /v1/kb/ask）同名，OpenAPI 用模块路径消歧义。
export type AskRequest = components["schemas"]["app__routes__kb__AskReq"];
export type AskResponse = components["schemas"]["KBAnswer"];
export type Conversation = components["schemas"]["Conversation"];
export type Message = components["schemas"]["Message"];
export type FeedbackIn = components["schemas"]["FeedbackIn"];
export type Feedback = components["schemas"]["Feedback"];
export type FeedbackRating = components["schemas"]["FeedbackRating"];
export type FeedbackReason = components["schemas"]["FeedbackReason"];

// 知识库文档（Day25）。后端 SQLModel 表直接序列化，字段与 app/db/models.py 的 KBDocument 对应。
export type KBDocument = {
  id: string;
  filename: string;
  object_key: string | null;
  size: number;
  status: "pending" | "processing" | "ready" | "failed";
  error: string | null;
  chunks: number;
  created_at: string;
  updated_at: string;
};

export type KBChunk = {
  chunk_index: number;
  section: string;
  text: string;
};

export class ApiError extends Error {
  status: number;
  requestId?: string;
  constructor(status: number, message: string, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      const raw = body?.error?.message ?? body?.detail ?? message;
      message = typeof raw === "string" ? raw : JSON.stringify(raw);
    } catch {
      /* 响应不是 JSON，保留 statusText；兼容 Day27 的 {error:{message}} 与 FastAPI 默认 {detail} */
    }
    throw new ApiError(
      res.status,
      message,
      res.headers.get("x-request-id") ?? undefined,
    );
  }
  return (await res.json()) as T;
}

// 上传文件必须用 FormData（multipart/form-data），不能走 request() 的 JSON Content-Type。
export async function uploadDoc(file: File): Promise<KBDocument> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/v1/kb/upload", { method: "POST", body: form });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      const raw = body?.error?.message ?? body?.detail ?? message;
      message = typeof raw === "string" ? raw : JSON.stringify(raw);
    } catch {
      /* 响应不是 JSON，保留 statusText */
    }
    throw new ApiError(
      res.status,
      message,
      res.headers.get("x-request-id") ?? undefined,
    );
  }
  return (await res.json()) as KBDocument;
}

export async function deleteDoc(id: string): Promise<void> {
  const res = await fetch(`/v1/kb/docs/${id}`, { method: "DELETE" });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      const raw = body?.error?.message ?? body?.detail ?? message;
      message = typeof raw === "string" ? raw : JSON.stringify(raw);
    } catch {
      /* 响应不是 JSON，保留 statusText */
    }
    throw new ApiError(
      res.status,
      message,
      res.headers.get("x-request-id") ?? undefined,
    );
  }
}

export const api = {
  ask: (body: AskRequest) =>
    request<AskResponse>("/v1/kb/ask", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listConversations: () =>
    request<Conversation[]>("/v1/conversations"),
  listMessages: (conversationId: string) =>
    request<Message[]>(`/v1/conversations/${conversationId}/messages`),
  sendFeedback: (messageId: string, body: FeedbackIn) =>
    request<Feedback>(`/v1/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listDocs: () => request<KBDocument[]>("/v1/kb/docs"),
  listChunks: (docId: string) =>
    request<KBChunk[]>(`/v1/kb/docs/${docId}/chunks`),
};
