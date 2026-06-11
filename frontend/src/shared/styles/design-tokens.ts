// design-tokens.ts — activia-trace Design System
// Fuente: design handoff Claude Design v1 (2026-06-06)
// Usar como referencia para clases Tailwind y valores inline cuando no haya clase equivalente.

export const colors = {
  // Texto
  ink:   '#1d2330',
  mut:   '#6b7280',
  faint: '#9aa1ad',

  // Bordes y fondos
  line:  '#eceef2',
  line2: '#f3f4f7',
  bg:    '#f7f8fb',

  // Acento primario (índigo)
  ind:   '#4f46e5',
  ind2:  '#4338ca',
  indBg: '#eef0ff',

  // Semánticos
  ok:      '#16a34a',
  okBg:    '#ecfdf3',
  warn:    '#e7515a',
  warnBg:  '#fff1f0',
  amber:   '#d97706',
  amberBg: '#fef6e7',
  vio:     '#6d28d9',
  vioBg:   '#f3eefe',
  cyan:    '#0e7490',
  cyanBg:  '#ecfeff',
} as const;

export const typography = {
  family: "'Manrope', system-ui, sans-serif",
  h1:      { size: '22px', weight: 800, letterSpacing: '-0.6px' },
  h2:      { size: '16px', weight: 800, letterSpacing: '-0.3px' },
  h3card:  { size: '14.5px', weight: 800 },
  body:    { size: '13px', weight: 400 },
  label:   { size: '11.5px', weight: 700 },
  micro:   { size: '10.5px', weight: 700, letterSpacing: '0.4px' },
  badge:   { size: '11px', weight: 700 },
} as const;

export const spacing = {
  pagePaddingTop: '24px',
  pagePaddingX:   '28px',
  cardGap:        '14px',
  cardPadding:    '18px',
  tableRowY:      '11px',
} as const;

export const radii = {
  page:     '16px',
  card:     '16px',
  btn:      '10px',
  btnSm:    '9px',
  badge:    '999px',
  tag:      '7px',
  avatar:   '50%',
  avatarSq: '10px',
} as const;

export const shadows = {
  card:    '0 1px 2px rgba(16,24,40,.04)',
  cardHov: '0 8px 26px rgba(16,24,40,.09)',
  modal:   '0 30px 80px rgba(16,24,40,.32)',
  toast:   '0 12px 34px rgba(0,0,0,.28)',
  logoPri: '0 3px 8px rgba(67,56,202,.35)',
} as const;

export const roleGradients: Record<string, string> = {
  COORDINADOR: 'linear-gradient(150deg, #818cf8, #4338ca)',
  PROFESOR:    'linear-gradient(150deg, #34d399, #0a9488)',
  ALUMNO:      'linear-gradient(150deg, #fbbf24, #d97706)',
  ADMIN:       'linear-gradient(150deg, #f472b6, #be185d)',
  FINANZAS:    'linear-gradient(150deg, #34d399, #047857)',
};
