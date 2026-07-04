import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import globals from 'globals';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import reactPlugin from 'eslint-plugin-react';
import { createStrictReactTsConfig } from '../eslint.shared.mjs';

const configDirectory = dirname(fileURLToPath(import.meta.url));

export default createStrictReactTsConfig({
  globals,
  reactHooksPlugin,
  reactPlugin,
  tsParser,
  tsPlugin: tseslint,
  project: './tsconfig.json',
  tsconfigRootDir: configDirectory,
});
