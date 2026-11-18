import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

// 把 [3] 改写成指向 #cite-3 的链接，再在 a 组件里渲染成 chip
const toCiteLinks = (s: string) => s.replace(/\[(\d{1,2})\](?!\()/g, "[$1](#cite-$1)");

export function AnswerMarkdown({
  text,
  onCite,
}: {
  text: string;
  onCite: (n: number) => void;
}) {
  return (
    <div className="prose prose-sm max-w-none break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]} // 白名单清洗：去掉 script / on* 属性 / javascript: 链接
        components={{
          a: ({ href, children }) => {
            const m = href?.match(/^#cite-(\d+)$/);
            if (m) {
              return (
                <button
                  type="button"
                  data-testid="citation-chip"
                  onClick={() => onCite(Number(m[1]))}
                  className="mx-0.5 rounded bg-blue-100 px-1.5 align-super text-xs text-blue-700 hover:bg-blue-200"
                >
                  {m[1]}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {toCiteLinks(text)}
      </ReactMarkdown>
    </div>
  );
}
