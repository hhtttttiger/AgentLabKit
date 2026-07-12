import { useTranslation } from 'react-i18next';
import { Badge } from '@/shared/ui/Badge';
import type { SkillFlowValidationResult } from '../lib/types';

export function SkillFlowValidationPanel({ validation }: { validation: SkillFlowValidationResult }) {
  const { t } = useTranslation(['common', 'agentManagement']);
  const wb = 'agentManagement:skills.workbench';
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge tone={validation.isValid ? 'success' : 'danger'}>
          {validation.isValid ? t(`${wb}.validation.pass`) : t(`${wb}.validation.fail`)}
        </Badge>
        <span className="text-sm text-text-secondary">
          {t(`${wb}.validation.errorCount`, { errors: validation.errors.length, warnings: validation.warnings.length })}
        </span>
      </div>

      {validation.errors.length > 0 ? (
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">{t(`${wb}.validation.errorsSection`)}</div>
          <ul className="mt-2 space-y-2">
            {validation.errors.map((error) => (
              <li key={error} className="rounded-[2px] border border-error/20 bg-error-subtle px-4 py-3 text-sm text-error-text">
                {error}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {validation.warnings.length > 0 ? (
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">{t(`${wb}.validation.warningsSection`)}</div>
          <ul className="mt-2 space-y-2">
            {validation.warnings.map((warning) => (
              <li key={warning} className="rounded-[2px] border border-warning/20 bg-warning-subtle px-4 py-3 text-sm text-warning-text">
                {warning}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
