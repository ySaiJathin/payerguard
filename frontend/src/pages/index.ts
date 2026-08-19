export * from './Dashboard';
export * from './Upload';
export * from './Incidents';
export * from './Investigation';
export * from './History';
export * from './Settings';

// `LiveMonitor` (/stream) and `Simulator` (/simulator) are intentionally not
// exported. Both pages are driven by the client-side random-claim generator,
// which the constitution rules out by name ("claims simulator"). The decision
// to either rebuild them around real replayed data or drop them is paused, not
// made -- so the files are kept on disk but excluded from the build (see
// `tsconfig.app.json`) rather than deleted.
