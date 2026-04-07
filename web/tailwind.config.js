/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        body: ['Noto Sans SC', 'sans-serif'],
      },
      colors: {
        brand: {
          50: 'hsl(27 92% 95%)',
          100: 'hsl(27 96% 88%)',
          200: 'hsl(25 94% 78%)',
          300: 'hsl(22 92% 66%)',
          400: 'hsl(18 88% 58%)',
          500: 'hsl(15 84% 52%)',
          600: 'hsl(12 77% 46%)',
          700: 'hsl(10 75% 39%)',
          800: 'hsl(8 73% 33%)',
          900: 'hsl(6 71% 28%)',
        },
      },
      boxShadow: {
        glass: '0 10px 40px hsl(15 84% 52% / 0.2)',
      },
      animation: {
        'fade-up': 'fadeUp 420ms ease-out both',
        'pulse-soft': 'pulseSoft 1800ms ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
};
