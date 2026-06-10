// Vistas del ALUMNO (content-only). Incluye reservar coloquio y acuse de avisos.

// ── Mi estado académico ─────────────────────────────────────
function AEstado({ ctx }) {
  const ms = PD.alumnoMaterias;
  const condCol = (c) => c === 'Promociona' ? ['#16a34a', '#ecfdf3'] : c === 'Regular' ? ['#4338ca', '#eef0ff'] : ['#e7515a', '#fff1f0'];
  const enRiesgo = ms.filter((m) => m.cond === 'Riesgo').length;
  return (
    <>
      <div style={{ fontSize: 23, fontWeight: 800, letterSpacing: '-.6px' }}>Hola, Joaquín 👋</div>
      <div style={{ color: '#6b7280', fontSize: 13.5, margin: '3px 0 20px' }}>Tu estado en las 4 materias de este cuatrimestre · Ing. en Sistemas</div>

      <div className="aKpis" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {[['Materias', '4', 'book', ''], ['Al día', '2', 'check', 'ok'], ['En riesgo', enRiesgo, 'alert', 'warn'], ['Próxima evaluación', '12 abr', 'calendar', 'amber']].map(([l, v, ic, k]) => (
          <div key={l} className="aKpi"><div className={'aChip ' + k}><Icon name={ic} size={18} /></div><div className="aKv" style={{ fontSize: k === 'amber' ? 21 : 26, color: k === 'warn' ? '#e7515a' : '#1d2330' }}>{v}</div><div className="aKl">{l}</div></div>
        ))}
      </div>

      {ms.some((m) => m.alerta) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18, background: '#fff7ed', border: '1px solid #fde4c8', borderRadius: 12, padding: '13px 16px' }}>
          <Icon name="alert" size={18} color="#d97706" />
          <div style={{ flex: 1, fontSize: 13, color: '#9a3412' }}>Tenés <b>actividades pendientes</b> en Análisis Matemático I y Física I. Revisá las fechas para regularizar.</div>
          <button className="aBtn pri sm" onClick={() => ctx.setView('coloquios')}>Reservar coloquio</button>
        </div>
      )}

      <h2 style={{ fontSize: 16, fontWeight: 800, marginBottom: 14 }}>Mis materias</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {ms.map((m) => { const [c, b] = condCol(m.cond); const pct = Math.round(m.cum / m.tot * 100); return (
          <div key={m.sigla} className="aCard pHL pClickable" onClick={() => ctx.setView('materias')} style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 13 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(150deg,#eef0ff,#e7e9ff)', color: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, flex: '0 0 auto' }}>{m.sigla}</div>
              <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 14.5, fontWeight: 800 }}>{m.nombre}</div><div style={{ fontSize: 12, color: '#6b7280' }}>Comisión {m.com}</div></div>
              <Badge color={c} bg={b}>{m.cond}</Badge>
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              <div><span style={{ fontSize: 10.5, color: '#9aa1ad', fontWeight: 600, textTransform: 'uppercase' }}>Parcial 1</span><div style={{ fontSize: 16, fontWeight: 800, color: m.p1 >= 6 ? '#16a34a' : m.p1 >= 4 ? '#d97706' : '#e7515a' }}>{m.p1 ?? '—'}</div></div>
              <div><span style={{ fontSize: 10.5, color: '#9aa1ad', fontWeight: 600, textTransform: 'uppercase' }}>Parcial 2</span><div style={{ fontSize: 16, fontWeight: 800, color: m.p2 == null ? '#c2c7d2' : m.p2 >= 6 ? '#16a34a' : '#d97706' }}>{m.p2 ?? '—'}</div></div>
              <div style={{ flex: 1 }}><span style={{ fontSize: 10.5, color: '#9aa1ad', fontWeight: 600, textTransform: 'uppercase' }}>Avance</span><div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}><span className="aBar" style={{ flex: 1 }}><span className="aBarF" style={{ display: 'block', height: '100%', width: pct + '%', background: m.cond === 'Riesgo' ? '#e7515a' : 'linear-gradient(90deg,#6366f1,#4338ca)' }} /></span><span className="num" style={{ fontSize: 11.5 }}>{m.cum}/{m.tot}</span></div></div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, borderTop: '1px solid var(--line)', paddingTop: 11, fontSize: 12, color: m.alerta ? '#9a3412' : '#6b7280', fontWeight: 600 }}>
              <Icon name={m.alerta ? 'alert' : 'calendar'} size={13} color={m.alerta ? '#d97706' : '#9aa1ad'} /> {m.alerta || `Próximo: ${m.prox}`}
            </div>
          </div>
        ); })}
      </div>
    </>
  );
}

// ── Mis materias (detalle alumno) ───────────────────────────
function AMaterias() {
  const ms = PD.alumnoMaterias;
  const condCol = (c) => c === 'Promociona' ? ['#16a34a', '#ecfdf3'] : c === 'Regular' ? ['#4338ca', '#eef0ff'] : ['#e7515a', '#fff1f0'];
  return (
    <>
      <PageHead title="Mis materias" sub="Detalle de tus calificaciones y próximas instancias." />
      <div className="aCard">
        <table className="aTbl">
          <thead><tr><th>Materia</th><th>Comisión</th><th style={{ textAlign: 'center' }}>Parcial 1</th><th style={{ textAlign: 'center' }}>Parcial 2</th><th style={{ width: 160 }}>Avance</th><th>Próximo</th><th>Condición</th></tr></thead>
          <tbody>
            {ms.map((m) => { const [c, b] = condCol(m.cond); const pct = Math.round(m.cum / m.tot * 100); const sc = (v) => v == null ? <span style={{ color: '#c2c7d2' }}>—</span> : <b style={{ color: v >= 6 ? '#16a34a' : v >= 4 ? '#d97706' : '#e7515a' }}>{v}</b>; return (
              <tr key={m.sigla}>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><div style={{ width: 30, height: 30, borderRadius: 8, background: '#eef0ff', color: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 11 }}>{m.sigla}</div><span className="aTblName">{m.nombre}</span></div></td>
                <td><span className="aTag">Com. {m.com}</span></td>
                <td style={{ textAlign: 'center' }}>{sc(m.p1)}</td><td style={{ textAlign: 'center' }}>{sc(m.p2)}</td>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="aBar" style={{ flex: 1 }}><span className="aBarF" style={{ display: 'block', height: '100%', width: pct + '%' }} /></span><span className="num" style={{ fontSize: 12 }}>{m.cum}/{m.tot}</span></div></td>
                <td style={{ color: '#6b7280' }}>{m.prox}</td><td><Badge color={c} bg={b}>{m.cond}</Badge></td>
              </tr>
            ); })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Coloquios · reservar turno (alumno) ─────────────────────
function AColoquios({ ctx }) {
  const [reserva, setReserva] = React.useState(null); // {sigla, dia, hora}
  const [modal, setModal] = React.useState(null); // turno candidato
  const confirmar = () => { setReserva({ ...modal }); setModal(null); ctx.toast(`Turno reservado · ${modal.dia} ${modal.hora}`, 'check'); };
  return (
    <>
      <PageHead title="Coloquios" sub="Reservá tu turno para las instancias de evaluación habilitadas." />
      {reserva && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18, background: '#ecfdf3', border: '1px solid #bbf3d0', borderRadius: 12, padding: '13px 16px' }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: '#16a34a', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto' }}><Icon name="check" size={17} stroke={2.4} /></div>
          <div style={{ flex: 1, fontSize: 13, color: '#166534' }}>Reservaste <b>{reserva.sigla}</b> · {reserva.dia} a las {reserva.hora}.</div>
          <button className="aBtn sm" onClick={() => { setReserva(null); ctx.toast('Reserva cancelada', 'x'); }}>Cancelar reserva</button>
        </div>
      )}
      {PD.coloquios.map((c) => (
        <div key={c.sigla} className="aCard" style={{ marginBottom: 16 }}>
          <div className="aCardH"><h3><Icon name="award" size={16} color="#4f46e5" /> {c.mesa} · {c.sigla}</h3><span className="aTag">{c.cupos - c.res} cupos libres</span></div>
          <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
            {c.turnos.map((t, i) => {
              const full = t.libres === 0;
              const mine = reserva && reserva.sigla === c.sigla && reserva.dia === t.dia && reserva.hora === t.hora;
              return (
                <div key={i} className={!full && !mine ? 'pHL pClickable' : ''} onClick={() => !full && !mine && setModal({ sigla: c.sigla, dia: t.dia, hora: t.hora })}
                  style={{ border: '1.5px solid ' + (mine ? '#16a34a' : full ? '#eceef2' : '#e3e6ee'), borderRadius: 12, padding: '13px 14px', background: mine ? '#ecfdf3' : full ? '#fafafa' : '#fff', opacity: full ? .6 : 1, cursor: full ? 'not-allowed' : 'pointer' }}>
                  <div style={{ fontSize: 13, fontWeight: 800 }}>{t.dia}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{t.hora} h</div>
                  <div style={{ marginTop: 9, fontSize: 11.5, fontWeight: 700, color: mine ? '#16a34a' : full ? '#9aa1ad' : '#4338ca' }}>
                    {mine ? '✓ Tu turno' : full ? 'Sin cupos' : `${t.libres} cupos`}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
      {modal && (
        <Modal title="Confirmar reserva" sub={`${modal.sigla} · ${modal.dia} a las ${modal.hora} h`} max={440} onClose={() => setModal(null)}
          footer={<><button className="aBtn" onClick={() => setModal(null)}>Volver</button><button className="aBtn pri" onClick={confirmar}><Icon name="check" size={14} color="#fff" /> Confirmar turno</button></>}>
          <div style={{ fontSize: 13.5, color: '#374151', lineHeight: 1.6 }}>Vas a reservar tu turno de coloquio de <b>{modal.sigla}</b> para el <b>{modal.dia}</b> a las <b>{modal.hora} h</b>. Podés cancelarlo hasta 24 h antes.</div>
        </Modal>
      )}
    </>
  );
}

// ── Avisos · con acuse de recibo (alumno) ───────────────────
function AAvisos({ ctx }) {
  const [acked, setAcked] = React.useState({});
  const sevCol = (s) => s === 'Crítico' ? ['#e7515a', '#fff1f0'] : s === 'Advertencia' ? ['#d97706', '#fef6e7'] : ['#4338ca', '#eef0ff'];
  return (
    <>
      <PageHead title="Avisos" sub="Novedades de la institución y tu cátedra." />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {PD.avisos.map((a, i) => { const [c, b] = sevCol(a.sev); const needAck = a.ack && !acked[i]; return (
          <div key={i} className="aCard" style={{ padding: 18, borderColor: needAck ? '#fde4c8' : '#eceef2' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 13 }}>
              <div style={{ width: 38, height: 38, borderRadius: 10, background: b, color: c, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto' }}><Icon name={a.sev === 'Info' ? 'bell' : 'alert'} size={18} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' }}><span style={{ fontSize: 14.5, fontWeight: 800 }}>{a.t}</span><Badge color={c} bg={b}>{a.sev}</Badge></div>
                <div style={{ fontSize: 13, color: '#52596a', margin: '7px 0 0', lineHeight: 1.55 }}>{a.cuerpo}</div>
                <div style={{ fontSize: 11.5, color: '#9aa1ad', marginTop: 9 }}>{a.de} · {a.f}</div>
              </div>
            </div>
            {a.ack && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid var(--line)', marginTop: 14, paddingTop: 13 }}>
                {acked[i]
                  ? <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5, color: '#16a34a', fontWeight: 700 }}><Icon name="check" size={15} color="#16a34a" stroke={2.4} /> Lectura confirmada</span>
                  : <><span style={{ fontSize: 12, color: '#9a3412' }}>Requiere acuse de recibo</span><button className="aBtn pri sm" onClick={() => { setAcked((s) => ({ ...s, [i]: true })); ctx.toast('Lectura confirmada', 'check'); }}><Icon name="check" size={14} color="#fff" /> Confirmar lectura</button></>}
              </div>
            )}
          </div>
        ); })}
      </div>
    </>
  );
}

Object.assign(window, { V_ALU: { estado: AEstado, materias: AMaterias, coloquios: AColoquios, avisos: AAvisos } });
