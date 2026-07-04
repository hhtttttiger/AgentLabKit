export function asOptionalString(value: string) {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

export function asOptionalBooleanFilter(value: string): boolean | undefined {
  if (value === 'true') return true;
  if (value === 'false') return false;
  return undefined;
}
