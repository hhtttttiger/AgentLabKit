import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';

type ErrorFallbackProps = {
  error: Error;
  onReset: () => void;
};

export function ErrorFallback({ error, onReset }: ErrorFallbackProps) {
  const { t } = useTranslation('common');

  return (
    <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="text-lg font-semibold text-text">
        {t('error.title', '出错了')}
      </div>
      <div className="max-w-md text-sm text-text-muted">
        {error.message || t('error.unknown', '发生了未知错误')}
      </div>
      <Button variant="primary" onClick={onReset}>
        {t('error.retry', '重试')}
      </Button>
    </div>
  );
}
