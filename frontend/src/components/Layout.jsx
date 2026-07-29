import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '▦' },
  { to: '/tickets', label: 'Tickets', icon: '☰' },
  { to: '/circulars', label: 'Circulars', icon: '⊞' },
  { to: '/policies', label: 'Policies', icon: '▤' },
  { to: '/audit', label: 'Audit Trail', icon: '≣' },
  { to: '/evaluation', label: 'RAGAS Eval', icon: '◎' },
]

const toolItems = [
  { to: '/ask-ai', label: 'Ask AI', icon: '◈' },
  { to: '/pipeline', label: 'Pipeline', icon: '⟳' },
]

function Layout({ children }) {
  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* SIDEBAR */}
      <aside style={{
        width: 'var(--sidebar-width)',
        background: 'var(--color-primary)',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0
      }}>
        <div style={{
          padding: '18px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.12)'
        }}>
          <div style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '0.02em' }}>
            AI Compliance
          </div>
          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', marginTop: '2px' }}>
            Copilot
          </div>
        </div>

        <nav style={{ padding: '12px 0', flex: 1 }}>
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 20px',
                fontSize: '13px',
                fontWeight: 500,
                textDecoration: 'none',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.7)',
                background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                borderLeft: isActive ? '3px solid #4fc3f7' : '3px solid transparent',
              })}
            >
              <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}

          <div style={{
            margin: '12px 20px',
            borderTop: '1px solid rgba(255,255,255,0.12)'
          }} />
          <div style={{
            padding: '8px 20px',
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '0.06em',
            color: 'rgba(255,255,255,0.4)',
            textTransform: 'uppercase'
          }}>
            Tools
          </div>

          {toolItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 20px',
                fontSize: '13px',
                fontWeight: 500,
                textDecoration: 'none',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.7)',
                background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                borderLeft: isActive ? '3px solid #4fc3f7' : '3px solid transparent',
              })}
            >
              <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={{
          padding: '14px 20px',
          borderTop: '1px solid rgba(255,255,255,0.12)',
          fontSize: '11px',
          color: 'rgba(255,255,255,0.5)'
        }}>
          CDAC Mumbai · PGCP-BDA
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main style={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <header style={{
          height: 'var(--header-height)',
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          flexShrink: 0
        }}>
          <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
            Bank of India · SEBI/RBI/IRDAI/PFRDA Monitoring
          </span>
        </header>

        <div style={{
          flex: 1,
          minHeight: 0,
          padding: '24px',
          overflowY: 'auto'
        }}>
          {children}
        </div>
      </main>
    </div>
  )
}

export default Layout
