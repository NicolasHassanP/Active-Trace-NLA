// Prototipo clickable — núcleo: datos, shell interactivo, switcher de rol, toast, modal.
// Reusa el sistema de clases ".a*" (global) de shell-a.jsx y el Icon/ACT de shared.jsx.

(function injectPCss() {
  if (document.getElementById('p-ds')) return;
  const s = document.createElement('style');
  s.id = 'p-ds';
  s.textContent = `
  .pApp{--ink:#1d2330;--mut:#6b7280;--faint:#9aa1ad;--line:#eceef2;--line2:#f3f4f7;--bg:#f7f8fb;
    --ind:#4f46e5;--ind2:#4338ca;--ok:#16a34a;--warn:#e7515a;--amber:#d97706;--vio:#6d28d9;--cyan:#0e7490;
    display:flex;height:100vh;overflow:hidden;background:var(--bg);font-family:'Manrope',system-ui,sans-serif;color:var(--ink);}
  .pApp *{box-sizing:border-box;}
  .pSide{width:252px;flex:0 0 252px;background:#fff;border-right:1px solid var(--line);display:flex;flex-direction:column;padding:18px 14px 14px;height:100vh;}
  .pBrand{display:flex;align-items:center;gap:9px;padding:0 8px 14px;}
  .pLogo{width:30px;height:30px;border-radius:9px;background:linear-gradient(150deg,#6366f1,#4338ca);display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:0 3px 8px rgba(67,56,202,.35);}
  .pBrand b{font-size:16px;font-weight:800;letter-spacing:-.4px;}
  .pBrand b span{color:var(--ind);}
  .pRole{position:relative;margin:0 2px 8px;}
  .pRoleBtn{display:flex;align-items:center;gap:10px;width:100%;padding:9px 11px;border-radius:11px;border:1px solid var(--line);background:#fafbff;cursor:pointer;text-align:left;}
  .pRoleBtn:hover{border-color:#d7dae6;}
  .pRoleAv{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:12px;flex:0 0 auto;}
  .pRoleM{flex:1;min-width:0;}
  .pRoleM .lab{font-size:9.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#9aa1ad;}
  .pRoleM .nm{font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .pMenu{position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border-radius:12px;box-shadow:0 12px 34px rgba(16,24,40,.16),0 0 0 1px rgba(0,0,0,.05);padding:6px;z-index:40;}
  .pMenu .it{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:9px;cursor:pointer;}
  .pMenu .it:hover{background:#f4f4f8;}
  .pMenu .it.on{background:#eef0ff;}
  .pMenuHd{font-size:9.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#9aa1ad;padding:6px 10px 3px;}
  .pNav{flex:1;overflow-y:auto;margin:0 -4px;padding:0 4px;}
  .pUser{display:flex;align-items:center;gap:10px;padding:10px;border-radius:11px;border:1px solid var(--line);margin-top:8px;}
  .pMain{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
  .pBody{flex:1;overflow-y:auto;padding:24px 28px 40px;}
  .pBanner{display:flex;align-items:center;gap:10px;background:#fff7ed;border-bottom:1px solid #fde4c8;color:#9a3412;font-size:12.5px;font-weight:600;padding:8px 28px;}
  /* toast */
  .pToastWrap{position:fixed;bottom:26px;left:50%;transform:translateX(-50%);z-index:120;display:flex;flex-direction:column;gap:9px;align-items:center;}
  .pToast{display:flex;align-items:center;gap:11px;background:#1d2330;color:#fff;font-size:13px;font-weight:600;padding:12px 17px;border-radius:12px;box-shadow:0 12px 34px rgba(0,0,0,.28);animation:pToastIn .25s cubic-bezier(.2,.8,.3,1);}
  .pToast .ic{width:22px;height:22px;border-radius:7px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;}
  @keyframes pToastIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
  /* modal */
  .pOverlay{position:fixed;inset:0;background:rgba(24,28,38,.42);backdrop-filter:blur(3px);z-index:100;display:flex;align-items:center;justify-content:center;padding:30px;animation:pFade .18s ease;}
  @keyframes pFade{from{opacity:0}to{opacity:1}}
  .pModal{background:#fff;border-radius:18px;box-shadow:0 30px 80px rgba(16,24,40,.32);width:100%;max-width:560px;max-height:88vh;overflow:hidden;display:flex;flex-direction:column;animation:pPop .22s cubic-bezier(.2,.8,.3,1);}
  @keyframes pPop{from{opacity:0;transform:scale(.96) translateY(8px)}to{opacity:1;transform:none}}
  .pModalH{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding:20px 22px 14px;border-bottom:1px solid var(--line);}
  .pModalH h3{font-size:17px;font-weight:800;letter-spacing:-.3px;}
  .pModalH p{font-size:12.5px;color:var(--mut);margin:4px 0 0;}
  .pModalB{padding:20px 22px;overflow-y:auto;}
  .pModalF{display:flex;justify-content:flex-end;gap:10px;padding:16px 22px;border-top:1px solid var(--line);background:#fafbfc;}
  .pX{width:32px;height:32px;border-radius:9px;border:1px solid var(--line);background:#fff;display:flex;align-items:center;justify-content:center;color:#6b7280;cursor:pointer;flex:0 0 auto;}
  .pX:hover{background:#f6f7fb;}
  .pClickable{cursor:pointer;}
  .pHL{transition:background .12s,box-shadow .12s,border-color .12s;}
  .pHL:hover{background:#fafbff;}
  `;
  document.head.appendChild(s);
})();

// ── Datos del prototipo ─────────────────────────────────────
const PD = {
  cuatri: '2026 · 1.ºC',
  roles: {
    COORDINADOR: { label: 'Coordinador', nombre: 'Prof. Mariana Suárez', av: 'MS', grad: 'linear-gradient(150deg,#818cf8,#4338ca)', sub: 'Coordinación · Cátedra', home: 'materias' },
    PROFESOR: { label: 'Profesor', nombre: 'Dra. Sofía Ledesma', av: 'SL', grad: 'linear-gradient(150deg,#34d399,#0a9488)', sub: 'Análisis Matemático I', home: 'materias' },
    ALUMNO: { label: 'Alumno', nombre: 'Joaquín Sosa', av: 'JS', grad: 'linear-gradient(150deg,#fbbf24,#d97706)', sub: 'Ing. en Sistemas · 1.ºC', home: 'estado' },
    ADMIN: { label: 'Administrador', nombre: 'Lucía Ferrer', av: 'LF', grad: 'linear-gradient(150deg,#f472b6,#be185d)', sub: 'Administración del tenant', home: 'estructura' },
    FINANZAS: { label: 'Finanzas', nombre: 'Roberto Díaz', av: 'RD', grad: 'linear-gradient(150deg,#34d399,#047857)', sub: 'Liquidaciones y honorarios', home: 'liquid' },
  },
  // Alumnos para planillas / atrasados / seguimiento (comisiones de AM1)
  alumnos: [
    { n: 'Martina Ríos', i: 'MR', leg: '45.118', mail: 'm.rios', com: '1A', reg: 'Córdoba', p1: 9, p2: 8, tp: 'Aprob.', cond: 'Promociona', cum: 12, tot: 12, dias: 0, ult: 'ayer', est: 'Al día' },
    { n: 'Lucas Giménez', i: 'LG', leg: '45.231', mail: 'l.gimenez', com: '1A', reg: 'Córdoba', p1: 7, p2: 6, tp: 'Aprob.', cond: 'Regular', cum: 9, tot: 12, dias: 0, ult: 'hoy', est: 'Al día' },
    { n: 'Joaquín Sosa', i: 'JS', leg: '45.402', mail: 'j.sosa', com: '1A', reg: 'Córdoba', p1: 4, p2: null, tp: 'Pend.', cond: 'Riesgo', cum: 5, tot: 12, dias: 9, ult: 'hace 9 d', est: 'Atrasado' },
    { n: 'Julieta Cabrera', i: 'JC', leg: '45.815', mail: 'j.cabrera', com: '1A', reg: 'Córdoba', p1: 6, p2: 4, tp: 'Aprob.', cond: 'Regular', cum: 7, tot: 12, dias: 6, ult: 'hace 6 d', est: 'Atrasado' },
    { n: 'Camila Ferrari', i: 'CF', leg: '45.087', mail: 'c.ferrari', com: '1B', reg: 'Córdoba', p1: 6, p2: 7, tp: 'Aprob.', cond: 'Regular', cum: 10, tot: 12, dias: 0, ult: 'hoy', est: 'Al día' },
    { n: 'Tomás Herrera', i: 'TH', leg: '45.560', mail: 't.herrera', com: '1B', reg: 'Córdoba', p1: 3, p2: 5, tp: 'Pend.', cond: 'Riesgo', cum: 4, tot: 12, dias: 14, ult: 'hace 14 d', est: 'En riesgo' },
    { n: 'Sofía Molina', i: 'SM', leg: '45.299', mail: 's.molina', com: '1B', reg: 'Córdoba', p1: 8, p2: 9, tp: 'Aprob.', cond: 'Promociona', cum: 11, tot: 12, dias: 0, ult: 'hoy', est: 'Al día' },
    { n: 'Valentina Páez', i: 'VP', leg: '45.733', mail: 'v.paez', com: '2A', reg: 'Rosario', p1: 2, p2: null, tp: 'Pend.', cond: 'Riesgo', cum: 3, tot: 12, dias: 21, ult: 'hace 21 d', est: 'En riesgo' },
  ],
  // Materias del PROFESOR (sus comisiones)
  materiasProf: [
    { nombre: 'Análisis Matemático I', sigla: 'AM1', carrera: 'Ing. en Sistemas de Información', com: '1A', cohorte: '2026 · 1.ºC', rol: 'Profesora titular', alumnos: 48, atrasados: 4, avance: 38, importado: false },
    { nombre: 'Análisis Matemático I', sigla: 'AM1', carrera: 'Ing. en Sistemas de Información', com: '1B', cohorte: '2026 · 1.ºC', rol: 'Profesora titular', alumnos: 48, atrasados: 3, avance: 41, importado: false },
    { nombre: 'Análisis Matemático I', sigla: 'AM1', carrera: 'Ing. en Sistemas de Información', com: '2A', cohorte: '2026 · 1.ºC', rol: 'Profesora titular', alumnos: 52, atrasados: 6, avance: 35, importado: false },
  ],
  // Materias del ALUMNO
  alumnoMaterias: [
    { nombre: 'Análisis Matemático I', sigla: 'AM1', com: '1A', cond: 'Regular', p1: 4, p2: null, cum: 5, tot: 12, prox: 'Parcial 2 · 12 abr', alerta: 'Parcial 2 pendiente' },
    { nombre: 'Álgebra y Geometría Analítica', sigla: 'AGA', com: '1A', cond: 'Promociona', p1: 8, p2: 9, cum: 11, tot: 12, prox: 'Coloquio · 18 mar', alerta: null },
    { nombre: 'Programación I', sigla: 'PR1', com: '1A', cond: 'Regular', p1: 7, p2: 6, cum: 9, tot: 12, prox: 'TP4 · 15 abr', alerta: null },
    { nombre: 'Física I', sigla: 'FIS', com: '1A', cond: 'Riesgo', p1: 3, p2: null, cum: 3, tot: 12, prox: 'Recuperatorio · 20 abr', alerta: '2 entregas faltantes' },
  ],
  // Convocatorias de coloquio
  coloquios: [
    { mesa: 'Mesa de Marzo', m: 'AM1 · Análisis Matemático I', sigla: 'AM1', insc: 24, res: 21, cupos: 30, est: 'Abierta',
      turnos: [{ dia: 'Lun 18 mar', hora: '09:00', libres: 4 }, { dia: 'Lun 18 mar', hora: '11:00', libres: 0 }, { dia: 'Mar 19 mar', hora: '09:00', libres: 6 }, { dia: 'Mar 19 mar', hora: '14:00', libres: 2 }] },
    { mesa: 'Mesa de Marzo', m: 'AGA · Álgebra y Geom. Analítica', sigla: 'AGA', insc: 18, res: 16, cupos: 24, est: 'Abierta',
      turnos: [{ dia: 'Mié 20 mar', hora: '10:00', libres: 3 }, { dia: 'Jue 21 mar', hora: '09:00', libres: 5 }] },
  ],
  // Avisos (para alumno / lectura)
  avisos: [
    { t: 'Cambio de fecha: Parcial 2 de Análisis Matemático I', cuerpo: 'El segundo parcial se reprograma para el 12 de abril a las 9:00 h en el aula 204. Por favor confirmá la lectura de este aviso.', de: 'Coordinación', f: 'hace 1 día', sev: 'Advertencia', ack: true },
    { t: 'Inicio del cuatrimestre 2026 · 1.ºC', cuerpo: '¡Bienvenidos al nuevo cuatrimestre! Revisá el cronograma de cursada y las fechas de evaluación en la sección correspondiente.', de: 'Secretaría académica', f: 'hace 2 semanas', sev: 'Info', ack: false },
  ],
  // Cola de comunicaciones (para aprobación del coordinador)
  cola: [
    { id: 'L-018', prof: 'Dra. Sofía Ledesma', av: 'SL', materia: 'AM1 · Com. 1A', dest: 2, asunto: 'Recordatorio de Parcial 1', est: 'Pendiente' },
    { id: 'L-017', prof: 'Lic. Bruno Paredes', av: 'BP', materia: 'PR1 · Com. 1A', dest: 14, asunto: 'Entrega TP3 vencida', est: 'Pendiente' },
    { id: 'L-016', prof: 'Dra. Sofía Ledesma', av: 'SL', materia: 'AM1 · Com. 2A', dest: 6, asunto: 'Citación a consulta', est: 'Enviado' },
  ],
};

// Navegación por rol → [label, icono, viewId]
const NAV = {
  COORDINADOR: [
    { group: 'Académico', items: [['Mis materias', 'book', 'materias'], ['Calificaciones', 'check', 'calif'], ['Padrón', 'file', 'padron'], ['Atrasados', 'clock', 'atrasados'], ['Seguimiento', 'usercheck', 'segui'], ['Monitor', 'activity', 'monitor']] },
    { group: 'Gestión', items: [['Equipos docentes', 'users', 'equipos'], ['Setup cuatrimestre', 'calendar', 'setup'], ['Tareas', 'clipboard', 'tareas']] },
    { group: 'Instancias', items: [['Encuentros', 'layers', 'encuentros'], ['Coloquios', 'award', 'coloquios']] },
    { group: 'Comunicación', items: [['Avisos', 'bell', 'avisos'], ['Comunicaciones', 'mail', 'comuni'], ['Aprobaciones', 'check', 'aprob'], ['Mensajes', 'mail', 'inbox']] },
    { group: 'Sistema', items: [['Auditoría', 'shield', 'auditoria']] },
  ],
  PROFESOR: [
    { group: 'Mi cátedra', items: [['Mis materias', 'book', 'materias'], ['Calificaciones', 'check', 'calif'], ['Atrasados', 'clock', 'atrasados'], ['Sin corregir', 'file', 'sincorregir'], ['Seguimiento', 'usercheck', 'segui']] },
    { group: 'Instancias', items: [['Encuentros', 'layers', 'encuentros'], ['Coloquios', 'award', 'coloquios'], ['Guardias', 'clock', 'guardias']] },
    { group: 'Trabajo', items: [['Tareas', 'clipboard', 'tareas'], ['Comunicaciones', 'mail', 'comuni'], ['Mensajes', 'mail', 'inbox']] },
  ],
  ALUMNO: [
    { group: 'Mi cursada', items: [['Mi estado', 'activity', 'estado'], ['Mis materias', 'book', 'materias'], ['Coloquios', 'award', 'coloquios'], ['Avisos', 'bell', 'avisos'], ['Mensajes', 'mail', 'inbox']] },
  ],
  ADMIN: [
    { group: 'Estructura académica', items: [['Estructura', 'sliders', 'estructura'], ['Fechas de evaluación', 'calendar', 'fechas'], ['Programas', 'file', 'programas']] },
    { group: 'Personas', items: [['Usuarios', 'user', 'usuarios']] },
    { group: 'Operación', items: [['Monitor', 'activity', 'monitor'], ['Avisos', 'bell', 'avisos'], ['Tareas', 'clipboard', 'tareas']] },
    { group: 'Sistema', items: [['Auditoría', 'shield', 'auditoria'], ['Configuración', 'sliders', 'config'], ['Mensajes', 'mail', 'inbox']] },
  ],
  FINANZAS: [
    { group: 'Liquidaciones', items: [['Liquidaciones', 'dollar', 'liquid'], ['Historial', 'clock', 'histliq']] },
    { group: 'Configuración', items: [['Grilla salarial', 'sliders', 'grilla'], ['Facturas', 'file', 'facturas']] },
    { group: 'Sistema', items: [['Auditoría', 'shield', 'auditoria'], ['Mensajes', 'mail', 'inbox']] },
  ],
};

// ── Shell interactivo ───────────────────────────────────────
function Shell({ role, view, setView, setRole, toast, children }) {
  const [open, setOpen] = React.useState(false);
  const r = PD.roles[role];
  const nav = NAV[role];
  const labelOf = () => { for (const g of nav) for (const it of g.items) if (it[2] === view) return it[0]; return ''; };
  return (
    <div className="pApp">
      <aside className="pSide">
        <div className="pBrand">
          <div className="pLogo"><Icon name="activity" size={17} color="#fff" stroke={2.2} /></div>
          <b>activia<span>·</span>trace</b>
        </div>
        <div className="pRole">
          <button className="pRoleBtn" onClick={() => setOpen((o) => !o)}>
            <div className="pRoleAv" style={{ background: r.grad }}>{r.av}</div>
            <div className="pRoleM"><div className="lab">Viendo como</div><div className="nm">{r.label}</div></div>
            <Icon name="chevd" size={15} color="#9aa1ad" />
          </button>
          {open && (
            <div className="pMenu">
              <div className="pMenuHd">Cambiar de rol (demo)</div>
              {Object.keys(PD.roles).map((k) => (
                <div key={k} className={'it' + (k === role ? ' on' : '')} onClick={() => { setOpen(false); if (k !== role) { setRole(k); setView(PD.roles[k].home); } }}>
                  <div className="pRoleAv" style={{ background: PD.roles[k].grad, width: 26, height: 26, fontSize: 11 }}>{PD.roles[k].av}</div>
                  <div style={{ flex: 1 }}><div style={{ fontSize: 13, fontWeight: 700 }}>{PD.roles[k].label}</div><div style={{ fontSize: 11, color: '#9aa1ad' }}>{PD.roles[k].nombre}</div></div>
                  {k === role && <Icon name="check" size={15} color="#4f46e5" stroke={2.4} />}
                </div>
              ))}
            </div>
          )}
        </div>
        <nav className="pNav">
          {nav.map((g) => (
            <div key={g.group}>
              <div className="aGrp">{g.group}</div>
              {g.items.map(([label, ic, vid]) => (
                <div key={vid} className={'aItem' + (vid === view ? ' on' : '')} onClick={() => setView(vid)}>
                  <Icon name={ic} size={17} /> {label}
                </div>
              ))}
            </div>
          ))}
        </nav>
        <div className="pUser">
          <div className="aAv" style={{ background: r.grad }}>{r.av}</div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.nombre}</div>
            <div style={{ fontSize: 11, color: '#9aa1ad', whiteSpace: 'nowrap' }}>{r.sub}</div>
          </div>
          <div className="aIco" style={{ width: 30, height: 30 }} title="Cerrar sesión" onClick={() => setRole('__logout')}><Icon name="logout" size={15} /></div>
        </div>
      </aside>
      <div className="pMain">
        <header className="aTop">
          <div className="aPill"><Icon name="calendar" size={14} /> {PD.cuatri}</div>
          <div className="aSearch"><Icon name="search" size={16} /> Buscar…</div>
          <div style={{ flex: 1 }} />
          <div className="aIco" onClick={() => toast('No hay notificaciones nuevas', 'bell')}><Icon name="bell" size={17} /><span className="aNdot" /></div>
          <div className="aIco" onClick={() => setView('inbox')}><Icon name="mail" size={17} /></div>
        </header>
        <div className="pBody" key={role + view}>{children}</div>
      </div>
    </div>
  );
}

// ── Modal genérico ──────────────────────────────────────────
function Modal({ title, sub, onClose, children, footer, max }) {
  return (
    <div className="pOverlay" onClick={onClose}>
      <div className="pModal" style={max ? { maxWidth: max } : null} onClick={(e) => e.stopPropagation()}>
        <div className="pModalH">
          <div><h3>{title}</h3>{sub && <p>{sub}</p>}</div>
          <div className="pX" onClick={onClose}><Icon name="x" size={16} /></div>
        </div>
        <div className="pModalB">{children}</div>
        {footer && <div className="pModalF">{footer}</div>}
      </div>
    </div>
  );
}

Object.assign(window, { PD, NAV, Shell, Modal });
