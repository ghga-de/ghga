/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme');
const colors = require('tailwindcss/colors');

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
        error: '#ba1a1a',
        warning: colors.amber['500'],
        success: colors.green['500'],
        info: colors.indigo['500'],
      },
      fontFamily: {
        mono: ['Illinois', ...defaultTheme.fontFamily.mono],
      },
    },
  },
  plugins: [],
};
