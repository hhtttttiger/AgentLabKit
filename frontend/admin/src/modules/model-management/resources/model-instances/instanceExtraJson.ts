export const INSTANCE_URL_EXTRA_KEY = 'endpointUrl';
export const INSTANCE_URL_EXAMPLE = 'https://your-provider.example.com/v1';
const INSTANCE_URL_EXTRA_ALIASES = ['endpointUrl', 'endpointURL', 'instanceUrl', 'url', 'baseUrl'] as const;

/**
 * Read the instance endpoint URL from a parsed extraJson object.
 * Searches common key aliases and returns the first non-empty string match.
 */
export function readInstanceUrlFromExtraJson(extraJson: Record<string, unknown>): string {
  if (!extraJson || typeof extraJson !== 'object' || Array.isArray(extraJson)) {
    return '';
  }

  for (const key of INSTANCE_URL_EXTRA_ALIASES) {
    const value = extraJson[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return '';
}

/**
 * Write or remove the endpoint URL in the extraJson object.
 * Returns a new object (does not mutate the input).
 */
export function writeInstanceUrlToExtraJson(
  extraJson: Record<string, unknown>,
  instanceUrl: string,
): Record<string, unknown> {
  const trimmedUrl = instanceUrl.trim();

  if (trimmedUrl) {
    return { ...extraJson, [INSTANCE_URL_EXTRA_KEY]: trimmedUrl };
  }

  // Remove the key when url is empty
  const { [INSTANCE_URL_EXTRA_KEY]: _, ...rest } = extraJson;
  return rest;
}
