import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard, Upload, Incidents, Investigation, History, Settings } from './pages';

/**
 * `/stream` and `/simulator` are deliberately absent.
 *
 * Both were backed by `streamSimulatorService.generateRandomClaim()`, which
 * fabricated a new fake claim every few seconds -- exactly the "claims
 * simulator" the constitution names as out of scope. Their page files are kept
 * on disk (excluded from the build) because the decision to rebuild them
 * around real, already-computed data or cut them entirely is still open.
 */
export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
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
