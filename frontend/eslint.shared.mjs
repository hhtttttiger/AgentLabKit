/**
 * Shared ESLint flat-config factory for the frontend monorepo.
 *
 * 每个 app 在自己的 eslint.config.mjs 里 import 已安装的插件实例,
 * 交给此工厂组装成一份 strict 的 React + TypeScript flat config。
 * 采用 non-type-aware(不强制 parserOptions.project),避免
 * "file not included in tsconfig" 之类的范围报错,保证开箱即用。
 */

/**
 * @param {object} opts
 * @param {object} opts.globals            - `globals` package
 * @param {object} opts.reactHooksPlugin   - `eslint-plugin-react-hooks`
 * @param {object} opts.reactPlugin        - `eslint-plugin-react`
 * @param {object} opts.tsParser           - `@typescript-eslint/parser`
 * @param {object} opts.tsPlugin           - `@typescript-eslint/eslint-plugin`
 * @param {string} [opts.project]          - tsconfig project path(可选,type-aware 时使用)
 * @param {string} [opts.tsconfigRootDir]  - tsconfig 根目录(可选)
 * @returns {object[]} ESLint flat config 数组
 */
export function createStrictReactTsConfig(opts) {
  const {
    globals: globalsPkg,
    reactHooksPlugin,
    reactPlugin,
    tsParser,
    tsPlugin,
    project,
    tsconfigRootDir,
  } = opts;

  const sharedGlobals = {
    ...(globalsPkg?.browser ?? {}),
    ...(globalsPkg?.node ?? {}),
    ...(globalsPkg?.es2022 ?? {}),
  };

  return [
    {
      name: 'shared/ignores',
      ignores: [
        'dist/**',
        'node_modules/**',
        'coverage/**',
        'build/**',
        '**/*.config.{js,mjs,cjs,ts}',
        'eslint.config.mjs',
      ],
    },
    {
      name: 'shared/base',
      files: ['**/*.{js,mjs,cjs,jsx,ts,tsx,cts,mts}'],
      languageOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
        globals: sharedGlobals,
      },
      plugins: {
        react: reactPlugin,
        'react-hooks': reactHooksPlugin,
      },
      settings: {
        react: { version: 'detect' },
      },
      rules: {
        'no-debugger': 'error',
        'no-var': 'error',
        'prefer-const': 'error',
        // React 17+ JSX transform 不再需要显式 import React
        'react/react-in-jsx-scope': 'off',
        'react/prop-types': 'off',
        'react/jsx-key': 'error',
        'react/no-deprecated': 'error',
        'react/no-unknown-property': 'error',
        // React Hooks —— rules-of-hooks 是正确性强约束,exhaustive-deps 提示依赖缺失
        'react-hooks/rules-of-hooks': 'error',
        'react-hooks/exhaustive-deps': 'warn',
      },
    },
    {
      name: 'shared/typescript',
      files: ['**/*.{ts,tsx,cts,mts}'],
      languageOptions: {
        parser: tsParser,
        parserOptions: {
          ecmaFeatures: { jsx: true },
          ...(project ? { project, tsconfigRootDir } : {}),
        },
      },
      plugins: {
        '@typescript-eslint': tsPlugin,
      },
      rules: {
        // TS 由 @typescript-eslint 接管未使用变量/未定义检测
        'no-unused-vars': 'off',
        'no-undef': 'off',
        '@typescript-eslint/no-unused-vars': [
          'error',
          {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_',
            caughtErrorsIgnorePattern: '^_',
          },
        ],
        // 以下规则对现有代码噪音过大,保持关闭(可按需开启)
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-non-null-assertion': 'off',
        '@typescript-eslint/consistent-type-imports': 'off',
      },
    },
  ];
}
