import { Incident, IncidentStatus } from '../types';
import { mockIncidents } from '../data/mockIncidents';

class IncidentService {
  private incidents: Incident[] = [...mockIncidents];

  public getAllIncidents(): Incident[] {
    return [...this.incidents];
  }

  public getIncidentById(id: string): Incident | undefined {
    return this.incidents.find((inc) => inc.id === id || inc.claimId === id);
  }

  public updateIncidentStatus(id: string, status: IncidentStatus, resolutionNote?: string, actor = 'Dr. Sarah Jenkins'): Incident | undefined {
    const incident = this.incidents.find((inc) => inc.id === id);
    if (!incident) return undefined;

    incident.status = status;
    incident.updatedAt = new Date().toISOString();

    if (resolutionNote) {
      incident.auditTrail.push({
        id: `LOG-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor,
        action: `Status changed to ${status.toUpperCase()}`,
        details: resolutionNote,
      });
    }

    if (status === 'resolved') {
      incident.slaStatus = 'met';
      if (incident.claimDetails) {
        incident.claimDetails.status = 'reprocessed';
      }
    }

    return incident;
  }

  public addIncident(incident: Incident): void {
    this.incidents.unshift(incident);
  }
}

export const incidentService = new IncidentService();
