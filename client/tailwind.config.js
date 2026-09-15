/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // 薄荷绿主题（沿用 1.0）
        mint: {
          50: '#F5FFFA',
          100: '#E6F7F0',
          200: '#C8F0DE',
          300: '#88D8B0',
          400: '#70CF9F',
          500: '#5CB88D',
          600: '#4A9F7A',
        },
      },
    },
  },
  plugins: [],
}
