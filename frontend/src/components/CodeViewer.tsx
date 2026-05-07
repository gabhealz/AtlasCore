type CodeToken = {
  text: string;
  className: string;
};

type CodeViewerProps = {
  code: string;
};

function pushToken(tokens: CodeToken[], text: string, className: string) {
  if (!text) {
    return;
  }

  tokens.push({ text, className });
}

function findTagEnd(code: string, startIndex: number) {
  let quote: '"' | "'" | null = null;

  for (let index = startIndex + 1; index < code.length; index += 1) {
    const character = code[index];

    if (quote !== null) {
      if (character === quote) {
        quote = null;
      }
      continue;
    }

    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }

    if (character === '>') {
      return index;
    }
  }

  return code.length - 1;
}

function tokenizeAttributes(source: string): CodeToken[] {
  const tokens: CodeToken[] = [];
  let index = 0;

  while (index < source.length) {
    const character = source[index];

    if (/\s/.test(character)) {
      let whitespaceEnd = index + 1;
      while (whitespaceEnd < source.length && /\s/.test(source[whitespaceEnd])) {
        whitespaceEnd += 1;
      }
      pushToken(tokens, source.slice(index, whitespaceEnd), 'text-slate-500');
      index = whitespaceEnd;
      continue;
    }

    if (character === '/') {
      pushToken(tokens, character, 'text-slate-500');
      index += 1;
      continue;
    }

    let nameEnd = index;
    while (
      nameEnd < source.length &&
      !/[\s=/>]/.test(source[nameEnd])
    ) {
      nameEnd += 1;
    }

    pushToken(tokens, source.slice(index, nameEnd), 'text-amber-300');
    index = nameEnd;

    while (index < source.length && /\s/.test(source[index])) {
      let whitespaceEnd = index + 1;
      while (whitespaceEnd < source.length && /\s/.test(source[whitespaceEnd])) {
        whitespaceEnd += 1;
      }
      pushToken(tokens, source.slice(index, whitespaceEnd), 'text-slate-500');
      index = whitespaceEnd;
    }

    if (source[index] !== '=') {
      continue;
    }

    pushToken(tokens, '=', 'text-slate-400');
    index += 1;

    while (index < source.length && /\s/.test(source[index])) {
      let whitespaceEnd = index + 1;
      while (whitespaceEnd < source.length && /\s/.test(source[whitespaceEnd])) {
        whitespaceEnd += 1;
      }
      pushToken(tokens, source.slice(index, whitespaceEnd), 'text-slate-500');
      index = whitespaceEnd;
    }

    if (index >= source.length) {
      break;
    }

    const valueStart = source[index];
    if (valueStart === '"' || valueStart === "'") {
      let valueEnd = index + 1;
      while (valueEnd < source.length && source[valueEnd] !== valueStart) {
        valueEnd += 1;
      }
      if (valueEnd < source.length) {
        valueEnd += 1;
      }
      pushToken(tokens, source.slice(index, valueEnd), 'text-emerald-300');
      index = valueEnd;
      continue;
    }

    let valueEnd = index;
    while (valueEnd < source.length && !/[\s>]/.test(source[valueEnd])) {
      valueEnd += 1;
    }
    pushToken(tokens, source.slice(index, valueEnd), 'text-emerald-300');
    index = valueEnd;
  }

  return tokens;
}

function tokenizeTag(tagSource: string): CodeToken[] {
  if (tagSource.startsWith('<!--')) {
    return [{ text: tagSource, className: 'text-slate-500' }];
  }

  const doctypeMatch = tagSource.match(/^<!DOCTYPE([\s\S]*)>$/i);
  if (doctypeMatch) {
    return [
      { text: '<!DOCTYPE', className: 'text-fuchsia-300' },
      ...tokenizeAttributes(doctypeMatch[1]),
      { text: '>', className: 'text-slate-400' },
    ];
  }

  const tagMatch = tagSource.match(/^<(\/?)([A-Za-z][\w:-]*)([\s\S]*?)(\/?)>$/);
  if (!tagMatch) {
    return [{ text: tagSource, className: 'text-slate-300' }];
  }

  const [, closingPrefix, tagName, attributesSource, selfClosingPrefix] = tagMatch;
  return [
    { text: '<', className: 'text-slate-400' },
    ...(closingPrefix ? [{ text: closingPrefix, className: 'text-slate-400' }] : []),
    { text: tagName, className: 'text-sky-300' },
    ...tokenizeAttributes(attributesSource),
    ...(selfClosingPrefix ? [{ text: selfClosingPrefix, className: 'text-slate-400' }] : []),
    { text: '>', className: 'text-slate-400' },
  ];
}

function tokenizeHtml(code: string): CodeToken[] {
  const tokens: CodeToken[] = [];
  let index = 0;

  while (index < code.length) {
    if (code.startsWith('<!--', index)) {
      const commentEnd = code.indexOf('-->', index + 4);
      const resolvedEnd = commentEnd === -1 ? code.length : commentEnd + 3;
      pushToken(tokens, code.slice(index, resolvedEnd), 'text-slate-500');
      index = resolvedEnd;
      continue;
    }

    if (code[index] === '<') {
      const tagEnd = findTagEnd(code, index);
      tokens.push(...tokenizeTag(code.slice(index, tagEnd + 1)));
      index = tagEnd + 1;
      continue;
    }

    let textEnd = code.indexOf('<', index);
    if (textEnd === -1) {
      textEnd = code.length;
    }
    pushToken(tokens, code.slice(index, textEnd), 'text-slate-300');
    index = textEnd;
  }

  return tokens;
}

export default function CodeViewer({ code }: CodeViewerProps) {
  const tokens = tokenizeHtml(code);

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-950 shadow-inner">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
        <span>Code Viewer</span>
        <span>HTML + Tailwind</span>
      </div>
      <pre className="overflow-x-auto p-5 text-sm leading-6 text-slate-100">
        <code>
          {tokens.map((token, index) => (
            <span key={`${index}-${token.text.length}`} className={token.className}>
              {token.text}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
