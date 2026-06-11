// Vistas de ADMIN y FINANZAS (content-only, interactivas).

// ════════ ADMIN ════════
function VUsuarios({ ctx }) {
  const us = [
    { n: 'Mariana Suárez', i: 'MS', m: 'm.suarez', roles: ['Coordinador', 'Profesor'], reg: 'Córdoba', est: 'Activo', ult: 'hoy' },
    { n: 'Sofía Ledesma', i: 'SL', m: 's.ledesma', roles: ['Profesor'], reg: 'Córdoba', est: 'Activo', ult: 'ayer' },
    { n: 'Bruno Paredes', i: 'BP', m: 'b.paredes', roles: ['Tutor'], reg: 'Córdoba', est: 'Activo', ult: 'hace 2 d' },
    { n: 'Diego Ferreyra', i: 'DF', m: 'd.ferreyra', roles: ['Profesor'], reg: 'Rosario', est: 'Activo', ult: 'hace 1 d' },
    { n: 'Valeria Roso', i: 'VR', m: 'v.roso', roles: ['Tutor'], reg: 'Rosario', est: 'Suspendido', ult: 'hace 30 d' },
    { n: 'Roberto Díaz', i: 'RD', m: 'r.diaz', roles: ['Finanzas'], reg: '—', est: 'Activo', ult: 'hoy' },
    { n: 'Lucía Ferrer', i: 'LF', m: 'l.ferrer', roles: ['Administrador'], reg: '—', est: 'Activo', ult: 'hoy' },
  ];
  const roleCol = (r) => r === 'Administrador' ? ['#be185d', '#fce7f3'] : r === 'Finanzas' ? ['#047857', '#ecfdf5'] : /Coordinador/.test(r) ? ['#4338ca', '#eef0ff'] : ['#52596a', '#f1f2f5'];
  return (
    <>
      <PageHead title="Usuarios" sub="Cuentas, roles y permisos del personal del tenant.">
        <Btn icon="download">Exportar</Btn>
        <button className="aBtn pri" onClick={() => ctx.toast('Formulario de nuevo usuario', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nuevo usuario</button>
      </PageHead>
      <div className="aCard" style={{ padding: '14px 16px', marginBottom: 16, display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div className="aField" style={{ flex: 2, minWidth: 200 }}><span className="aLabel">Buscar</span><div className="aInput ph"><span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><Icon name="search" size={14} /> Nombre o email…</span></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Rol</span><div className="aInput">Todos <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Estado</span><div className="aInput">Todos <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="user" size={16} color="#4f46e5" /> Usuarios <span className="aCount">{us.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Usuario</th><th>Email</th><th>Roles</th><th>Regional</th><th>Estado</th><th>Último acceso</th><th></th></tr></thead>
          <tbody>
            {us.map((u) => (
              <tr key={u.m}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{u.i}</span><span className="aTblName">{u.n}</span></div></td>
                <td style={{ color: '#6b7280' }}>{u.m}@activia.edu.ar</td>
                <td><div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>{u.roles.map((r) => { const [c, b] = roleCol(r); return <Badge key={r} color={c} bg={b}>{r}</Badge>; })}</div></td>
                <td style={{ color: '#6b7280' }}>{u.reg}</td><td>{estChip(u.est)}</td><td style={{ color: '#6b7280' }}>{u.ult}</td>
                <td><span className="aToggleLink" onClick={() => ctx.toast('Editar roles · impersonar', 'user')}>Editar</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function VEstructura({ ctx }) {
  const Node = ({ depth, icon, color, bg, label, sub, count, open, on }) => (
    <div className="pHL pClickable" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', paddingLeft: 12 + depth * 22, borderRadius: 10, background: on ? '#eef0ff' : 'transparent' }}>
      {count != null ? <Icon name={open ? 'chevd' : 'chev'} size={14} color="#9aa1ad" /> : <span style={{ width: 14 }} />}
      <div style={{ width: 28, height: 28, borderRadius: 8, background: bg, color, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto' }}><Icon name={icon} size={15} /></div>
      <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 13, fontWeight: on ? 800 : 700, color: on ? '#4338ca' : '#1d2330' }}>{label}</div>{sub && <div style={{ fontSize: 11, color: '#9aa1ad' }}>{sub}</div>}</div>
      {count != null && <span className="aTag">{count}</span>}
    </div>
  );
  return (
    <>
      <PageHead title="Estructura académica" sub="Regionales, carreras, materias y comisiones del tenant.">
        <button className="aBtn" onClick={() => ctx.toast('Nueva carrera', 'plus')}><Icon name="plus" size={15} /> Carrera</button>
        <button className="aBtn pri" onClick={() => ctx.toast('Nueva materia', 'plus')}><Icon name="plus" size={15} color="#fff" /> Materia</button>
      </PageHead>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="aCard">
          <div className="aCardH"><h3><Icon name="sliders" size={16} color="#4f46e5" /> Jerarquía</h3></div>
          <div style={{ padding: 10 }}>
            <Node depth={0} icon="shield" color="#0e7490" bg="#ecfeff" label="Regional Córdoba" sub="2 carreras · 60 materias" count={2} open />
            <Node depth={1} icon="award" color="#4338ca" bg="#eef0ff" label="Ing. en Sistemas de Información" sub="42 materias · 8 cohortes" count={42} open />
            <Node depth={2} icon="book" color="#4f46e5" bg="#f5f6ff" label="Análisis Matemático I" sub="4 comisiones" on />
            <Node depth={2} icon="book" color="#6b7280" bg="#f1f2f5" label="Álgebra y Geometría Analítica" sub="3 comisiones" />
            <Node depth={1} icon="award" color="#4338ca" bg="#eef0ff" label="Tecnicatura en Programación" sub="18 materias · 6 cohortes" count={18} />
            <Node depth={0} icon="shield" color="#0e7490" bg="#ecfeff" label="Regional Rosario" sub="3 carreras · 88 materias" count={3} />
          </div>
        </div>
        <div className="aCard" style={{ alignSelf: 'flex-start' }}>
          <div className="aCardH"><h3><Icon name="book" size={16} color="#4f46e5" /> Análisis Matemático I</h3><span className="aToggleLink" onClick={() => ctx.toast('Editar materia', 'book')}>Editar</span></div>
          <div style={{ padding: 18 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
              {[['Carrera', 'Ing. en Sistemas'], ['Regional', 'Córdoba'], ['Plan', '2023'], ['Código', 'AM1 · m-0c4f…a91']].map(([l, v]) => (
                <div key={l} style={{ background: '#f7f8fb', borderRadius: 10, padding: '10px 13px' }}><div style={{ fontSize: 11, color: '#9aa1ad', fontWeight: 600 }}>{l}</div><div style={{ fontSize: 13, fontWeight: 700, marginTop: 2 }}>{v}</div></div>
              ))}
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', marginBottom: 9 }}>COMISIONES</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[['1A', 48, 'Dra. Ledesma'], ['1B', 48, 'Ing. Núñez'], ['2A', 52, 'Prof. Ferreyra']].map(([c, al, d]) => (
                <div key={c} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 13px', border: '1px solid #eceef2', borderRadius: 11 }}>
                  <div style={{ width: 34, height: 34, borderRadius: 9, background: '#eef0ff', color: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 12 }}>{c}</div>
                  <div style={{ flex: 1 }}><div style={{ fontSize: 13, fontWeight: 700 }}>Comisión {c}</div><div style={{ fontSize: 11.5, color: '#9aa1ad' }}>A cargo: {d}</div></div>
                  <span className="aTag"><Icon name="users" size={12} /> {al}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function VFechas({ ctx }) {
  const f = [
    { tipo: 'Parcial', n: 1, m: 'AM1', f: '12 abr 2026', per: '2026-1' },
    { tipo: 'TP', n: 1, m: 'AM1', f: '28 abr 2026', per: '2026-1' },
    { tipo: 'Parcial', n: 2, m: 'AM1', f: '24 may 2026', per: '2026-1' },
    { tipo: 'Coloquio', n: 1, m: 'AGA', f: '18 mar 2026', per: '2026-1' },
    { tipo: 'Recuperatorio', n: 1, m: 'FIS', f: '20 abr 2026', per: '2026-1' },
  ];
  const tc = (t) => t === 'Parcial' ? ['#4338ca', '#eef0ff'] : t === 'TP' ? ['#0e7490', '#ecfeff'] : t === 'Coloquio' ? ['#6d28d9', '#f3eefe'] : ['#d97706', '#fef6e7'];
  return (
    <>
      <PageHead title="Fechas de evaluación" sub="Cronograma de parciales, TPs y coloquios por materia y cohorte.">
        <button className="aBtn" onClick={() => ctx.toast('Bloque para el aula virtual generado', 'check')}><Icon name="download" size={15} /> Generar para LMS</button>
        <button className="aBtn pri" onClick={() => ctx.toast('Nueva fecha académica', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nueva fecha</button>
      </PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="calendar" size={16} color="#4f46e5" /> Calendario 2026 · 1.ºC <span className="aCount">{f.length}</span></h3>
          <div className="aTabs"><span className="aTab on">Tabla</span><span className="aTab">Calendario</span></div></div>
        <table className="aTbl">
          <thead><tr><th>Tipo</th><th>Instancia</th><th>Materia</th><th>Período</th><th>Fecha</th><th></th></tr></thead>
          <tbody>
            {f.map((x, i) => { const [c, b] = tc(x.tipo); return (
              <tr key={i}>
                <td><Badge color={c} bg={b}>{x.tipo}</Badge></td>
                <td className="aTblName">{x.tipo} {x.n}</td><td><span className="aTag">{x.m}</span></td>
                <td style={{ color: '#6b7280' }}>{x.per}</td><td className="num" style={{ fontWeight: 700 }}>{x.f}</td>
                <td><span className="aToggleLink" onClick={() => ctx.toast('Editar fecha', 'calendar')}>Editar</span></td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function VProgramas({ ctx }) {
  const p = [
    { m: 'Análisis Matemático I', car: 'Ing. en Sistemas', co: '2026·1', arch: 'programa_am1_2026.pdf', at: '01 mar' },
    { m: 'Álgebra y Geom. Analítica', car: 'Ing. en Sistemas', co: '2026·1', arch: 'programa_aga_2026.pdf', at: '01 mar' },
    { m: 'Programación I', car: 'Tec. en Programación', co: '2026·1', arch: null, at: null },
  ];
  return (
    <>
      <PageHead title="Programas de materias" sub="Documento oficial del programa por materia, carrera y cohorte.">
        <button className="aBtn pri" onClick={() => ctx.toast('Subir programa', 'plus')}><Icon name="plus" size={15} color="#fff" /> Subir programa</button>
      </PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="file" size={16} color="#4f46e5" /> Programas <span className="aCount">{p.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Materia</th><th>Carrera</th><th>Cohorte</th><th>Archivo</th><th>Cargado</th><th></th></tr></thead>
          <tbody>
            {p.map((x, i) => (
              <tr key={i}>
                <td className="aTblName">{x.m}</td><td style={{ color: '#52596a' }}>{x.car}</td><td><span className="aTag">{x.co}</span></td>
                <td>{x.arch ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: '#4338ca', fontWeight: 600, fontSize: 12.5 }}><Icon name="file" size={14} /> {x.arch}</span> : <span style={{ fontSize: 12, color: '#d97706', fontWeight: 600 }}>Pendiente</span>}</td>
                <td style={{ color: '#6b7280' }}>{x.at || '—'}</td>
                <td>{x.arch ? <span className="aToggleLink" onClick={() => ctx.toast('Descargar programa', 'download')}>Descargar</span> : <span className="aToggleLink" onClick={() => ctx.toast('Subir archivo', 'plus')}>Subir</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function VConfig({ ctx }) {
  const [aprob, setAprob] = React.useState(true);
  const [tfa, setTfa] = React.useState(true);
  const Toggle = ({ on, set }) => (
    <div onClick={set} style={{ width: 42, height: 24, borderRadius: 99, background: on ? '#4338ca' : '#d4d8e4', position: 'relative', cursor: 'pointer', flex: '0 0 auto', transition: 'background .15s' }}>
      <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#fff', position: 'absolute', top: 3, left: on ? 21 : 3, transition: 'left .15s', boxShadow: '0 1px 3px rgba(0,0,0,.2)' }} />
    </div>
  );
  const Row = ({ t, d, children }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '15px 0', borderBottom: '1px solid var(--line2)' }}>
      <div style={{ flex: 1 }}><div style={{ fontSize: 13.5, fontWeight: 700 }}>{t}</div><div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{d}</div></div>
      {children}
    </div>
  );
  return (
    <>
      <PageHead title="Configuración del tenant" sub="Parámetros institucionales: marca, escalas, seguridad y comunicaciones." />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="aCard" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="sliders" size={16} color="#4f46e5" /> General</div>
          <Row t="Aprobación de comunicaciones masivas" d="Exigir aprobación antes del despacho (RN-17).">
            <Toggle on={aprob} set={() => { setAprob((v) => !v); ctx.toast('Preferencia actualizada', 'check'); }} />
          </Row>
          <Row t="Verificación en dos pasos (2FA)" d="Obligatoria para todos los usuarios del tenant.">
            <Toggle on={tfa} set={() => { setTfa((v) => !v); ctx.toast('Preferencia actualizada', 'check'); }} />
          </Row>
          <Row t="Umbral de aprobación por defecto" d="Valor inicial para nuevas materias (RN-03).">
            <span className="aTag" style={{ fontSize: 13, fontWeight: 800, color: '#4338ca' }}>60 %</span>
          </Row>
        </div>
        <div className="aCard" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="check" size={16} color="#4f46e5" /> Escala de calificación textual</div>
          <div style={{ fontSize: 12, color: '#6b7280', margin: '0 0 14px' }}>Valores que cuentan como aprobado (RN-02).</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
            {['Satisfactorio', 'Supera lo esperado'].map((v) => <span key={v} className="aBadge" style={{ color: '#16a34a', background: '#ecfdf3' }}><Icon name="check" size={12} color="#16a34a" /> {v}</span>)}
            {['No satisfactorio', 'No alcanzado'].map((v) => <span key={v} className="aBadge" style={{ color: '#6b7280', background: '#f1f2f5' }}>{v}</span>)}
          </div>
          <div style={{ fontSize: 14, fontWeight: 800, margin: '22px 0 6px', display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="award" size={16} color="#4f46e5" /> Marca institucional</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
            <div style={{ width: 40, height: 40, borderRadius: 11, background: 'linear-gradient(150deg,#6366f1,#4338ca)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="activity" size={20} color="#fff" /></div>
            <div><div style={{ fontSize: 13, fontWeight: 700 }}>activia·trace</div><div style={{ fontSize: 11.5, color: '#9aa1ad' }}>Color de acento · Índigo</div></div>
            <button className="aBtn sm" style={{ marginLeft: 'auto' }} onClick={() => ctx.toast('Personalizar marca', 'sliders')}>Cambiar</button>
          </div>
        </div>
      </div>
    </>
  );
}

// ════════ FINANZAS ════════
const LIQ = {
  general: [
    { n: 'Sofía Ledesma', i: 'SL', rol: 'Profesor', com: 2, base: 480000, plus: 120000 },
    { n: 'Bruno Paredes', i: 'BP', rol: 'Tutor', com: 1, base: 220000, plus: 40000 },
    { n: 'Diego Ferreyra', i: 'DF', rol: 'Profesor', com: 1, base: 360000, plus: 60000 },
    { n: 'Mariana Suárez', i: 'MS', rol: 'Coordinador', com: 0, base: 540000, plus: 0 },
  ],
  nexo: [{ n: 'Pablo Iglesias', i: 'PI', rol: 'Nexo', com: 3, base: 300000, plus: 90000 }],
  factura: [{ n: 'Carla Núñez', i: 'CN', rol: 'Profesor', com: 1, total: 268000 }],
};
const money = (n) => '$ ' + n.toLocaleString('es-AR');
function VLiquid({ ctx }) {
  const [cerrada, setCerrada] = React.useState(false);
  const [modal, setModal] = React.useState(false);
  const tot = (arr) => arr.reduce((s, x) => s + (x.total != null ? x.total : x.base + x.plus), 0);
  const sinF = tot(LIQ.general) + tot(LIQ.nexo);
  const conF = tot(LIQ.factura);
  const Seg = ({ title, rows, hint }) => (
    <div className="aCard" style={{ marginBottom: 14 }}>
      <div className="aCardH"><h3 style={{ fontSize: 13.5 }}>{title}</h3>{hint && <span className="aHelp">{hint}</span>}</div>
      <table className="aTbl">
        <thead><tr><th>Docente</th><th>Rol</th><th style={{ textAlign: 'center' }}>Comis.</th><th style={{ textAlign: 'right' }}>Base</th><th style={{ textAlign: 'right' }}>Plus</th><th style={{ textAlign: 'right' }}>Total</th></tr></thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.n}>
              <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{d.i}</span><span className="aTblName">{d.n}</span></div></td>
              <td style={{ color: '#52596a' }}>{d.rol}</td><td style={{ textAlign: 'center' }} className="num">{d.com}</td>
              <td style={{ textAlign: 'right' }} className="num">{d.base != null ? money(d.base) : '—'}</td>
              <td style={{ textAlign: 'right' }} className="num">{d.plus != null ? money(d.plus) : '—'}</td>
              <td style={{ textAlign: 'right', fontWeight: 800 }} className="num">{money(d.total != null ? d.total : d.base + d.plus)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return (
    <>
      <PageHead title="Liquidaciones" sub="Cálculo de honorarios Base + Plus por período. Universo en relación de dependencia y facturantes.">
        <div className="aInput" style={{ width: 160, fontSize: 12.5 }}>Período · abr 2026 <Icon name="chevd" size={14} color="#9aa1ad" /></div>
        <Btn icon="download">Exportar</Btn>
        {cerrada
          ? <span className="aBadge" style={{ color: '#6b7280', background: '#f1f2f5', padding: '8px 12px' }}><Icon name="shield" size={13} /> Cerrada · inmutable</span>
          : <button className="aBtn pri" onClick={() => setModal(true)}><Icon name="check" size={15} color="#fff" /> Cerrar liquidación</button>}
      </PageHead>
      <div className="aKpis" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {[['Total sin factura', money(sinF), 'dollar', 'ok'], ['Total con factura', money(conF), 'file', 'amber'], ['Docentes', String(LIQ.general.length + LIQ.nexo.length + LIQ.factura.length), 'users', 'vio'], ['Estado', cerrada ? 'Cerrada' : 'Abierta', 'shield', '']].map(([l, v, ic, k]) => (
          <div key={l} className="aKpi"><div className={'aChip ' + k}><Icon name={ic} size={18} /></div><div className="aKv" style={{ fontSize: 21 }}>{v}</div><div className="aKl">{l}</div></div>
        ))}
      </div>
      <Seg title="Detalle general (relación de dependencia)" rows={LIQ.general} />
      <Seg title="NEXO · se muestra aparte pero suma al total (RN-36)" rows={LIQ.nexo} />
      <Seg title="Docentes que facturan · excluidos del total (RN-35)" rows={LIQ.factura} hint="Su pago se gestiona en Facturas" />
      {modal && (
        <Modal title="Cerrar liquidación" sub="abr 2026 · cohorte 2026·1" max={440} onClose={() => setModal(false)}
          footer={<><button className="aBtn" onClick={() => setModal(false)}>Cancelar</button><button className="aBtn pri" onClick={() => { setCerrada(true); setModal(false); ctx.toast('Liquidación cerrada · inmutable', 'check'); }}><Icon name="shield" size={14} color="#fff" /> Cerrar definitivamente</button></>}>
          <div style={{ fontSize: 13.5, color: '#374151', lineHeight: 1.6 }}>Al cerrar, la liquidación de este período queda <b>inmutable</b> y no podrá modificarse (RN-22). Total a liquidar: <b>{money(sinF)}</b>.</div>
        </Modal>
      )}
    </>
  );
}

function VHistLiq() {
  const h = [['mar 2026', '2026·1', money(1560000), 18, 'Cerrada'], ['feb 2026', '2026·1', money(1490000), 18, 'Cerrada'], ['dic 2025', '2025·2', money(1720000), 21, 'Cerrada']];
  return (
    <>
      <PageHead title="Historial de liquidaciones" sub="Liquidaciones cerradas de períodos anteriores. Solo lectura."><Btn icon="download">Exportar</Btn></PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="clock" size={16} color="#4f46e5" /> Períodos cerrados <span className="aCount">{h.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Período</th><th>Cohorte</th><th style={{ textAlign: 'right' }}>Total</th><th style={{ textAlign: 'center' }}>Docentes</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {h.map((x, i) => (
              <tr key={i}><td className="aTblName">{x[0]}</td><td><span className="aTag">{x[1]}</span></td><td style={{ textAlign: 'right', fontWeight: 700 }} className="num">{x[2]}</td><td style={{ textAlign: 'center' }} className="num">{x[3]}</td><td>{estChip('Cerrada')}</td><td><span className="aToggleLink">Ver detalle</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function VGrilla({ ctx }) {
  return (
    <>
      <PageHead title="Grilla salarial" sub="Base por rol y Plus por categoría de materia, con vigencia temporal (RN-31..33).">
        <button className="aBtn pri" onClick={() => ctx.toast('Nueva regla salarial', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nueva regla</button>
      </PageHead>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="aCard">
          <div className="aCardH"><h3><Icon name="dollar" size={16} color="#4f46e5" /> Salario base por rol</h3></div>
          <table className="aTbl">
            <thead><tr><th>Rol</th><th style={{ textAlign: 'right' }}>Monto</th><th>Vigencia</th></tr></thead>
            <tbody>
              {[['Coordinador', 540000], ['Profesor', 480000], ['Nexo', 300000], ['Tutor', 220000]].map((r) => (
                <tr key={r[0]}><td className="aTblName">{r[0]}</td><td style={{ textAlign: 'right' }} className="num">{money(r[1])}</td><td style={{ color: '#6b7280', fontSize: 12 }}>desde 01/01/26</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="aCard">
          <div className="aCardH"><h3><Icon name="layers" size={16} color="#4f46e5" /> Plus por categoría × rol</h3></div>
          <table className="aTbl">
            <thead><tr><th>Categoría</th><th>Rol</th><th style={{ textAlign: 'right' }}>Monto</th></tr></thead>
            <tbody>
              {[['PROG', 'Profesor', 80000], ['PROG', 'Tutor', 40000], ['BD', 'Profesor', 70000], ['MAT', 'Profesor', 60000]].map((r, i) => (
                <tr key={i}><td><span className="aTag" style={{ color: '#6d28d9', background: '#f3eefe', borderColor: 'transparent' }}>{r[0]}</span></td><td style={{ color: '#52596a' }}>{r[1]}</td><td style={{ textAlign: 'right' }} className="num">{money(r[2])}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function VFacturas({ ctx }) {
  const [fs, setFs] = React.useState([
    { n: 'Carla Núñez', i: 'CN', per: 'abr 2026', det: 'Honorarios docentes · AM1', kb: 142, est: 'Pendiente' },
    { n: 'Marcos Vidal', i: 'MV', per: 'abr 2026', det: 'Honorarios docentes · PR1', kb: 98, est: 'Pendiente' },
    { n: 'Laura Pinto', i: 'LP', per: 'mar 2026', det: 'Honorarios docentes · BD', kb: 120, est: 'Abonada' },
  ]);
  const pagar = (i) => { setFs((s) => s.map((x, j) => j === i ? { ...x, est: 'Abonada' } : x)); ctx.toast('Factura marcada como abonada', 'check'); };
  return (
    <>
      <PageHead title="Facturas" sub="Comprobantes de docentes que facturan. Su pago va por fuera de la liquidación general (RN-35).">
        <Btn icon="download">Exportar</Btn>
      </PageHead>
      <div className="aCard" style={{ padding: '14px 16px', marginBottom: 16, display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div className="aField" style={{ flex: 2, minWidth: 200 }}><span className="aLabel">Buscar</span><div className="aInput ph"><span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><Icon name="search" size={14} /> Docente o detalle…</span></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Estado</span><div className="aInput">Todos <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField" style={{ flex: 1 }}><span className="aLabel">Período</span><div className="aInput">abr 2026 <Icon name="calendar" size={14} color="#9aa1ad" /></div></div>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="file" size={16} color="#4f46e5" /> Comprobantes <span className="aCount">{fs.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Docente</th><th>Período</th><th>Detalle</th><th>Archivo</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {fs.map((f, i) => (
              <tr key={i}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{f.i}</span><span className="aTblName">{f.n}</span></div></td>
                <td style={{ color: '#6b7280' }}>{f.per}</td><td style={{ color: '#52596a' }}>{f.det}</td>
                <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#4338ca', fontWeight: 600, fontSize: 12.5 }}><Icon name="file" size={14} /> factura.pdf <span style={{ color: '#9aa1ad', fontWeight: 500 }}>· {f.kb} KB</span></span></td>
                <td>{estChip(f.est === 'Abonada' ? 'Pagado' : 'Pendiente')}</td>
                <td>{f.est === 'Pendiente' ? <button className="aBtn pri sm" onClick={() => pagar(i)}><Icon name="check" size={13} color="#fff" /> Marcar abonada</button> : <span style={{ fontSize: 12, color: '#9aa1ad' }}>—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

Object.assign(window, {
  V_ADMIN: { usuarios: VUsuarios, estructura: VEstructura, fechas: VFechas, programas: VProgramas, config: VConfig },
  V_FIN: { liquid: VLiquid, histliq: VHistLiq, grilla: VGrilla, facturas: VFacturas },
});
