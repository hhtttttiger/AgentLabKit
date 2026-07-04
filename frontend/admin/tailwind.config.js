/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
          hover: 'rgb(var(--color-primary-hover) / <alpha-value>)',
          active: 'rgb(var(--color-primary-active) / <alpha-value>)',
          subtle: 'rgb(var(--color-primary-subtle) / <alpha-value>)',
          muted: 'rgb(var(--color-primary-muted) / <alpha-value>)',
        },
        // Background colors
        background: {
          DEFAULT: 'rgb(var(--color-background-default) / <alpha-value>)',
          subtle: 'rgb(var(--color-background-subtle) / <alpha-value>)',
          sunken: 'rgb(var(--color-background-sunken) / <alpha-value>)',
          elevated: 'rgb(var(--color-background-elevated) / <alpha-value>)',
        },
        // Surface colors (cards, panels)
        surface: {
          DEFAULT: 'rgb(var(--color-surface-default) / <alpha-value>)',
          raised: 'rgb(var(--color-surface-raised) / <alpha-value>)',
          overlay: 'rgb(var(--color-surface-overlay) / <alpha-value>)',
          scrim: 'rgb(var(--color-surface-scrim) / <alpha-value>)',
        },
        // Border colors
        border: {
          DEFAULT: 'rgb(var(--color-border-default) / <alpha-value>)',
          subtle: 'rgb(var(--color-border-subtle) / <alpha-value>)',
          strong: 'rgb(var(--color-border-strong) / <alpha-value>)',
          focus: 'rgb(var(--color-border-focus) / <alpha-value>)',
        },
        // Text colors
        text: {
          DEFAULT: 'rgb(var(--color-text-default) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
          muted: 'rgb(var(--color-text-muted) / <alpha-value>)',
          subtle: 'rgb(var(--color-text-subtle) / <alpha-value>)',
          inverse: 'rgb(var(--color-text-inverse) / <alpha-value>)',
          link: 'rgb(var(--color-text-link) / <alpha-value>)',
          'link-hover': 'rgb(var(--color-text-link-hover) / <alpha-value>)',
        },
        // State colors
        state: {
          hover: 'rgb(var(--color-state-hover) / <alpha-value>)',
          active: 'rgb(var(--color-state-active) / <alpha-value>)',
          focus: 'rgb(var(--color-state-focus) / <alpha-value>)',
          'focus-ring': 'rgb(var(--color-state-focus-ring) / <alpha-value>)',
        },
        // Feedback colors
        success: {
          DEFAULT: 'rgb(var(--color-success) / <alpha-value>)',
          subtle: 'rgb(var(--color-success-subtle) / <alpha-value>)',
          text: 'rgb(var(--color-success-text) / <alpha-value>)',
        },
        warning: {
          DEFAULT: 'rgb(var(--color-warning) / <alpha-value>)',
          subtle: 'rgb(var(--color-warning-subtle) / <alpha-value>)',
          text: 'rgb(var(--color-warning-text) / <alpha-value>)',
        },
        error: {
          DEFAULT: 'rgb(var(--color-error) / <alpha-value>)',
          subtle: 'rgb(var(--color-error-subtle) / <alpha-value>)',
          text: 'rgb(var(--color-error-text) / <alpha-value>)',
        },
        info: {
          DEFAULT: 'rgb(var(--color-info) / <alpha-value>)',
          subtle: 'rgb(var(--color-info-subtle) / <alpha-value>)',
          text: 'rgb(var(--color-info-text) / <alpha-value>)',
        },
        // Sidebar specific colors
        sidebar: {
          bg: 'rgb(var(--color-sidebar-bg) / <alpha-value>)',
          'bg-hover': 'rgb(var(--color-sidebar-bg-hover) / <alpha-value>)',
          'bg-active': 'rgb(var(--color-sidebar-bg-active) / <alpha-value>)',
          text: 'rgb(var(--color-sidebar-text) / <alpha-value>)',
          'text-muted': 'rgb(var(--color-sidebar-text-muted) / <alpha-value>)',
          border: 'rgb(var(--color-sidebar-border) / <alpha-value>)',
        },
      },
      height: {
        control: '2.5rem',      // 40px — unified form control height
        'control-sm': '2.25rem', // 36px — compact (toolbar / filter)
      },
      minHeight: {
        control: '2.5rem',
        'control-sm': '2.25rem',
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'DEFAULT': 'var(--shadow-DEFAULT)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
      },
      keyframes: {
        'card-enter': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
      animation: {
        'card-enter': 'card-enter 200ms ease both',
      },
    },
  },
  plugins: [],
}
