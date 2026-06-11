/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink:     '#1d2330',
        mut:     '#6b7280',
        faint:   '#9aa1ad',
        line:    '#eceef2',
        line2:   '#f3f4f7',
        bg:      '#f7f8fb',
        ind:     '#4f46e5',
        ind2:    '#4338ca',
        indBg:   '#eef0ff',
        ok:      '#16a34a',
        okBg:    '#ecfdf3',
        warn:    '#e7515a',
        warnBg:  '#fff1f0',
        amber2:  '#d97706',
        amberBg: '#fef6e7',
        vio:     '#6d28d9',
        vioBg:   '#f3eefe',
      },
      fontFamily: {
        sans: ["'Manrope'", 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        btn:  '10px',
        tag:  '7px',
      },
      boxShadow: {
        card:         '0 1px 2px rgba(16,24,40,.04)',
        'card-hover': '0 8px 26px rgba(16,24,40,.09)',
        modal:        '0 30px 80px rgba(16,24,40,.32)',
      },
      keyframes: {
        'bell-ring': {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '15%':      { transform: 'rotate(16deg)' },
          '30%':      { transform: 'rotate(-13deg)' },
          '45%':      { transform: 'rotate(10deg)' },
          '60%':      { transform: 'rotate(-7deg)' },
          '75%':      { transform: 'rotate(5deg)' },
          '90%':      { transform: 'rotate(-3deg)' },
        },
      },
      animation: {
        'bell-ring': 'bell-ring 0.65s ease-in-out',
      },
    },
  },
  plugins: [],
}
