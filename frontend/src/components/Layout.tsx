import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, MessageCircle, Database, Network, ClipboardCheck, Shield } from 'lucide-react'
import { ReactNode } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/chat', icon: MessageCircle, label: 'Chat' },
  { to: '/knowledge', icon: Database, label: 'Knowledge' },
  { to: '/entities', icon: Network, label: 'Entities' },
  { to: '/evaluation', icon: ClipboardCheck, label: 'Evaluation' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 glass flex flex-col border-r border-aegis-border">
        {/* Logo */}
        <div className="p-6 border-b border-aegis-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aegis-accent to-purple-500 flex items-center justify-center shadow-lg shadow-aegis-accent/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white">AEGIS</h1>
              <p className="text-[10px] text-aegis-text-muted tracking-widest uppercase">Knowledge System</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                  isActive
                    ? 'bg-aegis-accent/15 text-aegis-accent-light border border-aegis-accent/20 shadow-sm'
                    : 'text-aegis-text-muted hover:text-aegis-text hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-4.5 h-4.5 flex-shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-aegis-border">
          <p className="text-[10px] text-aegis-text-dim text-center">
            Aegis Series-7 Knowledge System
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="animate-fade-in-up">
          {children}
        </div>
      </main>
    </div>
  )
}
