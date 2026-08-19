import { KPIMetric, NotificationItem } from '../types';

export const mockDashboardKPIs: KPIMetric[] = [
  {
    title: 'Clean Claim Rate',
    value: '98.4%',
    unit: 'Target ≥98.0%',
    changePercent: 0.6,
    isPositiveChange: true,
    trendText: 'vs last 24h',
    subtext: 'High quality pass-through',
    status: 'good',
  },
  {
    title: 'Claims Processed (24h)',
    value: '142,850',
    unit: 'claims',
    changePercent: 12.4,
    isPositiveChange: true,
    trendText: 'vs avg daily vol',
    subtext: '$84.2M Total Billed',
    status: 'info',
  },
  {
    title: 'SLA Compliance Rate',
    value: '99.4%',
    unit: 'Target ≥99.0%',
    changePercent: -0.2,
    isPositiveChange: false,
    trendText: '1 Breached ticket',
    subtext: 'Turnaround: 18.2m avg',
    status: 'warning',
  },
  {
    title: 'Active DQ Incidents',
    value: '4',
    unit: '2 Critical',
    changePercent: -25.0, // Reduced incidents is good
    isPositiveChange: true,
    trendText: 'down from 6',
    subtext: '1 under active audit',
    status: 'critical',
  }
];

export const mockAnomalyDistributions = [
  { category: 'NPI Registry Mismatch', count: 42, percentage: 8.0, color: 'bg-rose-500' },
  { category: 'NCCI Code Unbundling', count: 186, percentage: 35.3, color: 'bg-amber-500' },
  { category: 'Duplicate Service Lines', count: 94, percentage: 17.8, color: 'bg-indigo-500' },
  { category: 'Modifier 25 Inconsistency', count: 112, percentage: 21.2, color: 'bg-cyan-500' },
  { category: 'Timely Filing Risk', count: 28, percentage: 5.3, color: 'bg-rose-400' },
  { category: 'High-Dollar Charge Outlier', count: 65, percentage: 12.4, color: 'bg-emerald-500' },
];

export const mockHourlyThroughput = [
  { hour: '00:00', volume: 4200, cleanRate: 98.8, latencyMs: 140 },
  { hour: '02:00', volume: 3800, cleanRate: 98.2, latencyMs: 145 },
  { hour: '04:00', volume: 5100, cleanRate: 98.5, latencyMs: 152 },
  { hour: '06:00', volume: 7400, cleanRate: 97.9, latencyMs: 170 },
  { hour: '08:00', volume: 14200, cleanRate: 98.4, latencyMs: 210 },
  { hour: '10:00', volume: 18900, cleanRate: 98.1, latencyMs: 240 },
  { hour: '12:00', volume: 17400, cleanRate: 98.6, latencyMs: 195 },
  { hour: '14:00', volume: 16800, cleanRate: 98.7, latencyMs: 185 },
  { hour: '16:00', volume: 15100, cleanRate: 98.4, latencyMs: 190 },
  { hour: '18:00', volume: 11200, cleanRate: 99.1, latencyMs: 160 },
  { hour: '20:00', volume: 8900, cleanRate: 98.9, latencyMs: 150 },
  { hour: '22:00', volume: 6200, cleanRate: 99.0, latencyMs: 142 },
];

export const mockNotifications: NotificationItem[] = [
  {
    id: 'NOTIF-01',
    title: 'SLA Breach Warning: INC-8921',
    message: 'Medicare claim 8921-7729-CMS has 24 minutes left before statutory SLA violation.',
    severity: 'critical',
    timestamp: '2026-08-18T05:16:00Z',
    read: false,
    link: '/investigation/INC-8921',
  },
  {
    id: 'NOTIF-02',
    title: 'SLA Escalation: INC-7734',
    message: 'Inpatient Claim 7734-1102-UHC escalated to Senior Compliance Director.',
    severity: 'critical',
    timestamp: '2026-08-18T04:15:00Z',
    read: false,
    link: '/investigation/INC-7734',
  },
  {
    id: 'NOTIF-03',
    title: 'EDI Batch Validation Completed',
    message: 'Batch BATCH-2026-0818-A processed 1,250 claims with 99.2% clean rate.',
    severity: 'low',
    timestamp: '2026-08-18T03:30:00Z',
    read: true,
    link: '/history',
  }
];
