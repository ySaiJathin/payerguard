# Investigation Risk Label Formula

**Version**: `v1`
**Generated at**: 2026-08-19T04:55:40.971167+00:00

## Formula

```
IRI = w_q * norm(historical_quality_failure_rate)
    + w_a * norm(anomaly_frequency)
    + w_d * norm(max(|volume_deviation|, |amount_deviation|))

investigation_risk_label = 1 if IRI >= percentile_threshold(IRI over train-split windows)
                           else 0
Zero-claim windows always receive investigation_risk_label = 0.
```

## Weights

- `w_q` = 0.4
- `w_a` = 0.4
- `w_d` = 0.2

## Normalization statistics (train-split windows only)

- `quality_failure_rate`: min=0.33799887066859136, max=0.33799887066859136
- `anomaly_frequency`: min=0.0, max=0.0
- `amount_deviation`: min=0.0, max=322622.1849586942

## Percentile threshold: 75.0

## Rationale

The investigation-risk label is not an SLA-breach / processing-turnaround label: per MVP_CONTEXT.md Section 2.4, this dataset has no genuine claims-adjudication-turnaround field ('FI_CLM_PROC_DT' is 100% null; 'NCH_WKLY_PROC_DT' is a fixed weekly batch-cutoff date, not an operational timestamp). Instead, this formula combines three real, already-computed signals -- historical quality-failure rate (Phase 4), anomaly frequency (Phase 7), and the larger of volume/amount deviation from baseline (Phase 5) -- into a single, documented Investigation Risk Indicator (IRI), thresholded at the 75th percentile of IRI over Phase 6's train-split windows only, to determine which windows are investigation-worthy.
