import defaultTheme from 'tailwindcss/defaultTheme'

// Palette taken from the AHAM Housing Finance brand: deep navy (logo navy #283079, site navy #1e1b4b / #17153a),
// gold accent (#eab308) and the red of the logo roof (#ed2636).
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['"Inter Variable"', 'Inter', ...defaultTheme.fontFamily.sans] },
      colors: {
        brand: {
          50: '#f2f3fa', 100: '#e4e6f4', 200: '#c8cce8', 300: '#a0a7d6', 400: '#7580bf', 500: '#4d58a3',
          600: '#364090', 700: '#283079', 800: '#1e1b4b', 900: '#17153a', 950: '#0f0e29',
        },
        gold: {
          50: '#fefce8', 100: '#fef9c3', 200: '#fef08a', 300: '#fde047', 400: '#facc15', 500: '#eab308', 600: '#ca8a04', 700: '#a16207',
        },
        roof: { 50: '#fff1f2', 100: '#ffe0e2', 200: '#ffc6ca', 500: '#ed2636', 600: '#d41f2e', 700: '#b01a27' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(23,21,58,0.04), 0 6px 20px -8px rgba(23,21,58,0.10)',
        pop: '0 12px 40px -12px rgba(23,21,58,0.35)',
      },
      keyframes: { shimmer: { '100%': { transform: 'translateX(100%)' } } },
      animation: { shimmer: 'shimmer 1.6s infinite' },
    },
  },
  plugins: [],
}
