/**
 * AI Chat Module — Copy Button
 * Copies text to clipboard with brief visual feedback.
 */
import { useCallback, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { useTranslation } from 'react-i18next';

type CopyButtonProps = {
  text: string;
};

export function CopyButton({ text }: CopyButtonProps) {
  const { t } = useTranslation('aiChat');
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silently fail
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="absolute right-2 top-2 rounded-[2px] p-1.5 text-text-muted opacity-0 transition-all hover:bg-surface-hover hover:text-text group-hover:opacity-100"
      title={copied ? t('message.copied') : t('message.copy')}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}
