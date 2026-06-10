// App principal: login, router por rol, toasts.
(function injectLoginCss() {
  if (document.getElementById('p-login')) return;
  const s = document.createElement('style');
  s.id = 'p-login';
  s.textContent = `
  .lgWrap{--ind:#4f46e5;--ind2:#4338ca;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:radial-gradient(1200px 600px at 70% -10%,#eef0ff,transparent),linear-gradient(180deg,#f7f8fb,#eef0f6);
    font-family:'Manrope',system-ui,sans-serif;color:#1d2330;padding:24px;}
  .lgCard{width:100%;max-width:420px;background:#fff;border:1px solid #eceef2;border-radius:20px;
    box-shadow:0 30px 80px rgba(16,24,40,.14);padding:32px 30px;}
  .lgBrand{display:flex;align-items:center;gap:10px;margin-bottom:22px;}
  .lgLogo{width:34px;height:34px;border-radius:10px;background:linear-gradient(150deg,#6366f1,#4338ca);display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:0 4px 10px rgba(67,56,202,.4);}
  .lgBrand b{font-size:18px;font-weight:800;letter-spacing:-.4px;}
  .lgBrand b span{color:var(--ind);}
  .lgH{font-size:21px;font-weight:800;letter-spacing:-.5px;}
  .lgP{font-size:13px;color:#6b7280;margin:4px 0 22px;}
  .lgL{font-size:11.5px;font-weight:700;color:#6b7280;display:block;margin-bottom:6px;}
  .lgIn{width:100%;border:1.5px solid #e3e6ee;border-radius:11px;padding:11px 13px;font-size:13.5px;font-family:inherit;color:#1d2330;margin-bottom:14px;background:#fff;}
  .lgIn:focus{outline:none;border-color:var(--ind);box-shadow:0 0 0 3px rgba(79,70,229,.1);}
  .lgBtn{width:100%;border:none;background:var(--ind2);color:#fff;font-weight:700;font-size:14px;padding:12px;border-radius:11px;cursor:pointer;font-family:inherit;}
  .lgBtn:hover{background:#3730a3;}
  .lgDiv{display:flex;align-items:center;gap:12px;margin:22px 0 16px;color:#9aa1ad;font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;}
  .lgDiv::before,.lgDiv::after{content:'';flex:1;height:1px;background:#eceef2;}
  .lgRoles{display:flex;flex-direction:column;gap:8px;}
  .lgRole{display:flex;align-items:center;gap:11px;padding:11px 13px;border:1px solid #eceef2;border-radius:12px;cursor:pointer;background:#fff;transition:border-color .12s,background .12s;}
  .lgRole:hover{border-color:#c7ccf7;background:#fafbff;}
  .lgRoleAv{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:12px;flex:0 0 auto;}
  .lgFoot{text-align:center;font-size:11.5px;color:#9aa1ad;margin-top:18px;}
  `;
  document.head.appendChild(s);
})();

function Login({ onLogin }) {
  return (
    <div className="lgWrap">
      <div className="lgCard">
        <div className="lgBrand"><div className="lgLogo"><Icon name="activity" size={19} color="#fff" stroke={2.2} /></div><b>activia<span>·</span>trace</b></div>
        <div className="lgH">Iniciá sesión</div>
        <div className="lgP">Gestión académica y trazabilidad · Regional Córdoba</div>
        <label className="lgL">Email</label>
        <input className="lgIn" defaultValue="m.suarez@activia.edu.ar" />
        <label className="lgL">Contraseña</label>
        <input className="lgIn" type="password" defaultValue="123456789" />
        <button className="lgBtn" onClick={() => onLogin('COORDINADOR')}>Ingresar</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 12, fontSize: 11.5, color: '#9aa1ad' }}><Icon name="shield" size={13} /> Verificación en dos pasos (2FA) habilitada para tu cuenta.</div>
        <div className="lgDiv">o entrá a la demo como</div>
        <div className="lgRoles">
          {Object.keys(PD.roles).map((k) => (
            <div key={k} className="lgRole" onClick={() => onLogin(k)}>
              <div className="lgRoleAv" style={{ background: PD.roles[k].grad }}>{PD.roles[k].av}</div>
              <div style={{ flex: 1 }}><div style={{ fontSize: 13.5, fontWeight: 800 }}>{PD.roles[k].label}</div><div style={{ fontSize: 11.5, color: '#9aa1ad' }}>{PD.roles[k].nombre}</div></div>
              <Icon name="arrow" size={16} color="#9aa1ad" />
            </div>
          ))}
        </div>
        <div className="lgFoot">Prototipo de demostración · datos de ejemplo</div>
      </div>
    </div>
  );
}

function Toasts({ items }) {
  const col = { check: '#34d399', x: '#f87171', mail: '#818cf8', bell: '#fbbf24', plus: '#818cf8', layers: '#c4b5fd', calendar: '#818cf8', clipboard: '#818cf8' };
  return (
    <div className="pToastWrap">
      {items.map((t) => (
        <div key={t.id} className="pToast">
          <div className="ic" style={{ background: 'rgba(255,255,255,.14)' }}><Icon name={t.icon || 'check'} size={14} color={col[t.icon] || '#34d399'} stroke={2.4} /></div>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

function resolveView(role, view) {
  if (role === 'ALUMNO') return ({ ...window.V_ALU, inbox: window.V_GEST.inbox })[view];
  return ({ ...window.V_ACAD, ...window.V_GEST, ...window.V_ADMIN, ...window.V_FIN })[view];
}

function App() {
  const [logged, setLogged] = React.useState(() => localStorage.getItem('act-logged') === '1');
  const [role, setRole] = React.useState(() => localStorage.getItem('act-role') || 'COORDINADOR');
  const [view, setView] = React.useState(() => PD.roles[localStorage.getItem('act-role') || 'COORDINADOR'].home);
  const [toasts, setToasts] = React.useState([]);

  React.useEffect(() => { localStorage.setItem('act-role', role); }, [role]);
  React.useEffect(() => { localStorage.setItem('act-logged', logged ? '1' : '0'); }, [logged]);

  const toast = (msg, icon) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, icon }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  };
  const onRole = (r) => { if (r === '__logout') { setLogged(false); return; } setRole(r); };
  const login = (r) => { setRole(r); setView(PD.roles[r].home); setLogged(true); };

  if (!logged) return <Login onLogin={login} />;

  const View = resolveView(role, view) || (() => <Empty title="En construcción" icon="layers">Esta vista todavía no está en el prototipo.</Empty>);
  const ctx = { role, setView, toast };
  return (
    <>
      <Shell role={role} view={view} setView={setView} setRole={onRole} toast={toast}>
        <View ctx={ctx} />
      </Shell>
      <Toasts items={toasts} />
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
