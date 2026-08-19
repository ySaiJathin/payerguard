import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlayCircle,
  History as HistoryIcon,
  ShieldCheck,
  X
} from 'lucide-react';
import { cn } from '../utils/cn';
import { BASE_URL } from '../services/apiClient';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  incidentCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  incidentCount = 0,
}) => {
  /*
   * Three destinations. Upload Claims, Incidents and Settings were removed:
   * upload now lives on the Simulator page, incident history is the History
   * page, and Settings configured nothing the backend reads.
   *
   * The incident badge is the real open-incident count passed in by the
   * layout, not a placeholder.
   */
  const navigationItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      name: 'Simulator',
      path: '/simulator',
      icon: PlayCircle,
      badge: null,
    },
    {
      name: 'History',
      path: '/history',
      icon: HistoryIcon,
      badge: incidentCount > 0 ? `${incidentCount}` : null,
      badgeDanger: incidentCount > 0,
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-xs lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          'fixed top-0 bottom-0 left-0 z-40 w-64 bg-slate-900/95 border-r border-slate-800 flex flex-col transition-transform duration-200 ease-in-out lg:static lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800 bg-slate-950/50">
          <NavLink
            to="/dashboard"
            onClick={onClose}
            className="flex items-center gap-3 group focus:outline-none"
          >
            <div className="w-9 h-9 rounded-lg bg-linear-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md shadow-cyan-950/50 border border-cyan-400/30 group-hover:border-cyan-300 transition-colors">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-base tracking-tight text-white font-heading">
                  Payer<span className="text-cyan-400">Guard</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">
                  v2.4
                </span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide">
                Claims Quality &amp; Risk Monitoring
              </span>
            </div>
          </NavLink>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Platform Navigation
          </div>
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group select-none',
                    isActive
                      ? 'bg-cyan-600/15 text-cyan-300 border border-cyan-500/30 font-semibold shadow-xs'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3">
                      <Icon
                        className={cn(
                          'w-4 h-4 transition-colors',
                          isActive
                            ? 'text-cyan-400'
                            : 'text-slate-400 group-hover:text-slate-200'
                        )}
                      />
                      <span>{item.name}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded font-mono font-medium border',
                          item.badgeDanger
                            ? 'bg-rose-950/80 text-rose-300 border-rose-800/60 font-bold'
                            : isActive
                            ? 'bg-cyan-950/80 text-cyan-300 border-cyan-800/60'
                            : 'bg-slate-800 text-slate-400 border-slate-750'
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/*
          Shows the API this UI is pointed at. The previous version displayed a
          "99.4% / SLA Target 99.0%" uptime readout, which had no source -- the
          backend exposes no uptime or SLA metric, and this project has no SLA
          concept at all.
        */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40">
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              Backend
            </span>
            <span className="text-[11px] font-mono text-cyan-400 break-all">{BASE_URL}</span>
          </div>
        </div>
      </aside>
    </>
  );
};
