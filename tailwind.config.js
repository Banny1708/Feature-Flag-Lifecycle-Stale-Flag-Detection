/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        surface: {
          50: '#1e2433',
          100: '#181d2a',
          200: '#121622',
          300: '#0d111a',
          DEFAULT: '#111622',
        },
        border: {
          subtle: '#1e2638',
          DEFAULT: '#263047',
          strong: '#364362',
        },
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        status: {
          active: '#10b981',
          potentiallyStale: '#f59e0b',
          stale: '#ef4444',
          removalPending: '#8b5cf6',
          removed: '#64748b',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
