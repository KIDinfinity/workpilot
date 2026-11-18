export type SSEMessage = { event: string; data: string };

/**
 * 按空行分帧解析 SSE 流。
 * 网络 chunk 边界与 SSE 帧边界无关，因此 buffer 里保留未闭合的半帧。
 */
export async function* readSSE(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<SSEMessage> {
  // TextDecoderStream 的 writable 类型是 BufferSource，比 Uint8Array 宽，需断言
  const decoder = new TextDecoderStream() as unknown as ReadableWritablePair<
    string,
    Uint8Array
  >;
  const reader = body.pipeThrough(decoder).getReader();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value.replace(/\r\n/g, "\n");
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const msg = parseFrame(frame);
        if (msg) yield msg;
      }
    }
    // 流结束但没有尾随空行时，最后半帧也要解析
    const tail = parseFrame(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): SSEMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (!line || line.startsWith(":")) continue; // 空行 / 心跳注释
    const i = line.indexOf(":");
    const field = i === -1 ? line : line.slice(0, i);
    let value = i === -1 ? "" : line.slice(i + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length ? { event, data: data.join("\n") } : null;
}
