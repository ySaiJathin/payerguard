import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard, Simulator, Investigation, History } from './pages';

/**
 * Four routes, deliberately.
 *
 * `/settings` and `/incidents` were removed outright. Settings configured
 * nothing the backend reads. The Incidents list duplicated what History now
 * shows -- History is the single home for incident history across every run,
 * and every "Investigate" action goes to `/investigation/:id`, which is where
 * it always went.
 *
 * `/upload` was folded into `/simulator`: an uploaded file is another way to
 * feed the same pipeline, so it belongs beside the batch runner rather than
 * on a page of its own.
 *
 * Anything still pointing at a removed path lands on `/dashboard` via the
 * catch-all rather than 404ing.
 */
export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="history" element={<History />} />
          <Route path="investigation/:id" element={<Investigation />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
