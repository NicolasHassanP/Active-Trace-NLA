// Sistema de diseño "A · Índigo pulido": shell + primitivos reutilizables.
// CSS inyectado una sola vez (global). Componentes exportados a window.

(function injectACss() {
  if (document.getElementById('a-ds')) return;
  const s = document.createElement('style');
  s.id = 'a-ds';
  s.textContent = `
  .aApp{--ink:#1d2330;--mut:#6b7280;--faint:#9aa1ad;--line:#eceef2;--line2:#f3f4f7;--bg:#f7f8fb;
    --ind:#4f46e5;--ind2:#4338ca;--ok:#16a34a;--warn:#e7515a;--amber:#d97706;--vio:#6d28d9;--cyan:#0e7490;
    display:flex;height:980px;background:var(--bg);font-family:'Manrope',system-ui,sans-serif;color:var(--ink);}
  .aApp *{box-sizing:border-box;}
  .aApp ::-webkit-scrollbar{width:0;height:0;}
  /* sidebar */
  .aSide{width:250px;flex:0 0 250px;background:#fff;border-right:1px solid var(--line);display:flex;flex-direction:column;padding:22px 14px 16px;}
  .aBrand{display:flex;align-items:center;gap:9px;padding:0 8px 16px;}
  .aLogo{width:30px;height:30px;border-radius:9px;background:linear-gradient(150deg,#6366f1,#4338ca);display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:0 3px 8px rgba(67,56,202,.35);}
  .aBrand b{font-size:16px;font-weight:800;letter-spacing:-.4px;}
  .aBrand b span{color:var(--ind);}
  .aNav{flex:1;overflow:hidden;}
  .aGrp{font-size:10.5px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:#9aa1ad;padding:13px 10px 5px;}
  .aItem{display:flex;align-items:center;gap:11px;padding:7.5px 10px;border-radius:9px;color:#4b5563;font-size:13.5px;font-weight:600;cursor:pointer;margin-bottom:1px;}
  .aItem:hover{background:#f4f4f8;color:var(--ink);}
  .aItem.on{background:#eef0ff;color:var(--ind2);}
  .aItem.on svg{color:var(--ind);}
  .aItem svg{color:#9aa1ad;flex:0 0 auto;}
  .aUser{display:flex;align-items:center;gap:10px;padding:10px;border-radius:11px;border:1px solid var(--line);}
  .aAv{width:34px;height:34px;border-radius:50%;background:linear-gradient(150deg,#818cf8,#4338ca);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex:0 0 auto;}
  /* main */
  .aMain{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
  .aTop{height:60px;flex:0 0 60px;background:rgba(255,255,255,.85);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;padding:0 28px;}
  .aPill{display:flex;align-items:center;gap:7px;background:#eef0ff;color:var(--ind2);font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:999px;white-space:nowrap;}
  .aSearch{flex:1;max-width:340px;display:flex;align-items:center;gap:9px;background:#f4f5f8;border:1px solid var(--line);border-radius:10px;padding:8px 12px;color:#9aa1ad;font-size:13px;}
  .aIco{width:36px;height:36px;border-radius:10px;border:1px solid var(--line);background:#fff;display:flex;align-items:center;justify-content:center;color:#6b7280;position:relative;cursor:pointer;}
  .aIco:hover{background:#f6f7fb;}
  .aNdot{position:absolute;top:8px;right:9px;width:7px;height:7px;border-radius:50%;background:#ef4444;border:1.5px solid #fff;}
  .aBody{flex:1;overflow:hidden;padding:24px 28px;}
  /* page head */
  .aPageHead{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:20px;}
  .aH1{font-size:22px;font-weight:800;letter-spacing:-.6px;}
  .aHsub{color:var(--mut);font-size:13.5px;margin-top:3px;max-width:640px;}
  .aActions{display:flex;gap:9px;align-items:center;flex:0 0 auto;}
  /* buttons */
  .aBtn{display:inline-flex;align-items:center;justify-content:center;gap:7px;font-size:13px;font-weight:700;padding:9px 14px;border-radius:10px;border:1px solid var(--line);background:#fff;color:#3a4253;cursor:pointer;white-space:nowrap;}
  .aBtn:hover{background:#f6f7fb;}
  .aBtn.pri{background:var(--ind2);color:#fff;border-color:var(--ind2);}
  .aBtn.pri:hover{background:#3730a3;}
  .aBtn.sm{padding:7px 11px;font-size:12.5px;border-radius:9px;}
  .aBtn svg{flex:0 0 auto;}
  /* cards */
  .aCard{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 1px 2px rgba(16,24,40,.04);}
  .aCardH{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid var(--line);}
  .aCardH h3{font-size:14.5px;font-weight:800;display:flex;align-items:center;gap:9px;}
  .aCardB{padding:18px;}
  .aCount{font-size:11.5px;font-weight:700;color:var(--ind2);background:#eef0ff;padding:3px 9px;border-radius:999px;}
  /* kpis */
  .aKpis{display:grid;gap:14px;margin-bottom:22px;}
  .aKpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:15px 16px;box-shadow:0 1px 2px rgba(16,24,40,.04);}
  .aChip{width:34px;height:34px;border-radius:10px;background:#eef0ff;color:var(--ind);display:flex;align-items:center;justify-content:center;}
  .aChip.warn{background:#fff1f0;color:var(--warn);}
  .aChip.ok{background:#ecfdf3;color:var(--ok);}
  .aChip.amber{background:#fef6e7;color:var(--amber);}
  .aChip.vio{background:#f3eefe;color:var(--vio);}
  .aKv{font-size:26px;font-weight:800;letter-spacing:-1px;margin-top:11px;}
  .aKl{font-size:12.5px;color:var(--mut);font-weight:600;margin-top:1px;}
  .aKs{font-size:11.5px;color:#9aa1ad;margin-top:7px;}
  /* tabs / segmented */
  .aTabs{display:flex;gap:7px;align-items:center;}
  .aTab{font-size:12.5px;font-weight:700;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:#fff;color:#6b7280;cursor:pointer;display:flex;align-items:center;gap:5px;}
  .aTab.on{background:var(--ind2);color:#fff;border-color:var(--ind2);}
  /* tags + badges */
  .aTag{font-size:11.5px;font-weight:600;color:#52596a;background:#f5f6f9;border:1px solid var(--line);padding:4px 9px;border-radius:7px;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;}
  .aBadge{font-size:11px;font-weight:700;padding:4px 9px;border-radius:999px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;}
  /* table */
  .aTblWrap{width:100%;overflow:hidden;}
  .aTbl{width:100%;border-collapse:collapse;font-size:13px;}
  .aTbl th{text-align:left;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:var(--faint);padding:11px 14px;border-bottom:1px solid var(--line);white-space:nowrap;}
  .aTbl td{padding:11px 14px;border-bottom:1px solid var(--line2);vertical-align:middle;}
  .aTbl tbody tr:last-child td{border-bottom:none;}
  .aTbl tbody tr:hover{background:#fafbff;}
  .aTbl .num{font-variant-numeric:tabular-nums;font-weight:700;}
  .aTblName{font-weight:700;}
  .aAvSm{width:30px;height:30px;border-radius:50%;background:linear-gradient(150deg,#a5b4fc,#6366f1);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex:0 0 auto;}
  /* progress */
  .aBar{height:6px;border-radius:99px;background:#eef0f3;overflow:hidden;}
  .aBarF{height:100%;border-radius:99px;background:linear-gradient(90deg,#6366f1,#4338ca);}
  .aBarMini{height:6px;width:90px;border-radius:99px;background:#eef0f3;overflow:hidden;display:inline-block;vertical-align:middle;}
  /* forms */
  .aField{display:flex;flex-direction:column;gap:6px;}
  .aLabel{font-size:11.5px;font-weight:700;color:var(--mut);}
  .aLabel .opt{color:#9aa1ad;font-weight:500;}
  .aInput{border:1.5px solid #e3e6ee;border-radius:10px;padding:9px 12px;font-size:13px;font-family:inherit;color:var(--ink);background:#fff;display:flex;align-items:center;justify-content:space-between;gap:8px;}
  .aInput.ph{color:var(--faint);}
  .aInput.focus{border-color:var(--ind);box-shadow:0 0 0 3px rgba(79,70,229,.1);}
  .aCombo{display:flex;align-items:center;gap:10px;border:1.5px solid #e3e6ee;border-radius:11px;padding:9px 12px;cursor:pointer;background:#fff;}
  .aCombo.act{border-color:var(--ind);box-shadow:0 0 0 3px rgba(79,70,229,.1);}
  .aComboAv{width:30px;height:30px;border-radius:8px;background:#eef0ff;color:var(--ind2);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:11px;flex:0 0 auto;}
  .aComboM{flex:1;min-width:0;}
  .aComboM b{font-size:13.5px;font-weight:700;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .aComboM span{font-size:11px;color:var(--faint);font-family:ui-monospace,monospace;}
  .aToggleLink{font-size:12px;font-weight:700;color:var(--ind);cursor:pointer;display:inline-flex;align-items:center;gap:6px;}
  .aCheck{width:18px;height:18px;border-radius:5px;border:1.5px solid #cbd0db;background:#fff;display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;cursor:pointer;}
  .aCheck.on{background:var(--ind2);border-color:var(--ind2);color:#fff;}
  /* empty */
  .aEmpty{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:46px 20px;color:var(--faint);}
  .aEmpty .ic{width:54px;height:54px;border-radius:14px;background:#f3f4f7;display:flex;align-items:center;justify-content:center;color:#c2c7d2;margin-bottom:14px;}
  .aEmpty b{color:#5a6172;font-size:14px;}
  .aEmpty p{font-size:12.5px;margin:5px 0 0;}
  /* misc */
  .aSplit{display:grid;gap:16px;}
  .aDot{width:7px;height:7px;border-radius:50%;flex:0 0 auto;}
  .aHelp{font-size:12.5px;color:var(--mut);font-style:italic;}
  .aDivute{height:1px;background:var(--line);margin:16px 0;}
  `;
  document.head.appendChild(s);
})();

function AppShellA({ active, children }) {
  return (
    <div className="aApp">
      <aside className="aSide">
        <div className="aBrand">
          <div className="aLogo"><Icon name="activity" size={17} color="#fff" stroke={2.2} /></div>
          <b>activia<span>·</span>trace</b>
        </div>
        <nav className="aNav">
          {ACT.nav.map((g) => (
            <div key={g.group}>
              <div className="aGrp">{g.group}</div>
              {g.items.map(([label, ic]) => (
                <div key={label} className={'aItem' + (label === active ? ' on' : '')}>
                  <Icon name={ic} size={17} /> {label}
                </div>
              ))}
            </div>
          ))}
        </nav>
        <div className="aUser">
          <div className="aAv">{ACT.prof.inicial}</div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ACT.prof.nombre}</div>
            <div style={{ fontSize: 11, color: '#9aa1ad', whiteSpace: 'nowrap' }}>{ACT.prof.rol}</div>
          </div>
        </div>
      </aside>
      <div className="aMain">
        <header className="aTop">
          <div className="aPill"><Icon name="calendar" size={14} /> {ACT.cuatri}</div>
          <div className="aSearch"><Icon name="search" size={16} /> Buscar materia, comisión o alumno…</div>
          <div style={{ flex: 1 }} />
          <div className="aIco"><Icon name="bell" size={17} /><span className="aNdot" /></div>
          <div className="aIco"><Icon name="grid" size={17} /></div>
        </header>
        <div className="aBody">{children}</div>
      </div>
    </div>
  );
}

function PageHead({ title, sub, children }) {
  return (
    <div className="aPageHead">
      <div>
        <div className="aH1">{title}</div>
        {sub && <div className="aHsub">{sub}</div>}
      </div>
      {children && <div className="aActions">{children}</div>}
    </div>
  );
}

function Btn({ children, pri, sm, icon, style }) {
  return <button className={'aBtn' + (pri ? ' pri' : '') + (sm ? ' sm' : '')} style={style}>
    {icon && <Icon name={icon} size={sm ? 14 : 15} color={pri ? '#fff' : 'currentColor'} />}{children}
  </button>;
}

function Badge({ children, color, bg }) {
  return <span className="aBadge" style={{ color, background: bg }}>{children}</span>;
}

function Combo({ label, av, name, id, act, small }) {
  return (
    <div className="aField">
      <span className="aLabel">{label}</span>
      <div className={'aCombo' + (act ? ' act' : '')}>
        <div className="aComboAv" style={small ? { fontSize: 10 } : null}>{av}</div>
        <div className="aComboM"><b>{name}</b><span>{id}</span></div>
        <Icon name="chevd" size={16} color="#9aa1ad" />
      </div>
    </div>
  );
}

function Empty({ icon = 'clipboard', title, children }) {
  return (
    <div className="aEmpty">
      <div className="ic"><Icon name={icon} size={26} stroke={1.6} /></div>
      <b>{title}</b>
      {children && <p>{children}</p>}
    </div>
  );
}

function Check({ on }) {
  return <span className={'aCheck' + (on ? ' on' : '')}>{on && <Icon name="check" size={12} color="#fff" stroke={2.4} />}</span>;
}

// estado → [color, bg]
const EST = {
  Vigente: ['#16a34a', '#ecfdf3'], 'Por vencer': ['#d97706', '#fef6e7'], Vencido: ['#e7515a', '#fff1f0'],
  Activa: ['#16a34a', '#ecfdf3'], Activo: ['#16a34a', '#ecfdf3'], Pendiente: ['#d97706', '#fef6e7'],
  'En curso': ['#4338ca', '#eef0ff'], Hecha: ['#16a34a', '#ecfdf3'], Borrador: ['#6b7280', '#f1f2f5'],
  Publicado: ['#16a34a', '#ecfdf3'], Cerrada: ['#6b7280', '#f1f2f5'], Abierta: ['#16a34a', '#ecfdf3'],
  Aprobado: ['#16a34a', '#ecfdf3'], Pagado: ['#16a34a', '#ecfdf3'], Atrasado: ['#e7515a', '#fff1f0'],
  Inactivo: ['#6b7280', '#f1f2f5'], Suspendido: ['#e7515a', '#fff1f0'],
};
function estChip(e) { const [c, b] = EST[e] || ['#6b7280', '#f1f2f5']; return <Badge color={c} bg={b}><span className="aDot" style={{ background: c }} />{e}</Badge>; }

Object.assign(window, { AppShellA, PageHead, Btn, Badge, Combo, Empty, Check, estChip, EST });
