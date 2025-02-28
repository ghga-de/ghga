/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme');
export default {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        primary: '#00393f',
        secondary: '#005a5a',
        tertiary: '#e84614',
        quaternary: '#007e8c',
        quinary: '#cfe7cd',
        outline: '#70787a',
      },
      fontFamily: {
        mono: ['Illinois', ...defaultTheme.fontFamily.mono],
      },
    },
  },
  plugins: [],
};
