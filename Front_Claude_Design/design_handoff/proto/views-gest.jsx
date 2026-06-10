// Vistas de gestión y comunicación (content-only). Coordinador + Profesor.

// ── Aprobaciones · cola de comunicaciones (coordinador) ─────
function VAprob({ ctx }) {
  const [cola, setCola] = React.useState(PD.cola);
  const act = (id, estado, msg) => { setCola((c) => c.map((x) => x.id === id ? { ...x, estado } : x)); ctx.toast(msg, estado === 'Cancelado' ? 'x' : 'check'); };
  const pend = cola.filter((c) => c.est === 'Pendiente' || c.estado === 'Pendiente');
  return (
    <>
      <PageHead title="Aprobación de comunicaciones" sub="Los envíos masivos quedan en cola hasta que los apruebes (RN-17). Revisá y habilitá o cancelá." />
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        {[['Pendientes de aprobar', cola.filter((c) => (c.estado || c.est) === 'Pendiente').length, 'amber'], ['Aprobados hoy', cola.filter((c) => c.estado === 'Enviando' || c.est === 'Enviado').length, 'ok'], ['Cancelados', cola.filter((c) => c.estado === 'Cancelado').length, 'warn']].map(([l, v, k]) => (
          <div key={l} className="aCard" style={{ flex: 1, padding: '13px 16px' }}><div style={{ fontSize: 11.5, color: '#6b7280', fontWeight: 600 }}>{l}</div><div style={{ fontSize: 22, fontWeight: 800, marginTop: 3, color: k === 'warn' ? '#e7515a' : k === 'amber' ? '#d97706' : '#16a34a' }}>{v}</div></div>
        ))}
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="mail" size={16} color="#4f46e5" /> Lotes en cola <span className="aCount">{cola.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Lote</th><th>Docente</th><th>Materia</th><th style={{ textAlign: 'center' }}>Destinatarios</th><th>Asunto</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {cola.map((c) => {
              const est = c.estado || c.est;
              const isPend = est === 'Pendiente';
              const shown = est === 'Enviando' ? 'Enviando' : est;
              return (
                <tr key={c.id}>
                  <td className="num" style={{ color: '#6b7280' }}>{c.id}</td>
                  <td><div style={{ display: 'flex', alignItems: 'center', gap: 9 }}><span className="aAvSm" style={{ width: 26, height: 26, fontSize: 10 }}>{c.av}</span><span style={{ fontSize: 12.5 }}>{c.prof}</span></div></td>
                  <td><span className="aTag">{c.materia}</span></td>
                  <td style={{ textAlign: 'center' }} className="num">{c.dest}</td>
                  <td className="aTblName">{c.asunto}</td>
                  <td>{estChip(shown === 'Enviando' || shown === 'Enviado' ? 'Enviado' : shown === 'Cancelado' ? 'Cancelada' : 'Pendiente')}</td>
                  <td>
                    {isPend ? (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="aBtn pri sm" onClick={() => act(c.id, 'Enviando', `Lote ${c.id} aprobado · ${c.dest} mensajes en envío`)}>Aprobar</button>
                        <button className="aBtn sm" onClick={() => act(c.id, 'Cancelado', `Lote ${c.id} cancelado`)}>Cancelar</button>
                      </div>
                    ) : <span style={{ fontSize: 12, color: '#9aa1ad' }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Avisos (coordinador) ────────────────────────────────────
function VAvisos({ ctx }) {
  const [list, setList] = React.useState([
    { t: 'Inicio de cuatrimestre 2026 · 1.ºC', aud: 'Todos los docentes', f: '01 mar', est: 'Publicado', sev: 'Info', ack: false },
    { t: 'Recordatorio: carga de notas Parcial 1', aud: 'Equipo AM1', f: '28 mar', est: 'Publicado', sev: 'Advertencia', ack: true },
    { t: 'Cambio de fecha: Parcial 2 de AM1', aud: 'Cohorte 2026·1', f: '02 abr', est: 'Publicado', sev: 'Advertencia', ack: true },
  ]);
  const [modal, setModal] = React.useState(false);
  const [ack, setAck] = React.useState(true);
  const [sev, setSev] = React.useState('Advertencia');
  const sevCol = (s) => s === 'Crítico' ? ['#e7515a', '#fff1f0'] : s === 'Advertencia' ? ['#d97706', '#fef6e7'] : ['#4338ca', '#eef0ff'];
  const publish = () => { setList((l) => [{ t: 'Nuevo aviso', aud: 'Cohorte 2026·1', f: 'ahora', est: 'Publicado', sev, ack }, ...l]); setModal(false); ctx.toast('Aviso publicado', 'bell'); };
  return (
    <>
      <PageHead title="Avisos" sub="Publicá novedades segmentadas por audiencia, severidad y vigencia.">
        <button className="aBtn pri" onClick={() => setModal(true)}><Icon name="plus" size={15} color="#fff" /> Nuevo aviso</button>
      </PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="bell" size={16} color="#4f46e5" /> Gestión de avisos <span className="aCount">{list.length}</span></h3>
          <div className="aTabs"><span className="aTab on">Todos</span><span className="aTab">Publicados</span><span className="aTab">Borradores</span></div></div>
        <table className="aTbl">
          <thead><tr><th>Título</th><th>Audiencia</th><th>Severidad</th><th>Acuse</th><th>Fecha</th><th>Estado</th></tr></thead>
          <tbody>
            {list.map((a, i) => { const [c, b] = sevCol(a.sev); return (
              <tr key={i}>
                <td className="aTblName">{a.t}</td><td style={{ color: '#52596a' }}>{a.aud}</td>
                <td><Badge color={c} bg={b}>{a.sev}</Badge></td>
                <td>{a.ack ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#16a34a', fontWeight: 700 }}><Icon name="check" size={13} color="#16a34a" /> Requiere</span> : <span style={{ fontSize: 12, color: '#9aa1ad' }}>No</span>}</td>
                <td style={{ color: '#6b7280' }}>{a.f}</td><td>{estChip(a.est)}</td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
      {modal && (
        <Modal title="Nuevo aviso" sub="Definí audiencia, severidad y vigencia" onClose={() => setModal(false)}
          footer={<><button className="aBtn" onClick={() => setModal(false)}>Cancelar</button><button className="aBtn pri" onClick={publish}><Icon name="bell" size={14} color="#fff" /> Publicar</button></>}>
          <div className="aField" style={{ marginBottom: 13 }}><span className="aLabel">Título</span><div className="aInput ph">Ej. Cambio de aula del Parcial 2…</div></div>
          <div className="aField" style={{ marginBottom: 13 }}><span className="aLabel">Cuerpo</span><div className="aInput ph" style={{ minHeight: 80, alignItems: 'flex-start' }}>Escribí el mensaje…</div></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 13 }}>
            <div className="aField"><span className="aLabel">Alcance</span><div className="aInput">Por cohorte <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
            <div className="aField"><span className="aLabel">Severidad</span>
              <div className="aTabs">{['Info', 'Advertencia', 'Crítico'].map((s) => <span key={s} className={'aTab' + (sev === s ? ' on' : '')} onClick={() => setSev(s)}>{s}</span>)}</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div className="aField"><span className="aLabel">Visible desde</span><div className="aInput">hoy <Icon name="calendar" size={14} color="#9aa1ad" /></div></div>
            <div className="aField"><span className="aLabel">Hasta</span><div className="aInput">15 abr <Icon name="calendar" size={14} color="#9aa1ad" /></div></div>
          </div>
          <div className="pHL pClickable" style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '11px 13px', border: '1px solid #eceef2', borderRadius: 11 }} onClick={() => setAck((v) => !v)}>
            <Check on={ack} />
            <div><div style={{ fontSize: 13, fontWeight: 700 }}>Requiere acuse de recibo</div><div style={{ fontSize: 11.5, color: '#9aa1ad' }}>El destinatario debe confirmar la lectura (RN-19).</div></div>
          </div>
        </Modal>
      )}
    </>
  );
}

// ── Comunicaciones · composer (coord / profesor) ────────────
function VComuni({ ctx }) {
  const [preview, setPreview] = React.useState(false);
  const encolar = () => ctx.toast('Comunicación encolada · pendiente de aprobación', 'mail');
  return (
    <>
      <PageHead title="Comunicaciones" sub="Redactá un mensaje con variables y enviálo a una audiencia segmentada." />
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16 }}>
        <div className="aCard" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 9 }}><Icon name="mail" size={16} color="#4f46e5" /> Componer mensaje</div>
          <div className="aField" style={{ marginBottom: 14 }}><span className="aLabel">Asunto</span><div className="aInput">Recordatorio de Parcial 1 — {'{{materia}}'}</div></div>
          <div className="aField" style={{ marginBottom: 12 }}><span className="aLabel">Cuerpo</span>
            <div style={{ border: '1.5px solid #e3e6ee', borderRadius: 10, padding: '12px 13px', fontSize: 13, minHeight: 150, lineHeight: 1.6 }}>
              Hola <span style={{ background: '#eef0ff', color: '#4338ca', borderRadius: 5, padding: '1px 5px', fontWeight: 700 }}>{'{{nombre}}'}</span>, te recordamos que el <b>Parcial 1</b> de <span style={{ background: '#eef0ff', color: '#4338ca', borderRadius: 5, padding: '1px 5px', fontWeight: 700 }}>{'{{materia}}'}</span> es el <b>12 de abril</b>. ¡Éxitos!
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11.5, color: '#9aa1ad', fontWeight: 600 }}>Insertar:</span>
            {['{{nombre}}', '{{materia}}', '{{comision}}', '{{legajo}}'].map((v) => <span key={v} style={{ fontSize: 11.5, fontWeight: 700, color: '#4338ca', background: '#f5f6ff', border: '1px solid #e3e6ee', borderRadius: 7, padding: '4px 9px', cursor: 'pointer', fontFamily: 'ui-monospace,monospace' }}>{v}</span>)}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="aCard" style={{ padding: 18 }}>
            <div style={{ fontSize: 13.5, fontWeight: 800, marginBottom: 13, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="users" size={15} color="#4f46e5" /> Destinatarios</span><span className="aCount">142</span></div>
            <div className="aField" style={{ marginBottom: 11 }}><span className="aLabel">Audiencia</span><div className="aInput">Alumnos atrasados · AM1 <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
            <div className="eqPick" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, border: '1.5px solid #e3e6ee', borderRadius: 11, padding: 8 }}>
              <span className="aTag">Com. 1A</span><span className="aTag">Com. 1B</span><span className="aTag">Com. 2A</span>
            </div>
          </div>
          <div className="aCard" style={{ padding: 18 }}>
            <div style={{ fontSize: 13.5, fontWeight: 800, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="check" size={15} color="#16a34a" /> Antes de enviar</div>
            <div style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5, marginBottom: 14 }}>Toda comunicación pasa por <b>vista previa</b> (RN-16) y, si es masiva, por <b>aprobación</b> de Coordinación (RN-17).</div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="aBtn" style={{ flex: 1 }} onClick={() => setPreview(true)}><Icon name="search" size={14} /> Previsualizar</button>
              <button className="aBtn pri" style={{ flex: 1 }} onClick={encolar}><Icon name="mail" size={14} color="#fff" /> Encolar</button>
            </div>
          </div>
        </div>
      </div>
      {preview && (
        <Modal title="Vista previa" sub="Así lo recibirá el destinatario" onClose={() => setPreview(false)}
          footer={<><button className="aBtn" onClick={() => setPreview(false)}>Cerrar</button><button className="aBtn pri" onClick={() => { setPreview(false); encolar(); }}><Icon name="mail" size={14} color="#fff" /> Encolar</button></>}>
          <div style={{ background: '#f7f8fb', borderRadius: 10, padding: 16, fontSize: 13, lineHeight: 1.6 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Recordatorio de Parcial 1 — Análisis Matemático I</div>
            <div style={{ color: '#52596a' }}>Hola <b>Joaquín</b>, te recordamos que el Parcial 1 de <b>Análisis Matemático I</b> es el 12 de abril. ¡Éxitos!</div>
          </div>
        </Modal>
      )}
    </>
  );
}

// ── Tareas (coord / profesor) ───────────────────────────────
function VTareas({ ctx }) {
  const tareas = [
    { t: 'Cargar notas del Parcial 1', m: 'AM1', d: 'Dra. Sofía Ledesma', i: 'SL', v: '12 abr', est: 'En curso' },
    { t: 'Revisar padrón Comisión 2A', m: 'AM1', d: 'Lic. Valeria Roso', i: 'VR', v: '08 abr', est: 'Pendiente' },
    { t: 'Subir programa actualizado', m: 'AGA', d: 'Prof. Diego Ferreyra', i: 'DF', v: '15 abr', est: 'Pendiente' },
    { t: 'Validar equipo docente', m: 'AM1', d: 'Mariana Suárez', i: 'MS', v: '05 abr', est: 'Hecha' },
  ];
  return (
    <>
      <PageHead title="Tareas" sub="Coordiná el trabajo de la cátedra: asigná, seguí y cerrá tareas.">
        <button className="aBtn pri" onClick={() => ctx.toast('Formulario de nueva tarea', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nueva tarea</button>
      </PageHead>
      <div className="aCard" style={{ padding: '14px 16px', marginBottom: 16, display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div className="aField" style={{ flex: 1, minWidth: 150 }}><span className="aLabel">Asignada a</span><div className="aInput">Todos <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField" style={{ flex: 1, minWidth: 140 }}><span className="aLabel">Materia</span><div className="aInput">Todas <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <div className="aField" style={{ flex: 1, minWidth: 140 }}><span className="aLabel">Estado</span><div className="aInput">Todos <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
        <Btn pri icon="filter">Filtrar</Btn>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="clipboard" size={16} color="#4f46e5" /> Tareas <span className="aCount">{tareas.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Tarea</th><th>Materia</th><th>Asignada a</th><th>Vence</th><th>Estado</th></tr></thead>
          <tbody>
            {tareas.map((t) => (
              <tr key={t.t} className="pClickable" onClick={() => ctx.toast('Abrir hilo de la tarea', 'clipboard')}>
                <td className="aTblName">{t.t}</td><td><span className="aTag">{t.m}</span></td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="aAvSm" style={{ width: 26, height: 26, fontSize: 10 }}>{t.i}</span><span style={{ fontSize: 12.5 }}>{t.d}</span></div></td>
                <td style={{ color: '#6b7280' }}>{t.v}</td><td>{estChip(t.est)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Encuentros + guardias ───────────────────────────────────
function VEncuentros({ ctx }) {
  const enc = [
    { f: '03 abr', tema: 'Teórico · Unidad 3', com: '1A', mod: 'Presencial', as: '38/45' },
    { f: '05 abr', tema: 'Práctico Integrador', com: '1A', mod: 'Virtual', as: '41/45' },
    { f: '10 abr', tema: 'Teórico · Unidad 4', com: '2A', mod: 'Presencial', as: '30/52' },
  ];
  const modTag = (m) => <span className="aTag" style={{ color: m === 'Virtual' ? '#0e7490' : '#4338ca', background: m === 'Virtual' ? '#ecfeff' : '#eef0ff', borderColor: 'transparent' }}>{m}</span>;
  return (
    <>
      <PageHead title="Encuentros y guardias" sub="Instancias de clase sincrónicas y guardias docentes.">
        <button className="aBtn pri" onClick={() => ctx.toast('Crear encuentro (recurrente o único)', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nuevo encuentro</button>
      </PageHead>
      <div className="aCard" style={{ marginBottom: 16 }}>
        <div className="aCardH"><h3><Icon name="layers" size={16} color="#4f46e5" /> Instancias de encuentro <span className="aCount">{enc.length}</span></h3>
          <button className="aBtn sm" onClick={() => ctx.toast('Bloque HTML copiado para el aula virtual', 'check')}><Icon name="download" size={13} /> Generar para LMS</button></div>
        <table className="aTbl">
          <thead><tr><th>Fecha</th><th>Tema</th><th>Comisión</th><th>Modalidad</th><th>Asistencia</th><th></th></tr></thead>
          <tbody>
            {enc.map((e) => (
              <tr key={e.f + e.tema}>
                <td className="num" style={{ fontWeight: 700 }}>{e.f}</td><td className="aTblName">{e.tema}</td>
                <td><span className="aTag">Com. {e.com}</span></td><td>{modTag(e.mod)}</td><td className="num">{e.as}</td>
                <td><span className="aToggleLink" onClick={() => ctx.toast('Editar instancia · pegar URL de grabación', 'calendar')}>Editar</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="clock" size={16} color="#4f46e5" /> Registro de guardias</h3><Btn sm icon="download">Exportar</Btn></div>
        <table className="aTbl">
          <thead><tr><th>Docente</th><th>Día</th><th>Horario</th><th>Modalidad</th><th>Estado</th></tr></thead>
          <tbody>
            {[['Lic. Bruno Paredes', 'BP', 'Lunes', '18:00 – 20:00', 'Virtual', 'Activa'], ['Ing. Carla Núñez', 'CN', 'Miércoles', '16:00 – 18:00', 'Presencial', 'Activa'], ['Lic. Valeria Roso', 'VR', 'Jueves', '18:00 – 20:00', 'Virtual', 'Pendiente']].map((g) => (
              <tr key={g[0] + g[2]}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{g[1]}</span><span className="aTblName">{g[0]}</span></div></td>
                <td style={{ fontWeight: 600 }}>{g[2]}</td><td className="num" style={{ color: '#6b7280' }}>{g[3]}</td><td>{modTag(g[4])}</td><td>{estChip(g[5])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Guardias (profesor) ─────────────────────────────────────
function VGuardias({ ctx }) {
  return (
    <>
      <PageHead title="Mis guardias" sub="Registrá las guardias de atención a alumnos que cubrís.">
        <button className="aBtn pri" onClick={() => ctx.toast('Registrar guardia', 'plus')}><Icon name="plus" size={15} color="#fff" /> Registrar guardia</button>
      </PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="clock" size={16} color="#4f46e5" /> Guardias registradas <span className="aCount">3</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Día</th><th>Horario</th><th>Materia</th><th>Modalidad</th><th>Estado</th></tr></thead>
          <tbody>
            {[['Lunes', '18:00 – 20:00', 'AM1', 'Virtual', 'Realizada'], ['Miércoles', '16:00 – 18:00', 'AM1', 'Presencial', 'Realizada'], ['Viernes', '14:00 – 16:00', 'AM1', 'Presencial', 'Pendiente']].map((g, i) => (
              <tr key={i}><td style={{ fontWeight: 600 }}>{g[0]}</td><td className="num" style={{ color: '#6b7280' }}>{g[1]}</td><td><span className="aTag">{g[2]}</span></td>
                <td><span className="aTag" style={{ color: g[3] === 'Virtual' ? '#0e7490' : '#4338ca', background: g[3] === 'Virtual' ? '#ecfeff' : '#eef0ff', borderColor: 'transparent' }}>{g[3]}</span></td>
                <td>{estChip(g[4] === 'Realizada' ? 'Hecha' : 'Pendiente')}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Coloquios (coordinador / profesor) ──────────────────────
function VColoquios({ ctx }) {
  return (
    <>
      <PageHead title="Coloquios" sub="Convocatorias, inscripciones, reservas de mesa y carga de notas.">
        <button className="aBtn pri" onClick={() => ctx.toast('Nueva convocatoria de coloquio', 'plus')}><Icon name="plus" size={15} color="#fff" /> Nueva convocatoria</button>
      </PageHead>
      <div className="aKpis" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {[['Convocatorias activas', '2', 'award', ''], ['Alumnos cargados', '42', 'users', ''], ['Reservas activas', '37', 'check', 'ok'], ['Notas registradas', '12', 'file', 'vio']].map(([l, v, ic, k]) => (
          <div key={l} className="aKpi"><div className={'aChip ' + k}><Icon name={ic} size={18} /></div><div className="aKv">{v}</div><div className="aKl">{l}</div></div>
        ))}
      </div>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="award" size={16} color="#4f46e5" /> Convocatorias <span className="aCount">{PD.coloquios.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Convocatoria</th><th>Materia</th><th style={{ textAlign: 'center' }}>Convocados</th><th style={{ textAlign: 'center' }}>Reservas</th><th style={{ textAlign: 'center' }}>Cupos libres</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {PD.coloquios.map((c) => (
              <tr key={c.m}>
                <td className="aTblName">{c.mesa}</td><td style={{ color: '#52596a' }}>{c.m}</td>
                <td style={{ textAlign: 'center' }} className="num">{c.insc}</td><td style={{ textAlign: 'center' }} className="num">{c.res}</td>
                <td style={{ textAlign: 'center' }} className="num">{c.cupos - c.res}</td><td>{estChip(c.est)}</td>
                <td><span className="aToggleLink" onClick={() => ctx.toast('Gestionar convocatoria y agenda de reservas', 'award')}>Gestionar</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Setup cuatrimestre (coordinador) ────────────────────────
function VSetup({ ctx }) {
  const steps = [['Seleccionar / crear cohorte', 'Indicá la cohorte del nuevo cuatrimestre.'], ['Clonar equipo docente', 'Copiá el equipo de una cohorte anterior.'], ['Ajustar asignaciones', 'Agregá o modificá asignaciones del equipo.'], ['Ajustar vigencias', 'Actualizá las fechas del equipo.'], ['Cargar programas', 'Registrá los programas de materias.'], ['Cargar fechas académicas', 'Registrá fechas de evaluaciones.'], ['Publicar aviso de bienvenida', 'Anunciá el inicio del período.']];
  return (
    <>
      <PageHead title="Setup de cuatrimestre" sub="Asistente guiado para dejar lista la cátedra del nuevo período." />
      <div style={{ display: 'grid', gridTemplateColumns: '330px 1fr', gap: 22 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.7px', textTransform: 'uppercase', color: '#9aa1ad', marginBottom: 12 }}>Progreso · paso 1 de 7</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map(([t, d], i) => (
              <div key={t} className="aCard" style={{ padding: '12px 14px', display: 'flex', gap: 12, borderColor: i === 0 ? '#c7ccf7' : '#eceef2', background: i === 0 ? '#f5f6ff' : '#fff', boxShadow: 'none' }}>
                <div style={{ width: 25, height: 25, borderRadius: '50%', flex: '0 0 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800, background: i === 0 ? '#4338ca' : '#f1f2f5', color: i === 0 ? '#fff' : '#9aa1ad' }}>{i + 1}</div>
                <div><div style={{ fontSize: 13, fontWeight: 700, color: i === 0 ? '#4338ca' : '#8a90a0' }}>{t}</div><div style={{ fontSize: 11.5, color: '#9aa1ad', marginTop: 2 }}>{d}</div></div>
              </div>
            ))}
          </div>
        </div>
        <div className="aCard" style={{ padding: 26, alignSelf: 'flex-start' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, background: '#eef0ff', color: '#4338ca', fontSize: 11.5, fontWeight: 700, padding: '5px 11px', borderRadius: 999, marginBottom: 14 }}><Icon name="calendar" size={13} /> Paso 1</div>
          <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 8px' }}>Seleccionar o crear cohorte</h2>
          <p style={{ fontSize: 13.5, color: '#6b7280', margin: '0 0 22px', lineHeight: 1.5, maxWidth: 480 }}>Indicá la cohorte para este cuatrimestre. Si ya existe, la reutilizamos.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, maxWidth: 540 }}>
            <div className="aField"><span className="aLabel">ID de cohorte</span><div className="aInput focus">coh-2026-1 <Icon name="check" size={14} color="#16a34a" /></div></div>
            <div className="aField"><span className="aLabel">Nombre / período</span><div className="aInput">2026 · 1.ºC <Icon name="chevd" size={14} color="#9aa1ad" /></div></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 16, fontSize: 12.5, color: '#16a34a', fontWeight: 600 }}><Icon name="check" size={15} color="#16a34a" /> Cohorte encontrada — 4 materias asociadas.</div>
          <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
            <button className="aBtn pri" onClick={() => ctx.toast('Paso 1 confirmado · pasá a clonar el equipo', 'check')}><Icon name="arrow" size={15} color="#fff" /> Confirmar y continuar</button>
            <Btn>Guardar y salir</Btn>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Equipos docentes (coordinador) ──────────────────────────
function VEquipos({ ctx }) {
  const roster = [
    ['Dra. Sofía Ledesma', 'SL', 'Profesora titular', 'Com. 1A · 1B', 'Vigente'], ['Lic. Bruno Paredes', 'BP', 'JTP', 'Com. 1A', 'Vigente'],
    ['Ing. Carla Núñez', 'CN', 'Ayudante 1.ª', 'Com. 1B', 'Vigente'], ['Prof. Diego Ferreyra', 'DF', 'Adjunto', 'Com. 2A', 'Vigente'],
    ['Lic. Valeria Roso', 'VR', 'JTP', 'Com. 2A', 'Vigente'], ['Ayud. Tomás Quiroga', 'TQ', 'Ayudante 2.ª', 'Com. 1A', 'Por vencer'],
  ];
  const rc = (r) => /titular|Adjunto/.test(r) ? ['#4338ca', '#eef0ff'] : r === 'JTP' ? ['#6d28d9', '#f3eefe'] : ['#0e7490', '#ecfeff'];
  return (
    <>
      <PageHead title="Equipos docentes" sub="Elegí el contexto y gestioná el equipo: asignaciones, roles y vigencias." />
      <ContextBar />
      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 16 }}>
        <div className="aCard">
          <div className="aCardH"><h3><Icon name="users" size={17} color="#4f46e5" /> Equipo actual <span className="aCount">{roster.length}</span></h3><span className="aToggleLink"><Icon name="download" size={14} /> Exportar</span></div>
          {roster.map((d) => { const [c, b] = rc(d[2]); return (
            <div key={d[0]} style={{ display: 'flex', alignItems: 'center', gap: 13, padding: '11px 18px', borderBottom: '1px solid var(--line2)' }}>
              <span className="aAvSm" style={{ width: 36, height: 36, fontSize: 12.5 }}>{d[1]}</span>
              <div style={{ flex: 1 }}><div style={{ fontSize: 13.5, fontWeight: 700 }}>{d[0]}</div><div style={{ fontSize: 11.5, color: '#6b7280' }}>{d[3]}</div></div>
              <Badge color={c} bg={b}>{d[2]}</Badge>{estChip(d[4])}
            </div>
          ); })}
        </div>
        <div className="aCard" style={{ padding: 18, alignSelf: 'flex-start' }}>
          <div style={{ fontSize: 13, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}><Icon name="plus" size={15} color="#4f46e5" /> Asignación masiva</div>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 13px' }}>Agregá docentes por nombre con rol y vigencia.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, border: '1.5px solid #e3e6ee', borderRadius: 11, padding: 8, marginBottom: 11 }}>
            <span className="aTag" style={{ background: '#eef0ff', color: '#4338ca' }}>Lic. Mauro Gil</span><span className="aTag" style={{ background: '#eef0ff', color: '#4338ca' }}>Prof. Ana Vera</span>
            <span style={{ fontSize: 12.5, color: '#9aa1ad', padding: '5px 4px' }}>Buscar docente…</span>
          </div>
          <button className="aBtn pri" style={{ width: '100%' }} onClick={() => ctx.toast('2 docentes asignados', 'plus')}><Icon name="plus" size={15} color="#fff" /> Asignar 2 docentes</button>
          <div className="pHL pClickable" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 13, border: '1.5px dashed #d4d8e4', borderRadius: 12, marginTop: 14 }} onClick={() => ctx.toast('Equipo clonado desde 2025 · 2.ºC', 'layers')}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#f3eefe', color: '#6d28d9', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto' }}><Icon name="layers" size={18} /></div>
            <div style={{ flex: 1 }}><div style={{ fontSize: 13, fontWeight: 700 }}>Clonar desde 2025 · 2.ºC</div><div style={{ fontSize: 11.5, color: '#6b7280' }}>6 docentes · mismos roles</div></div>
            <Icon name="arrow" size={16} color="#6d28d9" />
          </div>
        </div>
      </div>
    </>
  );
}

// ── Auditoría (coordinador) ─────────────────────────────────
function VAuditoria() {
  const log = [
    ['Mariana Suárez', 'MS', 'Asignó equipo docente', 'crear', 'Equipo · AM1 / 2026-1', '02 abr · 14:32'],
    ['Sofía Ledesma', 'SL', 'Cargó notas Parcial 1', 'editar', 'Calificaciones · Com. 1A', '02 abr · 11:10'],
    ['Sistema', 'SY', 'Importó padrón', 'crear', 'Padrón · 142 filas', '01 abr · 09:02'],
    ['Bruno Paredes', 'BP', 'Editó vigencia de guardia', 'editar', 'Guardia · Lunes 18h', '31 mar · 18:45'],
    ['Mariana Suárez', 'MS', 'Publicó aviso', 'crear', 'Aviso · Inicio cuatrimestre', '01 mar · 08:00'],
  ];
  const tc = { crear: ['#16a34a', '#ecfdf3'], editar: ['#4338ca', '#eef0ff'], borrar: ['#e7515a', '#fff1f0'] };
  return (
    <>
      <PageHead title="Auditoría" sub="Registro inmutable de acciones del sistema. Solo lectura."><Btn icon="download">Exportar log</Btn></PageHead>
      <div className="aCard">
        <div className="aCardH"><h3><Icon name="shield" size={16} color="#4f46e5" /> Eventos recientes <span className="aCount">{log.length}</span></h3></div>
        <table className="aTbl">
          <thead><tr><th>Usuario</th><th>Acción</th><th>Entidad</th><th>Fecha y hora</th></tr></thead>
          <tbody>
            {log.map((l, i) => { const [c, b] = tc[l[3]]; return (
              <tr key={i}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="aAvSm">{l[1]}</span><span className="aTblName">{l[0]}</span></div></td>
                <td><Badge color={c} bg={b}>{l[2]}</Badge></td><td style={{ color: '#52596a' }}>{l[4]}</td><td className="num" style={{ color: '#6b7280' }}>{l[5]}</td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Inbox / mensajes (todos) ────────────────────────────────
function VInbox() {
  const [open, setOpen] = React.useState(0);
  const msgs = [
    { de: 'Coordinación', av: 'MS', asunto: 'Recordatorio: carga de notas', prev: 'Hola, te recuerdo que el cierre de notas del Parcial 1…', f: 'hace 2 h', cuerpo: 'Hola, te recuerdo que el cierre de notas del Parcial 1 es el viernes 12. Cualquier duda, avisame. Saludos, Mariana.' },
    { de: 'Secretaría académica', av: 'SY', asunto: 'Actualización de programas', prev: 'Se actualizó la plantilla de programas para 2026…', f: 'ayer', cuerpo: 'Se actualizó la plantilla de programas para 2026. Por favor revisá y resubí el programa de tu materia.' },
    { de: 'Lic. Bruno Paredes', av: 'BP', asunto: 'Consulta sobre guardia', prev: '¿Podemos coordinar la guardia del jueves?…', f: 'mar', cuerpo: '¿Podemos coordinar la guardia del jueves? Tengo un cruce de horario con la consulta de PR1.' },
  ];
  return (
    <>
      <PageHead title="Mensajes" sub="Bandeja interna entre usuarios del sistema." />
      <div className="aCard" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', overflow: 'hidden', minHeight: 420 }}>
        <div style={{ borderRight: '1px solid var(--line)' }}>
          {msgs.map((m, i) => (
            <div key={i} className="pHL pClickable" onClick={() => setOpen(i)} style={{ display: 'flex', gap: 11, padding: '13px 16px', borderBottom: '1px solid var(--line2)', background: open === i ? '#f5f6ff' : '#fff' }}>
              <span className="aAvSm" style={{ width: 34, height: 34 }}>{m.av}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><span style={{ fontSize: 13, fontWeight: 700 }}>{m.de}</span><span style={{ fontSize: 11, color: '#9aa1ad' }}>{m.f}</span></div>
                <div style={{ fontSize: 12.5, fontWeight: 600, marginTop: 1 }}>{m.asunto}</div>
                <div style={{ fontSize: 11.5, color: '#9aa1ad', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.prev}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ padding: 24, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 17, fontWeight: 800 }}>{msgs[open].asunto}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '12px 0 18px' }}><span className="aAvSm" style={{ width: 32, height: 32 }}>{msgs[open].av}</span><div><div style={{ fontSize: 13, fontWeight: 700 }}>{msgs[open].de}</div><div style={{ fontSize: 11.5, color: '#9aa1ad' }}>{msgs[open].f}</div></div></div>
          <div style={{ fontSize: 13.5, color: '#374151', lineHeight: 1.65, flex: 1 }}>{msgs[open].cuerpo}</div>
          <div style={{ display: 'flex', gap: 10, marginTop: 18, borderTop: '1px solid var(--line)', paddingTop: 16 }}>
            <div className="aInput ph" style={{ flex: 1 }}>Escribí una respuesta…</div>
            <Btn pri icon="mail">Responder</Btn>
          </div>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { V_GEST: { aprob: VAprob, avisos: VAvisos, comuni: VComuni, tareas: VTareas, encuentros: VEncuentros, guardias: VGuardias, coloquios: VColoquios, setup: VSetup, equipos: VEquipos, auditoria: VAuditoria, inbox: VInbox } });
