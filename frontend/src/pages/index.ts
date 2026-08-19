export * from './Dashboard';
export * from './Simulator';
export * from './Investigation';
export * from './History';

// `Settings`, `Incidents` and `Upload` were deleted, not hidden: Settings
// configured nothing the backend reads, the Incidents list is now History,
// and upload lives on the Simulator page beside the batch runner.
//
// `LiveMonitor` (/stream) is still excluded from the build. It was driven by
// the deleted client-side random-claim generator; the Simulator supersedes
// what it was for, and the file is kept on disk pending deletion rather than
// rewritten.
