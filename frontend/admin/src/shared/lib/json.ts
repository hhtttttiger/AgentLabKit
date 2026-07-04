export type JsonKind = 'object' | 'array';

export function getDefaultJson(kind: JsonKind) {
  return kind === 'array' ? '[]' : '{}';
}

export function validateJsonText(value: string, kind: JsonKind): string | null {
  const normalized = value.trim() || getDefaultJson(kind);

  try {
    const parsed = JSON.parse(normalized);

    if (kind === 'array' && !Array.isArray(parsed)) {
      return '这里需要输入 JSON 数组。';
    }

    if (kind === 'object' && (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object')) {
      return '这里需要输入 JSON 对象。';
    }

    return null;
  } catch {
    return 'JSON 格式不合法。';
  }
}

export function normalizeJsonText(value: string, kind: JsonKind) {
  return value.trim() || getDefaultJson(kind);
}
