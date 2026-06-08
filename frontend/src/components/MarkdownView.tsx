import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Conserta tabelas Markdown que a IA emitiu "coladas" numa unica linha
 * (cabecalho + |---| + linhas tudo junto), o que quebra a renderizacao GFM.
 * So atua em linhas que contem uma regua de delimitador (|---|---|) grudada a
 * conteudo; tabelas ja multi-linha passam intactas.
 */
function normalizeMarkdown(content: string): string {
  const delimiterRun = /\|(?:\s*:?-{3,}:?\s*\|)+/;
  return content
    .split('\n')
    .map((line) => {
      const match = line.match(delimiterRun);
      if (!match || match.index === undefined) {
        return line;
      }
      if (!line.trim().startsWith('|')) {
        return line;
      }
      const before = line.slice(0, match.index).trim();
      const after = line.slice(match.index + match[0].length).trim();
      // Delimitador sozinho na linha => tabela ja esta correta.
      if (before === '' && after === '') {
        return line;
      }
      const cols = (match[0].match(/-{3,}/g) || []).length;
      if (cols < 2 || before === '') {
        return line;
      }
      const splitRow = (segment: string) =>
        segment
          .replace(/^\|/, '')
          .replace(/\|$/, '')
          .split('|')
          .map((cell) => cell.trim());

      const header = splitRow(before);
      const data = after ? splitRow(after) : [];
      const headerLine = `| ${header.join(' | ')} |`;
      const delimLine = `|${Array(cols).fill('---').join('|')}|`;
      const rows: string[] = [];
      for (let i = 0; i < data.length; i += cols) {
        const row = data.slice(i, i + cols);
        while (row.length < cols) {
          row.push('');
        }
        rows.push(`| ${row.join(' | ')} |`);
      }
      return [headerLine, delimLine, ...rows].join('\n');
    })
    .join('\n');
}

/**
 * Renderiza Markdown (com tabelas GFM) em blocos estilizados, sem depender do
 * plugin de typography do Tailwind. Usado na revisao e na entrega.
 */
export function MarkdownView({ content }: { content: string }) {
  return (
    <div className="text-sm text-gray-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props) => (
            <h1
              className="mb-3 mt-6 text-2xl font-bold text-gray-900 first:mt-0"
              {...props}
            />
          ),
          h2: (props) => (
            <h2
              className="mb-2 mt-6 border-b border-gray-100 pb-1 text-xl font-bold text-gray-900 first:mt-0"
              {...props}
            />
          ),
          h3: (props) => (
            <h3
              className="mb-2 mt-4 text-base font-semibold text-gray-900"
              {...props}
            />
          ),
          h4: (props) => (
            <h4
              className="mb-1 mt-3 text-sm font-semibold text-gray-800"
              {...props}
            />
          ),
          p: (props) => <p className="my-2 leading-relaxed" {...props} />,
          ul: (props) => (
            <ul className="my-2 list-disc space-y-1 pl-5" {...props} />
          ),
          ol: (props) => (
            <ol className="my-2 list-decimal space-y-1 pl-5" {...props} />
          ),
          li: (props) => <li className="leading-relaxed" {...props} />,
          a: (props) => (
            <a
              className="break-words text-indigo-600 underline"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
          strong: (props) => (
            <strong className="font-semibold text-gray-900" {...props} />
          ),
          em: (props) => <em className="italic" {...props} />,
          blockquote: (props) => (
            <blockquote
              className="my-3 border-l-4 border-gray-200 pl-4 italic text-gray-600"
              {...props}
            />
          ),
          hr: () => <hr className="my-4 border-gray-200" />,
          code: (props) => (
            <code
              className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs text-gray-800"
              {...props}
            />
          ),
          table: (props) => (
            <div className="my-3 overflow-x-auto">
              <table
                className="w-full border-collapse text-left text-xs"
                {...props}
              />
            </div>
          ),
          thead: (props) => <thead className="bg-gray-50" {...props} />,
          th: (props) => (
            <th
              className="border border-gray-200 px-3 py-2 font-semibold text-gray-700"
              {...props}
            />
          ),
          td: (props) => (
            <td
              className="border border-gray-200 px-3 py-2 align-top text-gray-700"
              {...props}
            />
          ),
        }}
      >
        {normalizeMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
