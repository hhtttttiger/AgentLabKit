import { normalizeJsonText, validateJsonText, type JsonKind } from '@/shared/lib/json';
import { Button } from './Button';
import { TextAreaField } from './FormFields';

export function JsonEditor({
  label,
  value,
  kind,
  onChange,
  hint,
  placeholder,
  disabled = false,
}: {
  label: string;
  value: string;
  kind: JsonKind;
  onChange: (value: string) => void;
  hint?: string;
  placeholder?: string;
  disabled?: boolean;
}) {
  const error = validateJsonText(value, kind);

  return (
    <div className="space-y-2">
      <TextAreaField
        label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        error={error}
        hint={hint}
        placeholder={placeholder}
        disabled={disabled}
      />
      <div className="flex justify-end">
        <Button variant="ghost" disabled={disabled} onClick={() => onChange(normalizeJsonText(value, kind))}>
          格式化 JSON
        </Button>
      </div>
    </div>
  );
}
