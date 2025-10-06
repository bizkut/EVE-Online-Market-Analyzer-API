import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0d1117',
        panel: '#161b22',
        accent: '#00b0ff',
        'profit-positive': '#10b981',
        'profit-negative': '#ef4444',
        'neutral-text': '#c9d1d9',
      },
      fontFamily: {
        sans: ['var(--font-inter)'],
        orbitron: ['var(--font-orbitron)'],
      },
    },
  },
  plugins: [],
};
export default config;