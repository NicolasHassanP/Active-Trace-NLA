// Shared data + Icon for the activia-trace coordinator mockups.
// Exported to window so each Babel script can read it.

const ACT = {
  prof: {
    nombre: 'Prof. Mariana Suárez',
    inicial: 'MS',
    rol: 'Jefa de cátedra · Coordinación',
    regional: 'Regional Córdoba',
    email: 'm.suarez@activia.edu.ar',
  },
  cuatri: '2026 · 1.º cuatrimestre',
  kpis: [
    { label: 'Materias a cargo', value: '4', icon: 'book', sub: '3 vigentes · 1 por vencer' },
    { label: 'Alumnos totales', value: '500', icon: 'users', sub: 'en 11 comisiones' },
    { label: 'Alumnos atrasados', value: '44', icon: 'clock', sub: '8,8% del padrón', alert: true },
    { label: 'Tareas pendientes', value: '5', icon: 'clipboard', sub: '2 vencen esta semana' },
  ],
  materias: [
    { nombre: 'Análisis Matemático I', sigla: 'AM1', carrera: 'Ing. en Sistemas de Información',
      cohorte: '2026 · 1.ºC', rol: 'Coordinador', vig: '01 mar — 15 jul', estado: 'Vigente',
      comisiones: 4, alumnos: 196, docentes: 9, atrasados: 23, avance: 38, regional: 'Córdoba' },
    { nombre: 'Álgebra y Geometría Analítica', sigla: 'AGA', carrera: 'Ing. en Sistemas de Información',
      cohorte: '2026 · 1.ºC', rol: 'Jefe de cátedra', vig: '01 mar — 15 jul', estado: 'Vigente',
      comisiones: 3, alumnos: 142, docentes: 6, atrasados: 11, avance: 42, regional: 'Córdoba' },
    { nombre: 'Programación I', sigla: 'PR1', carrera: 'Tecnicatura en Programación',
      cohorte: '2026 · 1.ºC', rol: 'Profesor titular', vig: '01 mar — 15 jul', estado: 'Vigente',
      comisiones: 2, alumnos: 88, docentes: 4, atrasados: 6, avance: 45, regional: 'Córdoba' },
    { nombre: 'Bases de Datos', sigla: 'BDD', carrera: 'Tecnicatura en Programación',
      cohorte: '2025 · 2.ºC', rol: 'Jefe de cátedra', vig: '08 ago — 12 dic', estado: 'Por vencer',
      comisiones: 2, alumnos: 74, docentes: 3, atrasados: 4, avance: 96, regional: 'Rosario' },
  ],
  nav: [
    { group: 'Académico', items: [
      ['Mis materias', 'book'], ['Calificaciones', 'check'], ['Padrón', 'file'],
      ['Atrasados', 'clock'], ['Seguimiento', 'usercheck'] ] },
    { group: 'Gestión', items: [
      ['Equipos docentes', 'users'], ['Setup cuatrimestre', 'calendar'],
      ['Tareas', 'clipboard'], ['Monitor', 'activity'] ] },
    { group: 'Instancias', items: [ ['Encuentros', 'layers'], ['Coloquios', 'award'] ] },
    { group: 'Comunicación', items: [ ['Avisos', 'bell'], ['Comunicaciones', 'mail'] ] },
    { group: 'Administración', items: [
      ['Usuarios', 'user'], ['Estructura académica', 'sliders'],
      ['Liquidaciones', 'dollar'], ['Auditoría', 'shield'] ] },
  ],
  icons: {
    book: 'M4 19.5A2.5 2.5 0 016.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z',
    check: 'M9 11l3 3L22 4 M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11',
    file: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8',
    clock: 'M12 22a10 10 0 100-20 10 10 0 000 20z M12 6v6l4 2',
    usercheck: 'M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2 M11 7a4 4 0 11-8 0 4 4 0 018 0z M16 11l2 2 4-4',
    users: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75',
    calendar: 'M19 4H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2z M16 2v4 M8 2v4 M3 10h18',
    clipboard: 'M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2 M9 2h6a1 1 0 011 1v2a1 1 0 01-1 1H9a1 1 0 01-1-1V3a1 1 0 011-1z',
    activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
    layers: 'M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5',
    award: 'M12 15a7 7 0 100-14 7 7 0 000 14z M8.21 13.89L7 23l5-3 5 3-1.21-9.12',
    bell: 'M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9z M13.73 21a2 2 0 01-3.46 0',
    mail: 'M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2z M22 6l-10 7L2 6',
    user: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2 M12 11a4 4 0 100-8 4 4 0 000 8z',
    sliders: 'M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6',
    dollar: 'M12 1v22 M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6',
    shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    logout: 'M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4 M16 17l5-5-5-5 M21 12H9',
    search: 'M11 19a8 8 0 100-16 8 8 0 000 16z M21 21l-4.35-4.35',
    plus: 'M12 5v14 M5 12h14',
    chev: 'M9 18l6-6-6-6',
    chevd: 'M6 9l6 6 6-6',
    alert: 'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01',
    chart: 'M3 3v18h18 M7 15l4-5 3 3 5-7',
    arrow: 'M5 12h14 M13 6l6 6-6 6',
    grid: 'M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z',
    filter: 'M22 3H2l8 9.46V19l4 2v-8.54L22 3z',
    dot: 'M12 12m-3 0a3 3 0 106 0 3 3 0 10-6 0',
    x: 'M18 6L6 18 M6 6l12 12',
    download: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4 M7 10l5 5 5-5 M12 15V3',
  },
};

function Icon({ name, size = 18, stroke = 1.7, color = 'currentColor', style }) {
  const d = ACT.icons[name] || '';
  return React.createElement('svg', {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: color, strokeWidth: stroke, strokeLinecap: 'round', strokeLinejoin: 'round',
    style,
  }, d.split(' M').map((seg, i) =>
    React.createElement('path', { key: i, d: (i ? 'M' : '') + seg })));
}

Object.assign(window, { ACT, Icon });
