// Vistas académicas (content-only, role-aware). Incluye el flujo estrella del PROFESOR.
const { useState } = React;

function ContextBar({ extra }) {
  return (
    <div className="aCard" style={{ padding: '16px 18px', marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 13 }}>
        <h3 style={{ fontSize: 13.5, fontWeight: 800 }}>Materia, cohorte y comisión</h3>
        <span className="aToggleLink"><Icon name="file" size={13} /> ¿Preferís pegar IDs?</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: 12 }}>
        <Combo label="Materia" av="AM1" name="Análisis Matemático I" id="m-0c4f…a91" act />
        <Combo label="Cohorte" av="26·1" name="2026 · 1.ºC" id="coh-2026-1" small />
        <Combo label="Comisión" av="1A" name="Comisión 1A" id="com-1a" small />
      </div>
      {extra}
    </div>
  );
}

const condCol = (c) => c === 'Promociona' ? ['#16a34a', '#ecfdf3'] : c === 'Regular' ? ['#4338ca', '#eef0ff'] : c === 'Riesgo' ? ['#e7515a', '#fff1f0'] : ['#6b7280', '#f1f2f5'];
const estCol = (e) => e === 'Al día' ? ['#16a34a', '#ecfdf3'] : e === 'Atrasado' ? ['#d97706', '#fef6e7'] : ['#e7515a', '#fff1f0'];
function Av({ a }) { return <span className="aAvSm">{a.i}</span>; }
function Score({ v }) {
  if (v == null) return <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 34, height: 28, border: '1.5px dashed #d8dbe4', borderRadius: 7, color: '#c2c7d2', fontSize: 12 }}>—</span>;
  const col = v >= 6 ? '#16a34a' : v >= 4 ? '#d97706' : '#e7515a';
  return <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 34, height: 28, background: '#f7f8fb', border: '1px solid #eceef2', borderRadius: 7, color: col, fontWeight: 800, fontSize: 13 }}>{v}</span>;
}

// ── Mis materias (coordinador / profesor) ───────────────────
function VMaterias({ ctx }) {
  if (ctx.role === 'PROFESOR') {
    return (
      <>
        <PageHead title="Mis comisiones" sub="Tus asignaciones vigentes este cuatrimestre. Entrá a una para gestionar sus calificaciones." />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
          {PD.materiasProf.map((m) => (
            <div key={m.com} className="aCard pHL" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 46, height: 46, borderRadius: 12, background: 'linear-gradient(150deg,#eafaf8,#d4f3ee)', color: '#0a9488', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>{m.com}</div>
                <div><div style={{ fontSize: 15, fontWeight: 800, letterSpacing: '-.3px' }}>{m.nombre}</div><div style={{ fontSize: 12, color: '#6b7280' }}>Comisión {m.com} · {m.alumnos} alumnos</div></div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span className="aTag"><Icon name="calendar" size={12} /> {m.cohorte}</span>
                <span className="aTag" style={{ color: '#e7515a' }}><Icon name="clock" size={12} /> {m.atrasados} atrasados</span>
              </div>
              <div><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: '#6b7280', fontWeight: 600, marginBottom: 6 }}><span>Avance</span><span>{m.avance}%</span></div><div className="aBar"><div className="aBarF" style={{ width: m.avance + '%' }} /></div></div>
              <div style={{ display: 'flex', gap: 8, borderTop: '1px solid var(--line)', paddingTop: 13 }}>
                <button className="aBtn pri sm" style={{ flex: 1 }} onClick={() => ctx.setView('calif')}><Icon name="check" size={14} color="#fff" /> Calificar</button>
                <button className="aBtn sm" style={{ flex: 1 }} onClick={() => ctx.setView('atrasados')}><Icon name="clock" size={14} /> Atrasados</button>
              </div>
            </div>
          ))}
        </div>
      </>
    );
  }
  // Coordinador
  const rolColor = (r) => r === 'Coordinador' ? '#6d28d9' : r === 'Jefe de cátedra' ? '#4338ca' : '#0e7490';
  const rolBg = (r) => r === 'Coordinador' ? '#f3eefe' : r === 'Jefe de cátedra' ? '#eef0ff' : '#ecfeff';
  const kpis = ACT.kpis, mats = ACT.materias;
  const chipKind = ['', 'warn', 'amber', 'vio'];
  return (
    <>
      <div style={{ fontSize: 23, fontWeight: 800, letterSpacing: '-.6px' }}>Hola, Mariana 👋</div>
      <div style={{ color: '#6b7280', fontSize: 13.5, margin: '3px 0 20px' }}>Tenés <b>4 materias</b> a tu cargo este cuatrimestre · Regional Córdoba</div>
      <div className="aKpis" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {kpis.map((k, i) => (
          <div key={k.label} className="aKpi pHL pClickable" onClick={() => ctx.setView(i === 2 ? 'atrasados' : i === 3 ? 'tareas' : 'monitor')}>
            <div className={'aChip ' + chipKind[i]}><Icon name={k.icon} size={18} /></div>
            <div className="aKv" style={k.alert ? { color: '#e7515a' } : null}>{k.value}</div>
            <div className="aKl">{k.label}</div><div className="aKs">{k.sub}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <h2 style={{ fontSize: 16, fontWeight: 800 }}>Mis materias</h2>
        <div className="aTabs"><span className="aTab on">Todas</span><span className="aTab">Vigentes</span><span className="aTab">Por vencer</span></div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {mats.map((m) => (
          <div key={m.nombre} className="aCard pHL" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 13 }}>
              <div style={{ width: 46, height: 46, borderRadius: 12, background: 'linear-gradient(150deg,#eef0ff,#e7e9ff)', color: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, flex: '0 0 auto' }}>{m.sigla}</div>
              <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 15.5, fontWeight: 800, letterSpacing: '-.3px' }}>{m.nombre}</div><div style={{ fontSize: 12.5, color: '#6b7280', marginTop: 3 }}>{m.carrera}</div></div>
              <Badge color={rolColor(m.rol)} bg={rolBg(m.rol)}>{m.rol}</Badge>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span className="aTag"><Icon name="calendar" size={12} /> {m.cohorte}</span>{estChip(m.estado)}<span className="aTag">{m.vig}</span>
            </div>
            <div style={{ display: 'flex', gap: 18 }}>
              {[['alumnos', m.alumnos], ['comisiones', m.comisiones], ['docentes', m.docentes], ['atrasados', m.atrasados]].map(([l, v], j) => (
                <div key={l}><b style={{ fontSize: 17, fontWeight: 800, color: j === 3 ? '#e7515a' : '#1d2330' }}>{v}</b><span style={{ fontSize: 11, color: '#6b7280', fontWeight: 600, display: 'block' }}>{l}</span></div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, borderTop: '1px solid var(--line)', paddingTop: 13 }}>
              <button className="aBtn pri sm" style={{ flex: 1 }} onClick={() => ctx.setView('padron')}><Icon name="file" size={14} color="#fff" /> Padrón</button>
              <button className="aBtn sm" style={{ flex: 1 }} onClick={() => ctx.setView('calif')}><Icon name="check" size={14} /> Calificar</button>
              <button className="aBtn sm" style={{ flex: 1 }} onClick={() => ctx.setView('equipos')}><Icon name="users" size={14} /> Equipo</button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

// ── Calificaciones · flujo importar → analizar (FL-02) ──────
const ACTIVIDADES = [
  ['Parcial 1', 'Numérica', true], ['Parcial 2', 'Numérica', true], ['TP Integrador', 'Textual', true],
  ['Quiz Unidad 1', 'Numérica', false], ['Quiz Unidad 2', 'Numérica', false], ['Recuperatorio P1', 'Numérica', false],
];
function VCalif({ ctx }) {
  const [step, setStep] = useState('importar');
  const [sel, setSel] = useState(() => ACTIVIDADES.map((a) => a[2]));
  const [umbral, setUmbral] = useState(60);
  const rows = PD.alumnos.filter((a) => a.com === '1A' || a.com === '1B');

  const head = (
    <PageHead title="Calificaciones" sub="Importá las notas exportadas del LMS y analizá el estado de la comisión.">
      {step === 'listo' && <><Btn icon="download">Exportar</Btn><Btn pri icon="check">Guardar</Btn></>}
    </PageHead>
  );

  if (step === 'importar') return (
    <>{head}<ContextBar />
      <div className="aCard" style={{ padding: 22 }}>
        <div style={{ border: '2px dashed #d4d8e4', borderRadius: 14, padding: '34px 18px', textAlign: 'center', background: '#fafbff' }}>
          <div style={{ width: 50, height: 50, borderRadius: 13, background: '#eef0ff', color: '#4f46e5', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 13 }}><Icon name="download" size={24} /></div>
          <div style={{ fontSize: 15, fontWeight: 800 }}>Importá las calificaciones del LMS</div>
          <div style={{ fontSize: 12.5, color: '#6b7280', margin: '5px 0 16px' }}>Arrastrá el archivo exportado de Moodle (.xlsx / .csv) o sincronizá por Web Services.</div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
            <button className="aBtn pri" onClick={() => setStep('preview')}><Icon name="download" size={15} color="#fff" /> Simular importación</button>
            <button className="aBtn" onClick={() => setStep('preview')}><Icon name="activity" size={15} /> Sincronizar con LMS</button>
          </div>
          <div style={{ fontSize: 11.5, color: '#9aa1ad', marginTop: 14 }}>Las columnas que terminan en <b>(Real)</b> se interpretan como nota numérica (RN-01).</div>
        </div>
      </div>
    </>
  );

  if (step === 'preview') {
    const nSel = sel.filter(Boolean).length;
    return (
      <>{head}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, fontSize: 13, color: '#16a34a', fontWeight: 600 }}>
          <Icon name="check" size={16} color="#16a34a" /> Archivo procesado: <b>am1_1A_2026.xlsx</b> · 96 alumnos · 6 actividades detectadas
        </div>
        <div className="aCard" style={{ marginBottom: 16 }}>
          <div className="aCardH"><h3><Icon name="check" size={16} color="#4f46e5" /> Actividades detectadas</h3><span className="aHelp">Elegí cuáles incluir en el análisis</span></div>
          <div style={{ padding: 8 }}>
            {ACTIVIDADES.map((a, i) => (
              <div key={a[0]} className="pHL" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px', borderRadius: 10, cursor: 'pointer' }} onClick={() => setSel((s) => s.map((v, j) => j === i ? !v : v))}>
                <Check on={sel[i]} />
                <div style={{ flex: 1 }}><div style={{ fontSize: 13.5, fontWeight: 700 }}>{a[0]}</div></div>
                <span className="aTag" style={a[1] === 'Textual' ? { color: '#0e7490', background: '#ecfeff', borderColor: 'transparent' } : null}>Escala {a[1].toLowerCase()}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="aCard" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <div style={{ fontSize: 13.5, fontWeight: 800, marginBottom: 3 }}>Umbral de aprobación</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Por debajo de este porcentaje, un alumno cuenta como atrasado (RN-03).</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14 }}>
                <input type="range" min="40" max="80" value={umbral} onChange={(e) => setUmbral(+e.target.value)} style={{ flex: 1, accentColor: '#4f46e5' }} />
                <div style={{ fontSize: 22, fontWeight: 800, color: '#4338ca', minWidth: 56, textAlign: 'right' }}>{umbral}%</div>
              </div>
            </div>
            <button className="aBtn pri" onClick={() => setStep('listo')} style={{ alignSelf: 'flex-end', padding: '11px 18px' }}><Icon name="activity" size={15} color="#fff" /> Analizar {nSel} actividades</button>
          </div>
        </div>
      </>
    );
  }

  // listo
  const atras = rows.filter((a) => a.dias > 0).length;
  return (
    <>{head}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        {[['Promedio', '6,4', ''], ['Aprobados', '7 / ' + rows.length, 'ok'], ['Atrasados', atras, 'warn'], ['Umbral', umbral + '%', '']].map(([l, v, k]) => (
          <div key={l} className="aCard" style={{ flex: 1, padding: '12px 15px' }}>
            <div style={{ fontSize: 11.5, color: '#6b7280', fontWeight: 600 }}>{l}</div>
            <div style={{ fontSize: 20, fontWeight: 800, marginTop: 3, color: k === 'warn' ? '#e7515a' : k === 'ok' ? '#16a34a' : '#1d2330' }}>{v}</div>
          </div>
        ))}
      </div>
      <div className="aCard">
        <div className="aCardH">
          <h3><Icon name="check" size={16} color="#4f46e5" /> Planilla · Comisión 1A–1B <span className="aCount">{rows.length} alumnos</span></h3>
          <button className="aBtn sm" onClick={() => setStep('importar')}><Icon name="download" size={13} /> Volver a importar</button>
        </div>
        <table className="aTbl">
          <thead><tr><th>Alumno</th><th>Legajo</th><th style={{ textAlign: 'center' }}>Parcial 1</th><th style={{ textAlign: 'center' }}>Parcial 2</th><th style={{ textAlign: 'center' }}>TP Int.</th><th>Condición</th></tr></thead>
          <tbody>
            {rows.map((a) => { const [c, b] = condCol(a.cond); return (
              <tr key={a.leg}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Av a={a} /><span className="aTblName">{a.n}</span></div></td>
                <td className="num" style={{ color: '#6b7280' }}>{a.leg}</td>
                <td style={{ textAlign: 'center' }}><Score v={a.p1} /></td>
                <td style={{ textAlign: 'center' }}><Score v={a.p2} /></td>
                <td style={{ textAlign: 'center', color: '#52596a', fontWeight: 600 }}>{a.tp}</td>
                <td><Badge color={c} bg={b}>{a.cond}</Badge></td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16, background: '#fff7ed', border: '1px solid #fde4c8', borderRadius: 12, padding: '13px 16px' }}>
        <Icon name="alert" size={18} color="#d97706" />
        <div style={{ flex: 1, fontSize: 13, color: '#9a3412' }}><b>{atras} alumnos atrasados</b> detectados con el umbral del {umbral}%. Podés comunicarles un recordatorio.</div>
        <button className="aBtn pri sm" onClick={() => ctx.setView('atrasados')}>Ver atrasados <Icon name="arrow" size={14} color="#fff" /></button>
      </div>
    </>
  );
}

// ── Atrasados · seleccionar y comunicar ─────────────────────
function VAtrasados({ ctx }) {
  const rows = PD.alumnos.filter((a) => a.dias > 0);
  const [sel, setSel] = useState({});
  const [composer, setComposer] = useState(false);
  const [preview, setPreview] = useState(false);
  const n = Object.values(sel).filter(Boolean).length;
  const toggle = (k) => setSel((s) => ({ ...s, [k]: !s[k] }));
  const allOn = n === rows.length;
  const encolar = () => {
    setComposer(false); setPreview(false); setSel({});
    ctx.toast(`${n} mensaje${n > 1 ? 's' : ''} encolado${n > 1 ? 's' : ''} · pendiente${n > 1 ? 's' : ''} de aprobación`, 'mail');
  };
  return (
    <>
      <PageHead title="Alumnos atrasados" sub="Alumnos con actividades sin cumplir o nota bajo el umbral. Seleccioná y comunicá.">
        <button className="aBtn pri" disabled={n === 0} style={n === 0 ? { opacity: .5, cursor: 'not-allowed' } : null} onClick={() => n && setComposer(true)}>
          <Icon name="mail" size={15} color="#fff" /> Comunicar a {n} seleccionado{n !== 1 ? 's' : ''}
        </button>
      </PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="clock" size={16} color="#e7515a" /> Atrasados <span className="aCount">{rows.length}</span></h3>
          <div className="aTabs"><span className="aTab on">Todas</span><span className="aTab">Com. 1A</span><span className="aTab">Com. 1B</span><span className="aTab">Com. 2A</span></div>
        </div>
        <table className="aTbl">
          <thead><tr>
            <th style={{ width: 36 }}><span onClick={() => setSel(allOn ? {} : Object.fromEntries(rows.map((r) => [r.leg, true])))} style={{ cursor: 'pointer', display: 'inline-block' }}><Check on={allOn} /></span></th>
            <th>Alumno</th><th>Comisión</th><th>Actividad pendiente</th><th style={{ textAlign: 'center' }}>Días</th><th>Cumplidas</th><th>Último acceso</th>
          </tr></thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.leg} className="pClickable" onClick={() => toggle(a.leg)} style={sel[a.leg] ? { background: '#f5f6ff' } : null}>
                <td><Check on={!!sel[a.leg]} /></td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Av a={a} /><div><div className="aTblName">{a.n}</div><div style={{ fontSize: 11, color: '#9aa1ad' }}>{a.leg}</div></div></div></td>
                <td><span className="aTag">Com. {a.com}</span></td>
                <td style={{ color: '#52596a' }}>{a.p2 == null ? 'Parcial 2' : a.tp === 'Pend.' ? 'TP Integrador' : 'Recuperatorio'}</td>
                <td style={{ textAlign: 'center' }}><Badge color="#e7515a" bg="#fff1f0">{a.dias} d</Badge></td>
                <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span className="aBarMini"><span className="aBarF" style={{ display: 'block', height: '100%', width: (a.cum / a.tot * 100) + '%' }} /></span><span className="num" style={{ fontSize: 12 }}>{a.cum}/{a.tot}</span></span></td>
                <td style={{ color: '#6b7280' }}>{a.ult}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {composer && (
        <Modal title="Comunicar a alumnos atrasados" sub={`${n} destinatario${n !== 1 ? 's' : ''} · se enviará personalizado por alumno`} max={620}
          onClose={() => { setComposer(false); setPreview(false); }}
          footer={<>
            <button className="aBtn" onClick={() => setPreview((p) => !p)}><Icon name="search" size={14} /> {preview ? 'Editar' : 'Vista previa'}</button>
            <button className="aBtn pri" onClick={encolar}><Icon name="mail" size={14} color="#fff" /> Encolar envío</button>
          </>}>
          {!preview ? (
            <>
              <div className="aField" style={{ marginBottom: 14 }}><span className="aLabel">Asunto</span><div className="aInput">Recordatorio · {'{{materia}}'}</div></div>
              <div className="aField"><span className="aLabel">Cuerpo</span>
                <div style={{ border: '1.5px solid #e3e6ee', borderRadius: 10, padding: 13, fontSize: 13, lineHeight: 1.6, minHeight: 120 }}>
                  Hola <span style={{ background: '#eef0ff', color: '#4338ca', borderRadius: 5, padding: '1px 5px', fontWeight: 700 }}>{'{{nombre}}'}</span>, registramos que tenés actividades pendientes en <span style={{ background: '#eef0ff', color: '#4338ca', borderRadius: 5, padding: '1px 5px', fontWeight: 700 }}>{'{{materia}}'}</span>. Te esperamos para regularizar tu situación.
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 12, color: '#9a3412', background: '#fff7ed', border: '1px solid #fde4c8', borderRadius: 9, padding: '9px 12px' }}>
                <Icon name="alert" size={14} color="#d97706" /> Por ser un envío masivo, requiere aprobación de Coordinación antes de salir (RN-17).
              </div>
            </>
          ) : (
            <div style={{ background: '#f7f8fb', borderRadius: 10, padding: 16, fontSize: 13, lineHeight: 1.6 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Recordatorio · Análisis Matemático I</div>
              <div style={{ color: '#52596a' }}>Hola <b>Joaquín</b>, registramos que tenés actividades pendientes en <b>Análisis Matemático I</b>. Te esperamos para regularizar tu situación.</div>
              <div style={{ fontSize: 11.5, color: '#9aa1ad', marginTop: 12 }}>Vista previa para <b>Joaquín Sosa</b> · {n} destinatarios en total</div>
            </div>
          )}
        </Modal>
      )}
    </>
  );
}

// ── Seguimiento ─────────────────────────────────────────────
function VSegui() {
  return (
    <>
      <PageHead title="Seguimiento de alumnos" sub="Avance de cada alumno en las actividades del cuatrimestre.">
        <Btn icon="download">Exportar CSV</Btn>
      </PageHead>
      <div className="aCard" style={{ padding: '14px 16px', marginBottom: 16, display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div className="aField" style={{ flex: 2, minWidth: 200 }}><span className="aLabel">Buscar</span><div className="aInput ph"><span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><Icon name="search" size={14} /> Alumno o email…</span></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Comisión</span><div className="aInput">Todas <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Mín. cumplidas</span><div className="aInput ph">0–12</div></div>
        <Btn pri icon="filter">Filtrar</Btn>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="usercheck" size={16} color="#4f46e5" /> Alumnos <span className="aCount">{PD.alumnos.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Alumno</th><th>Comisión</th><th>Regional</th><th style={{ width: 200 }}>Progreso</th><th>Última actividad</th><th>Estado</th></tr></thead>
          <tbody>
            {PD.alumnos.map((a) => { const [c, b] = estCol(a.est); const pct = Math.round(a.cum / a.tot * 100); return (
              <tr key={a.leg}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Av a={a} /><div><div className="aTblName">{a.n}</div><div style={{ fontSize: 11, color: '#9aa1ad' }}>{a.mail}@activia.edu.ar</div></div></div></td>
                <td><span className="aTag">Com. {a.com}</span></td><td style={{ color: '#6b7280' }}>{a.reg}</td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aBar" style={{ flex: 1 }}><span className="aBarF" style={{ display: 'block', height: '100%', width: pct + '%', background: a.est === 'Al día' ? 'linear-gradient(90deg,#34d399,#16a34a)' : a.est === 'Atrasado' ? '#d97706' : '#e7515a' }} /></span><span className="num" style={{ fontSize: 12, minWidth: 42 }}>{a.cum}/{a.tot}</span></div></td>
                <td style={{ color: '#6b7280' }}>{a.ult}</td>
                <td><Badge color={c} bg={b}><span className="aDot" style={{ background: c }} />{a.est}</Badge></td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Monitor (coordinador) ───────────────────────────────────
function VMonitor() {
  const rows = PD.alumnos;
  return (
    <>
      <PageHead title="Monitor general de actividades" sub="Estado de cumplimiento en todas las comisiones y regionales del tenant.">
        <Btn icon="download">Exportar CSV</Btn>
      </PageHead>
      <div className="aCard" style={{ padding: '14px 16px', marginBottom: 16, display: 'grid', gridTemplateColumns: 'repeat(4,1fr) auto', gap: 10, alignItems: 'flex-end' }}>
        <div className="aField"><span className="aLabel">Materia</span><div className="aInput">Todas las materias <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField"><span className="aLabel">Comisión</span><div className="aInput">Todas <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField"><span className="aLabel">Regional</span><div className="aInput">Todas <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField"><span className="aLabel">Buscar alumno</span><div className="aInput ph">Nombre o legajo…</div></div>
        <Btn pri icon="filter">Filtrar</Btn>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="activity" size={16} color="#4f46e5" /> Resultados <span className="aCount">{rows.length} de 500</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Alumno</th><th>Comisión</th><th>Regional</th><th style={{ textAlign: 'center' }}>Cumplidas</th><th style={{ width: 150 }}>Avance</th><th>Estado</th></tr></thead>
          <tbody>
            {rows.map((a) => { const [c, b] = estCol(a.est); const pct = Math.round(a.cum / a.tot * 100); return (
              <tr key={a.leg}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Av a={a} /><span className="aTblName">{a.n}</span></div></td>
                <td><span className="aTag">Com. {a.com}</span></td><td style={{ color: '#6b7280' }}>{a.reg}</td>
                <td style={{ textAlign: 'center' }} className="num">{a.cum}/{a.tot}</td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 9 }}><span className="aBar" style={{ flex: 1 }}><span className="aBarF" style={{ display: 'block', height: '100%', width: pct + '%' }} /></span><span className="num" style={{ fontSize: 12 }}>{pct}%</span></div></td>
                <td><Badge color={c} bg={b}><span className="aDot" style={{ background: c }} />{a.est}</Badge></td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Padrón (coordinador) ────────────────────────────────────
function VPadron({ ctx }) {
  const [done, setDone] = useState(false);
  const rows = PD.alumnos;
  return (
    <>
      <PageHead title="Importación de Padrón" sub="Subí el padrón de la comisión o revisá los alumnos matriculados.">
        <Btn icon="download">Plantilla CSV</Btn>
      </PageHead>
      <ContextBar />
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, background: '#fff7ed', border: '1px solid #fde4c8', borderRadius: 12, padding: '11px 15px', fontSize: 12.5, color: '#9a3412' }}>
        <Icon name="alert" size={16} color="#d97706" /> Importar un padrón <b>reemplaza por completo</b> el anterior de esta comisión (RN-05). No se conserva historial.
      </div>
      <div className="aCard" style={{ padding: 22, marginBottom: 16 }}>
        <div style={{ border: '2px dashed #d4d8e4', borderRadius: 14, padding: '26px 18px', textAlign: 'center', background: '#fafbff' }}>
          <div style={{ width: 46, height: 46, borderRadius: 12, background: '#eef0ff', color: '#4f46e5', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}><Icon name="download" size={22} /></div>
          <div style={{ fontSize: 14, fontWeight: 800 }}>{done ? 'Padrón importado ✓' : 'Arrastrá tu archivo acá'}</div>
          <div style={{ fontSize: 12.5, color: '#6b7280', margin: '4px 0 13px' }}>CSV o Excel — columnas: legajo, nombre, email, comisión</div>
          <button className="aBtn pri" onClick={() => { setDone(true); ctx.toast('Padrón importado · 142 alumnos', 'check'); }}><Icon name="plus" size={15} color="#fff" /> Seleccionar archivo</button>
        </div>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="file" size={16} color="#4f46e5" /> Padrón actual <span className="aCount">142 alumnos</span></h3>
          <div className="aInput ph" style={{ width: 230, padding: '7px 11px' }}><span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><Icon name="search" size={14} /> Buscar alumno…</span></div></div>
        <table className="aTbl">
          <thead><tr><th>Alumno</th><th>Legajo</th><th>Email</th><th>Comisión</th><th>Estado</th></tr></thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.leg}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Av a={a} /><span className="aTblName">{a.n}</span></div></td>
                <td className="num" style={{ color: '#6b7280' }}>{a.leg}</td><td style={{ color: '#6b7280' }}>{a.mail}@activia.edu.ar</td>
                <td><span className="aTag">Com. {a.com}</span></td><td>{estChip('Activo')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Sin corregir (profesor) ─────────────────────────────────
function VSinCorregir() {
  const rows = [
    { n: 'Lucas Giménez', i: 'LG', com: '1A', act: 'TP Integrador', f: '28 mar', tipo: 'Textual' },
    { n: 'Camila Ferrari', i: 'CF', com: '1B', act: 'TP Integrador', f: '29 mar', tipo: 'Textual' },
    { n: 'Mateo Aguirre', i: 'MA', com: '2A', act: 'Ensayo Unidad 3', f: '30 mar', tipo: 'Textual' },
  ];
  return (
    <>
      <PageHead title="Posibles entregas sin corregir" sub="Actividades finalizadas en el LMS que todavía no tienen calificación (solo escala textual · RN-08).">
        <Btn icon="download">Exportar</Btn>
      </PageHead>
      <ContextBar />
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="file" size={16} color="#4f46e5" /> Detectadas <span className="aCount">{rows.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Alumno</th><th>Comisión</th><th>Actividad</th><th>Finalizada</th><th>Escala</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.n}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{r.i}</span><span className="aTblName">{r.n}</span></div></td>
                <td><span className="aTag">Com. {r.com}</span></td><td style={{ color: '#52596a' }}>{r.act}</td><td style={{ color: '#6b7280' }}>{r.f}</td>
                <td><span className="aTag" style={{ color: '#0e7490', background: '#ecfeff', borderColor: 'transparent' }}>{r.tipo}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

Object.assign(window, { V_ACAD: { materias: VMaterias, calif: VCalif, atrasados: VAtrasados, segui: VSegui, monitor: VMonitor, padron: VPadron, sincorregir: VSinCorregir } });
