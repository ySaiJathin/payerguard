import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAsync } from '../hooks/useAsync';
import { incidentsApi } from '../services/api';

export const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // The sidebar badge used to be hardcoded to 4, which contradicted the real
  // incident count on every page it sat next to. It now reflects the backend.
  const incidents = useAsync(() => incidentsApi.list(), []);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col lg:flex-row text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        incidentCount={incidents.data?.length ?? 0}
      />

      <div className="flex-1 flex flex-col min-w-0 bg-slate-950">
        <Header onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
