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
        vector: {
          darkest: '#07090e',
          darker: '#0b0f17',
          dark: '#121824',
          surface: '#182030',
          border: '#222f46',
          lime: '#d4ff00',
          'lime-glow': 'rgba(212, 255, 0, 0.25)',
          cyan: '#00f0ff',
          'cyan-glow': 'rgba(0, 240, 255, 0.25)',
          muted: '#8899ac',
        },
        vanta: {
          darkest: '#07090e',
          darker: '#0b0f17',
          dark: '#121824',
          surface: '#182030',
          border: '#222f46',
          lime: '#d4ff00',
          'lime-glow': 'rgba(212, 255, 0, 0.25)',
          cyan: '#00f0ff',
          'cyan-glow': 'rgba(0, 240, 255, 0.25)',
          muted: '#8899ac',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'border-beam': 'borderBeam 4s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 15px rgba(212, 255, 0, 0.3)' },
          '50%': { opacity: '.6', boxShadow: '0 0 5px rgba(212, 255, 0, 0.1)' },
        }
      }
    },
  },
  plugins: [],
}
