import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import {
  Dashboard,
  Upload,
  LiveMonitor,
  Simulator,
  Incidents,
  Investigation,
  History,
  Settings,
} from './pages';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="stream" element={<LiveMonitor />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="investigation/:id" element={<Investigation />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
