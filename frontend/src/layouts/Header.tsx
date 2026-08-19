import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Menu,
  Bell,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  ChevronDown,
  User,
  Shield,
  Layers,
  Database
} from 'lucide-react';
import { StatusIndicator } from '../components/ui/StatusIndicator';
import { NotificationItem } from '../types';

// Simple time ago helper
function getRelativeTime(isoString: string): string {
  try {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  } catch {
    return 'recently';
  }
}

interface HeaderProps {
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const navigate = useNavigate();
  // The backend exposes no notifications endpoint, so this starts empty rather
  // than seeded with invented alerts. Wire it up if such an endpoint is added.
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    // If matches incident ID format
    if (searchQuery.toUpperCase().startsWith('INC-')) {
      navigate(`/investigation/${searchQuery.trim().toUpperCase()}`);
    } else if (searchQuery.toUpperCase().startsWith('CLM-')) {
      navigate(`/investigation/INC-8921`); // fallback demo drilldown
    } else {
      navigate(`/incidents?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <header className="h-16 sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 sm:px-6 flex items-center justify-between">
      {/* Left side: Mobile menu toggle + Global search */}
      <div className="flex items-center gap-3 sm:gap-4 flex-1 max-w-xl">
        <button
          onClick={onToggleSidebar}
          className="p-2 -ml-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Claims Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search incident or window id..."
            className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all font-mono"
          />
        </form>
      </div>

      {/* Right side: Pipeline Status, Notification Trigger, User Profile */}
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Environment and Status Indicator */}
        <div className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs">
          {/*
            Was "HIPAA Gateway Live | EDI 5010 Engine" -- this backend never
            touches an EDI transaction and exposes no gateway health signal.
            Replaced with the dataset it actually reads.
          */}
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-mono">
            <Database className="w-3 h-3 text-cyan-400" />
            <span>CMS Inpatient RIF</span>
          </div>
        </div>

        {/* Notification Bell */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500 animate-pulse ring-2 ring-slate-900" />
            )}
          </button>

          {/* Notifications Dropdown Drawer */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-slate-900 border border-slate-750 shadow-2xl z-50 overflow-hidden text-slate-100 animate-in fade-in zoom-in-95 duration-100">
              <div className="flex items-center justify-between p-3.5 border-b border-slate-800 bg-slate-950/60">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Alerts
                  </h4>
                  {unreadCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800/60 font-bold">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400">
                    No active notifications
                  </div>
                ) : (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => {
                        if (notif.link) {
                          navigate(notif.link);
                          setShowNotifications(false);
                        }
                      }}
                      className={`p-3.5 transition-colors cursor-pointer hover:bg-slate-800/60 ${
                        !notif.read ? 'bg-cyan-950/20' : ''
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        {notif.severity === 'critical' ? (
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                        ) : notif.severity === 'high' ? (
                          <Clock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-slate-200 leading-snug">
                            {notif.title}
                          </p>
                          <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                            {notif.message}
                          </p>
                          <span className="text-[10px] text-slate-400 font-mono mt-1.5 block">
                            {getRelativeTime(notif.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2 border-t border-slate-800 bg-slate-950/40 text-center">
                <button
                  onClick={() => {
                    navigate('/incidents');
                    setShowNotifications(false);
                  }}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-1 py-1"
                >
                  View all incidents & alerts <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Profile */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center gap-2.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500"
          >
            <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-300 border border-slate-700">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-100 leading-tight">
                Local session
              </span>
              <span className="text-[10px] text-slate-400 font-medium">
                No authentication configured
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {/* Profile Popover */}
          {showProfileMenu && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-900 border border-slate-750 shadow-2xl z-50 p-2 text-slate-200 animate-in fade-in zoom-in-95 duration-100">
              <div className="p-2.5 border-b border-slate-800 mb-1">
                <p className="text-xs font-semibold text-white">Local session</p>
                <p className="text-[11px] text-slate-400 leading-relaxed mt-0.5">
                  The backend has no authentication or user model. Reviewer identity is
                  supplied per action when accepting or rejecting an incident.
                </p>
              </div>

              <div className="space-y-0.5 text-xs">
                <button
                  onClick={() => {
                    navigate('/settings');
                    setShowProfileMenu(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white text-left transition-colors"
                >
                  <Shield className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Quality Rules</span>
                </button>
                <button
                  onClick={() => {
                    navigate('/history');
                    setShowProfileMenu(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white text-left transition-colors"
                >
                  <Layers className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Batch History & Logs</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
