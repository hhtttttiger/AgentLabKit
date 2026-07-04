export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';
export type AccentColor = 'blue' | 'violet' | 'emerald' | 'rose' | 'amber' | 'orange';

export interface ThemeContextValue {
  /** 当前选择的主题（可能为 system） */
  theme: Theme;
  /** 实际生效的主题（light 或 dark） */
  resolvedTheme: ResolvedTheme;
  /** 设置主题 */
  setTheme: (theme: Theme) => void;
  /** 切换主题（light <-> dark） */
  toggleTheme: () => void;
  /** 当前主题色 */
  accent: AccentColor;
  /** 设置主题色 */
  setAccent: (accent: AccentColor) => void;
}
