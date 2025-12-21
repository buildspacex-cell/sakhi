/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    '../../packages/ui/**/*.{ts,tsx}',
    '../../packages/config/**/*.{ts,tsx}'
  ],
  presets: [require('../../packages/config/tailwind-preset')],
  theme: {
    extend: {}
  },
  plugins: []
};
