import { ClaimRecord, BatchUploadSummary } from '../types';
import { mockClaims } from '../data/mockClaims';
import { mockBatchHistory } from '../data/mockHistory';

class ClaimsService {
  private claims: ClaimRecord[] = [...mockClaims];
  private batches: BatchUploadSummary[] = [...mockBatchHistory];

  public getAllClaims(): ClaimRecord[] {
    return [...this.claims];
  }

  public getClaimById(id: string): ClaimRecord | undefined {
    return this.claims.find((c) => c.id === id || c.claimNumber === id);
  }

  public addClaim(claim: ClaimRecord): void {
    this.claims.unshift(claim);
  }

  public updateClaimStatus(id: string, status: ClaimRecord['status']): void {
    const claim = this.claims.find((c) => c.id === id);
    if (claim) {
      claim.status = status;
    }
  }

  public getBatches(): BatchUploadSummary[] {
    return [...this.batches];
  }

  public addBatch(batch: BatchUploadSummary): void {
    this.batches.unshift(batch);
  }
}

export const claimsService = new ClaimsService();
