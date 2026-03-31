/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      backgroundImage: {
        'hero-glow':
          'radial-gradient(circle at top left, rgba(111, 141, 255, 0.22), transparent 34%), radial-gradient(circle at 80% 10%, rgba(255, 255, 255, 0.08), transparent 22%), radial-gradient(circle at bottom right, rgba(77, 111, 255, 0.14), transparent 30%)'
      },
      boxShadow: {
        panel: '0 24px 80px rgba(0, 0, 0, 0.32)'
      },
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81'
        }
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
};
