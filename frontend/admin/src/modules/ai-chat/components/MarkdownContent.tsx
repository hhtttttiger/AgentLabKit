/**
 * AI Chat Module — Markdown Content Renderer
 * react-markdown + gfm tables + syntax highlighting.
 * No raw HTML passthrough for security.
 */
import { type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';
import { CopyButton } from './CopyButton';

type MarkdownContentProps = {
  content: string;
};

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );
}

// ── Custom components ────────────────────────────────────────────────

const markdownComponents: Components = {
  pre({ children, className, ...props }) {
    const lang = extractLanguage(className);
    const text = extractTextContent(children);

    return (
      <div className="group relative my-3 overflow-hidden rounded-[2px] border border-border bg-[#0f1f33] dark:bg-[#0a1525]">
        {lang && (
          <span className="absolute left-3 top-2 text-[11px] font-medium text-text-muted">
            {lang}
          </span>
        )}
        <CopyButton text={text} />
        <pre
          className="overflow-x-auto px-4 py-4 pt-8 text-sm leading-6 text-[#e8f1ff]"
          {...props}
        >
          {children}
        </pre>
      </div>
    );
  },

  code({ className, children, ...props }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded bg-surface-subtle px-1 py-0.5 text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },

  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline decoration-primary/30 hover:decoration-primary"
        {...props}
      >
        {children}
      </a>
    );
  },

  // Style tables for readability
  table({ children }) {
    return (
      <div className="my-3 overflow-x-auto">
        <table className="min-w-full border-collapse border border-border text-sm">
          {children}
        </table>
      </div>
    );
  },

  th({ children }) {
    return (
      <th className="border border-border bg-surface-subtle px-3 py-2 text-left font-medium text-text">
        {children}
      </th>
    );
  },

  td({ children }) {
    return (
      <td className="border border-border px-3 py-2 text-text">
        {children}
      </td>
    );
  },
};

// ── Helpers ──────────────────────────────────────────────────────────

function extractLanguage(className?: string): string | null {
  if (!className) return null;
  const match = className.match(/language-(\w+)/);
  return match ? match[1] : null;
}

function extractTextContent(children: ReactNode): string {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) {
    return children.map((c) => {
      if (typeof c === 'string') return c;
      if (c && typeof c === 'object' && 'props' in c) {
        const props = c.props as { children?: ReactNode };
        return extractTextContent(props.children);
      }
      return '';
    }).join('');
  }
  return '';
}
