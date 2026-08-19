# Data Profiling Report

- Source file: `D:\CODIN\payerguard\payerguard\data\raw\inpatient.csv`
- Generated at: 2026-08-19T04:44:47.301793+00:00
- Total rows: 58066
- Total columns: 197
- Unique claims (CLM_ID): 20867
- Unique beneficiaries (BENE_ID): 5699
- Lines per claim: mean 2.78, median 1.00
- Duplicate rows: 0

## Columns

| Column | Category | Dtype | Missing % | Cardinality | Notes |
|---|---|---|---|---|---|
| BENE_ID | identifier | int64 | 0.00 | 5699 | top: -10000010282387=1090, -10000010255799=1032, -10000010275202=1007 |
| CLM_ID | identifier | int64 | 0.00 | 20867 | top: -10000930775141=46, -10000930487748=34, -10000930521375=34 |
| NCH_NEAR_LINE_REC_IDENT_CD | categorical_code | str | 0.00 | 1 | top: V=58066 |
| NCH_CLM_TYPE_CD | categorical_code | int64 | 0.00 | 1 | top: 60=58066 |
| CLM_FROM_DT | date | str | 0.00 | 2914 | format=DD-Mon-YYYY min=25-Feb-2015 max=02-Mar-2023 |
| CLM_THRU_DT | date | str | 0.00 | 2910 | format=DD-Mon-YYYY min=07-Mar-2015 max=02-Mar-2023 |
| NCH_WKLY_PROC_DT | date | str | 0.00 | 417 | format=DD-Mon-YYYY min=13-Mar-2015 max=03-Mar-2023 |
| FI_CLM_PROC_DT | date | float64 | 100.00 | 0 | — |
| CLAIM_QUERY_CODE | categorical_code | int64 | 0.00 | 1 | top: 3=58066 |
| PRVDR_NUM | identifier | str | 4.89 | 4876 | top: 491581=1093, 030115=1077, 377673=1009 |
| CLM_FAC_TYPE_CD | categorical_code | int64 | 0.00 | 1 | top: 1=58066 |
| CLM_SRVC_CLSFCTN_TYPE_CD | categorical_code | int64 | 0.00 | 1 | top: 1=58066 |
| CLM_FREQ_CD | categorical_code | int64 | 0.00 | 1 | top: 1=58066 |
| FI_NUM | identifier | float64 | 100.00 | 0 | — |
| CLM_MDCR_NON_PMT_RSN_CD | categorical_code | str | 0.00 | 1 | top:  =58066 |
| CLM_PMT_AMT | amount | float64 | 0.00 | 10341 | mean=13638.31 median=1481.72 std=35993.91 min=62.44 max=598716.31 |
| NCH_PRMRY_PYR_CLM_PD_AMT | amount | float64 | 0.00 | 2263 | mean=2732.68 median=0.00 std=17139.23 min=0.00 max=598077.27 |
| NCH_PRMRY_PYR_CD | categorical_code | str | 0.00 | 1 | top:  =58066 |
| FI_CLM_ACTN_CD | categorical_code | float64 | 100.00 | 0 | — |
| PRVDR_STATE_CD | categorical_code | int64 | 0.00 | 51 | top: 10=6285, 5=4866, 33=4448 |
| ORG_NPI_NUM | identifier | int64 | 0.00 | 4902 | top: 1063523132=1093, 1275566200=1077, 1306950993=1009 |
| AT_PHYSN_UPIN | identifier | str | 0.00 | 1 | top:  =58066 |
| AT_PHYSN_NPI | identifier | int64 | 0.00 | 2463 | top: 9999868992=1479, 9999997494=1108, 9999907899=1012 |
| OP_PHYSN_UPIN | identifier | str | 0.00 | 1 | top:  =58066 |
| OP_PHYSN_NPI | identifier | int64 | 0.00 | 2463 | top: 9999868992=1479, 9999997494=1108, 9999907899=1012 |
| OT_PHYSN_UPIN | identifier | float64 | 100.00 | 0 | — |
| OT_PHYSN_NPI | identifier | float64 | 100.00 | 0 | — |
| CLM_MCO_PD_SW | categorical_code | int64 | 0.00 | 1 | top: 0=58066 |
| PTNT_DSCHRG_STUS_CD | categorical_code | int64 | 0.00 | 1 | top: 1=58066 |
| CLM_PPS_IND_CD | categorical_code | str | 0.00 | 1 | top:  =58066 |
| CLM_TOT_CHRG_AMT | amount | float64 | 0.00 | 10341 | mean=13638.31 median=1481.72 std=35993.91 min=62.44 max=598716.31 |
| CLM_ADMSN_DT | date | str | 0.00 | 2914 | format=DD-Mon-YYYY min=25-Feb-2015 max=02-Mar-2023 |
| CLM_IP_ADMSN_TYPE_CD | categorical_code | int64 | 0.00 | 3 | top: 1=43089, 3=14020, 2=957 |
| CLM_SRC_IP_ADMSN_CD | categorical_code | int64 | 0.00 | 4 | top: 5=14838, 1=14707, 2=14285 |
| NCH_PTNT_STATUS_IND_CD | categorical_code | str | 0.00 | 1 | top: A=58066 |
| CLM_PASS_THRU_PER_DIEM_AMT | amount | int64 | 0.00 | 1 | mean=10.00 median=10.00 std=0.00 min=10.00 max=10.00 |
| NCH_BENE_IP_DDCTBL_AMT | amount | float64 | 0.00 | 694 | mean=9.59 median=0.00 std=84.71 min=0.00 max=1644.00 |
| NCH_BENE_PTA_COINSRNC_LBLTY_AM | amount | float64 | 0.00 | 8032 | mean=1894.95 median=228.01 std=6138.65 min=0.00 max=119743.40 |
| NCH_BENE_BLOOD_DDCTBL_LBLTY_AM | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| NCH_PROFNL_CMPNT_CHRG_AMT | amount | int64 | 0.00 | 1 | mean=4.00 median=4.00 std=0.00 min=4.00 max=4.00 |
| NCH_IP_NCVRD_CHRG_AMT | amount | float64 | 0.00 | 2370 | mean=1695.81 median=0.00 std=12396.74 min=0.00 max=246764.71 |
| NCH_IP_TOT_DDCTN_AMT | amount | float64 | 0.00 | 2370 | mean=1695.81 median=0.00 std=12396.74 min=0.00 max=246764.71 |
| CLM_TOT_PPS_CPTL_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_CPTL_FSP_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_CPTL_OUTLIER_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_CPTL_DSPRPRTNT_SHR_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_CPTL_IME_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_CPTL_EXCPTN_AMT | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_PPS_OLD_CPTL_HLD_HRMLS_AMT | categorical_code | int64 | 0.00 | 1 | top: 0=58066 |
| CLM_PPS_CPTL_DRG_WT_NUM | amount | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_UTLZTN_DAY_CNT | utilization_duration | int64 | 0.00 | 45 | mean=1.70 median=0.00 std=4.00 min=0.00 max=104.00 |
| BENE_TOT_COINSRNC_DAYS_CNT | utilization_duration | int64 | 0.00 | 3 | mean=0.00 median=0.00 std=0.26 min=0.00 max=44.00 |
| BENE_LRD_USED_CNT | utilization_duration | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| CLM_NON_UTLZTN_DAYS_CNT | utilization_duration | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| NCH_BLOOD_PNTS_FRNSHD_QTY | utilization_duration | int64 | 0.00 | 1 | mean=0.00 median=0.00 std=0.00 min=0.00 max=0.00 |
| NCH_VRFD_NCVRD_STAY_FROM_DT | date | float64 | 100.00 | 0 | — |
| NCH_VRFD_NCVRD_STAY_THRU_DT | date | float64 | 100.00 | 0 | — |
| NCH_ACTV_OR_CVRD_LVL_CARE_THRU | date | float64 | 100.00 | 0 | — |
| NCH_BENE_MDCR_BNFTS_EXHTD_DT_I | date | float64 | 100.00 | 0 | — |
| NCH_BENE_DSCHRG_DT | date | str | 0.00 | 2910 | format=DD-Mon-YYYY min=07-Mar-2015 max=02-Mar-2023 |
| CLM_DRG_CD | categorical_code | float64 | 5.62 | 167 | top: 951.0=28831, 950.0=1456, 949.0=1332 |
| CLM_DRG_OUTLIER_STAY_CD | categorical_code | int64 | 0.00 | 3 | top: 0=56137, 2=1925, 1=4 |
| NCH_DRG_OUTLIER_APRVD_PMT_AMT | categorical_code | int64 | 0.00 | 1 | top: 0=58066 |
| ADMTG_DGNS_CD | diagnosis_procedure_code | str | 72.22 | 65 | top: Z7682=2881, T50901A=2541, Z951=1694 |
| PRNCPAL_DGNS_CD | diagnosis_procedure_code | str | 0.00 | 190 | top: Z733=11469, Z608=7216, T7432X=3314 |
| ICD_DGNS_CD1 | diagnosis_procedure_code | str | 0.00 | 231 | top: Z733=13031, Z608=8227, T7432X=3727 |
| CLM_POA_IND_SW1 | diagnosis_procedure_code | str | 0.00 | 2 | top: Y=30497, N=27569 |
| ICD_DGNS_CD2 | diagnosis_procedure_code | str | 0.10 | 242 | top: Z733=9567, Z608=9095, T7432X=4054 |
| CLM_POA_IND_SW2 | diagnosis_procedure_code | str | 0.10 | 2 | top: Y=45106, N=12903 |
| ICD_DGNS_CD3 | diagnosis_procedure_code | str | 0.46 | 238 | top: Z608=5868, Z733=5823, N1830=3002 |
| CLM_POA_IND_SW3 | diagnosis_procedure_code | str | 0.46 | 2 | top: Y=44689, N=13109 |
| ICD_DGNS_CD4 | diagnosis_procedure_code | str | 1.11 | 223 | top: N1830=4203, Z608=3359, I259=2715 |
| CLM_POA_IND_SW4 | diagnosis_procedure_code | str | 1.11 | 2 | top: Y=44407, N=13017 |
| ICD_DGNS_CD5 | diagnosis_procedure_code | str | 1.89 | 218 | top: N1830=4338, Z653=2704, I259=2515 |
| CLM_POA_IND_SW5 | diagnosis_procedure_code | str | 1.89 | 2 | top: Y=44224, N=12743 |
| ICD_DGNS_CD6 | diagnosis_procedure_code | str | 2.74 | 204 | top: Z653=3230, N1830=3195, E1121=3067 |
| CLM_POA_IND_SW6 | diagnosis_procedure_code | str | 2.74 | 2 | top: Y=43729, N=12745 |
| ICD_DGNS_CD7 | diagnosis_procedure_code | str | 3.93 | 210 | top: E1121=3205, Z653=3129, R931=2661 |
| CLM_POA_IND_SW7 | diagnosis_procedure_code | str | 3.93 | 2 | top: Y=42633, N=13151 |
| ICD_DGNS_CD8 | diagnosis_procedure_code | str | 5.36 | 204 | top: E1121=3445, Z653=2979, I259=2662 |
| CLM_POA_IND_SW8 | diagnosis_procedure_code | str | 5.36 | 2 | top: Y=41926, N=13028 |
| ICD_DGNS_CD9 | diagnosis_procedure_code | str | 7.71 | 202 | top: E1121=3768, Z653=2433, I259=2377 |
| CLM_POA_IND_SW9 | diagnosis_procedure_code | str | 7.71 | 2 | top: Y=41862, N=11728 |
| ICD_DGNS_CD10 | diagnosis_procedure_code | str | 10.57 | 196 | top: E1121=4461, R931=2149, Z653=2029 |
| CLM_POA_IND_SW10 | diagnosis_procedure_code | str | 10.57 | 2 | top: Y=41085, N=10846 |
| ICD_DGNS_CD11 | diagnosis_procedure_code | str | 13.78 | 190 | top: E1121=4741, I259=2223, E669=2201 |
| CLM_POA_IND_SW11 | diagnosis_procedure_code | str | 13.78 | 2 | top: Y=40264, N=9802 |
| ICD_DGNS_CD12 | diagnosis_procedure_code | str | 17.54 | 179 | top: E1121=3906, E669=2752, I259=2176 |
| CLM_POA_IND_SW12 | diagnosis_procedure_code | str | 17.54 | 2 | top: Y=39708, N=8172 |
| ICD_DGNS_CD13 | diagnosis_procedure_code | str | 21.66 | 171 | top: E1121=3187, E669=2558, E8881=2053 |
| CLM_POA_IND_SW13 | diagnosis_procedure_code | str | 21.66 | 2 | top: Y=37973, N=7517 |
| ICD_DGNS_CD14 | diagnosis_procedure_code | str | 26.18 | 170 | top: E1121=3334, E669=2659, E8881=2148 |
| CLM_POA_IND_SW14 | diagnosis_procedure_code | str | 26.18 | 2 | top: Y=36200, N=6665 |
| ICD_DGNS_CD15 | diagnosis_procedure_code | str | 30.69 | 165 | top: E1121=2755, E8881=2552, E669=2324 |
| CLM_POA_IND_SW15 | diagnosis_procedure_code | str | 30.69 | 2 | top: Y=34792, N=5455 |
| ICD_DGNS_CD16 | diagnosis_procedure_code | str | 36.03 | 157 | top: E8881=2826, E669=2719, E1121=2233 |
| CLM_POA_IND_SW16 | diagnosis_procedure_code | str | 36.03 | 2 | top: Y=32610, N=4534 |
| ICD_DGNS_CD17 | diagnosis_procedure_code | str | 41.72 | 154 | top: E8881=3021, E669=2872, R7303=2463 |
| CLM_POA_IND_SW17 | diagnosis_procedure_code | str | 41.72 | 2 | top: Y=29618, N=4223 |
| ICD_DGNS_CD18 | diagnosis_procedure_code | str | 47.16 | 140 | top: E669=2962, R7303=2560, D649=2121 |
| CLM_POA_IND_SW18 | diagnosis_procedure_code | str | 47.16 | 2 | top: Y=26787, N=3895 |
| ICD_DGNS_CD19 | diagnosis_procedure_code | str | 52.21 | 132 | top: R7303=2632, E669=2428, D649=2356 |
| CLM_POA_IND_SW19 | diagnosis_procedure_code | str | 52.21 | 2 | top: Y=24714, N=3036 |
| ICD_DGNS_CD20 | diagnosis_procedure_code | str | 57.70 | 133 | top: D649=2560, R7303=2053, E669=2012 |
| CLM_POA_IND_SW20 | diagnosis_procedure_code | str | 57.70 | 2 | top: Y=21945, N=2618 |
| ICD_DGNS_CD21 | diagnosis_procedure_code | str | 62.76 | 129 | top: D649=2064, R7303=1751, E669=1534 |
| CLM_POA_IND_SW21 | diagnosis_procedure_code | str | 62.76 | 2 | top: Y=19446, N=2177 |
| ICD_DGNS_CD22 | diagnosis_procedure_code | str | 68.61 | 116 | top: D649=1614, E669=1584, R7303=1532 |
| CLM_POA_IND_SW22 | diagnosis_procedure_code | str | 68.61 | 2 | top: Y=16395, N=1830 |
| ICD_DGNS_CD23 | diagnosis_procedure_code | str | 74.80 | 106 | top: E669=1533, R7303=1493, D649=1470 |
| CLM_POA_IND_SW23 | diagnosis_procedure_code | str | 74.80 | 2 | top: Y=13104, N=1526 |
| ICD_DGNS_CD24 | diagnosis_procedure_code | str | 79.88 | 103 | top: R7303=1684, D649=1531, E669=1083 |
| CLM_POA_IND_SW24 | diagnosis_procedure_code | str | 79.88 | 2 | top: Y=10358, N=1324 |
| ICD_DGNS_CD25 | diagnosis_procedure_code | str | 83.98 | 92 | top: D649=1372, R7303=1356, E669=682 |
| CLM_POA_IND_SW25 | diagnosis_procedure_code | str | 83.98 | 2 | top: Y=8093, N=1211 |
| FST_DGNS_E_CD | categorical_code | str | 21.60 | 137 | top: W86=10445, X58=7202, W19=4899 |
| ICD_DGNS_E_CD1 | diagnosis_procedure_code | str | 21.60 | 126 | top: W86=10445, X58=6868, W19=5162 |
| CLM_E_POA_IND_SW1 | categorical_code | str | 21.60 | 2 | top: Y=29170, U=16355 |
| ICD_DGNS_E_CD2 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW2 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD3 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW3 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD4 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW4 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD5 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW5 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD6 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW6 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD7 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW7 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD8 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW8 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD9 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW9 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD10 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW10 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD11 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW11 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_DGNS_E_CD12 | diagnosis_procedure_code | str | 0.00 | 1 | top:  =58066 |
| CLM_E_POA_IND_SW12 | categorical_code | str | 0.00 | 1 | top:  =58066 |
| ICD_PRCDR_CD1 | diagnosis_procedure_code | str | 17.07 | 114 | top: GZ3=16142, Z741=12421, BW03ZZZ=3337 |
| PRCDR_DT1 | date | str | 17.07 | 2824 | format=DD-Mon-YYYY min=07-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD2 | diagnosis_procedure_code | str | 22.40 | 51 | top: Z741=14553, F419=6575, BW03ZZZ=3712 |
| PRCDR_DT2 | date | str | 22.40 | 2724 | format=DD-Mon-YYYY min=07-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD3 | diagnosis_procedure_code | str | 31.14 | 53 | top: Z9181=8017, F419=7868, Z1331=6869 |
| PRCDR_DT3 | date | str | 31.14 | 2530 | format=DD-Mon-YYYY min=08-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD4 | diagnosis_procedure_code | str | 38.53 | 23 | top: Z1331=15086, Z9181=4857, Z139=3939 |
| PRCDR_DT4 | date | str | 38.53 | 2332 | format=DD-Mon-YYYY min=09-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD5 | diagnosis_procedure_code | str | 45.53 | 16 | top: Z1331=16209, F1990=4218, Z9981=2197 |
| PRCDR_DT5 | date | str | 45.53 | 2167 | format=DD-Mon-YYYY min=09-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD6 | diagnosis_procedure_code | str | 56.16 | 11 | top: Z1331=8637, F1990=5933, Z9981=2185 |
| PRCDR_DT6 | date | str | 56.16 | 1893 | format=DD-Mon-YYYY min=09-Mar-2015 max=02-Mar-2023 |
| ICD_PRCDR_CD7 | diagnosis_procedure_code | str | 68.69 | 11 | top: F1990=4285, Z715=2967, F109=2966 |
| PRCDR_DT7 | date | str | 68.69 | 1404 | format=DD-Mon-YYYY min=12-Mar-2015 max=28-Feb-2023 |
| ICD_PRCDR_CD8 | diagnosis_procedure_code | str | 81.57 | 12 | top: Z715=2211, Z9981=2134, F109=2074 |
| PRCDR_DT8 | date | str | 81.57 | 829 | format=DD-Mon-YYYY min=15-Mar-2015 max=28-Feb-2023 |
| ICD_PRCDR_CD9 | diagnosis_procedure_code | str | 90.23 | 9 | top: Z9981=2084, F08H5ZZ=1252, BW03ZZZ=620 |
| PRCDR_DT9 | date | str | 90.23 | 366 | format=DD-Mon-YYYY min=15-Mar-2015 max=24-Feb-2023 |
| ICD_PRCDR_CD10 | diagnosis_procedure_code | str | 92.88 | 9 | top: Z9981=2073, F08H5ZZ=1122, F13=428 |
| PRCDR_DT10 | date | str | 92.88 | 237 | format=DD-Mon-YYYY min=23-Mar-2015 max=25-Feb-2023 |
| ICD_PRCDR_CD11 | diagnosis_procedure_code | str | 93.68 | 5 | top: Z9981=2062, F08H5ZZ=990, F13=368 |
| PRCDR_DT11 | date | str | 93.68 | 205 | format=DD-Mon-YYYY min=13-May-2015 max=16-Feb-2023 |
| ICD_PRCDR_CD12 | diagnosis_procedure_code | str | 95.02 | 6 | top: Z9981=1612, F08H5ZZ=870, F13=302 |
| PRCDR_DT12 | date | str | 95.02 | 157 | format=DD-Mon-YYYY min=14-May-2015 max=27-Jan-2023 |
| ICD_PRCDR_CD13 | diagnosis_procedure_code | str | 95.79 | 4 | top: Z9981=1448, F08H5ZZ=727, F13=230 |
| PRCDR_DT13 | date | str | 95.79 | 130 | format=DD-Mon-YYYY min=14-Sep-2015 max=28-Jan-2023 |
| ICD_PRCDR_CD14 | diagnosis_procedure_code | str | 96.57 | 5 | top: Z9981=1110, F08H5ZZ=601, F13=204 |
| PRCDR_DT14 | date | str | 96.57 | 103 | format=DD-Mon-YYYY min=15-Sep-2015 max=29-Jan-2023 |
| ICD_PRCDR_CD15 | diagnosis_procedure_code | str | 97.40 | 5 | top: Z9981=800, F08H5ZZ=496, F13=176 |
| PRCDR_DT15 | date | str | 97.40 | 78 | format=DD-Mon-YYYY min=16-Sep-2015 max=30-Jan-2023 |
| ICD_PRCDR_CD16 | diagnosis_procedure_code | str | 98.34 | 4 | top: Z9981=385, F08H5ZZ=368, F13=146 |
| PRCDR_DT16 | date | str | 98.34 | 48 | format=DD-Mon-YYYY min=17-Sep-2015 max=31-Jan-2023 |
| ICD_PRCDR_CD17 | diagnosis_procedure_code | str | 99.12 | 4 | top: F08H5ZZ=283, F13=114, Z9981=88 |
| PRCDR_DT17 | date | str | 99.12 | 21 | format=DD-Mon-YYYY min=18-Sep-2015 max=11-Dec-2022 |
| ICD_PRCDR_CD18 | diagnosis_procedure_code | str | 99.36 | 4 | top: F08H5ZZ=229, Z9981=49, Z8616=46 |
| PRCDR_DT18 | date | str | 99.36 | 15 | format=DD-Mon-YYYY min=19-Sep-2015 max=12-Dec-2022 |
| ICD_PRCDR_CD19 | diagnosis_procedure_code | str | 99.36 | 4 | top: F08H5ZZ=229, Z9981=71, F13=46 |
| PRCDR_DT19 | date | str | 99.36 | 15 | format=DD-Mon-YYYY min=20-Sep-2015 max=13-Dec-2022 |
| ICD_PRCDR_CD20 | diagnosis_procedure_code | str | 99.50 | 4 | top: F08H5ZZ=149, Z9981=49, Z8616=46 |
| PRCDR_DT20 | date | str | 99.50 | 11 | format=DD-Mon-YYYY min=21-Sep-2015 max=14-Dec-2022 |
| ICD_PRCDR_CD21 | diagnosis_procedure_code | str | 99.50 | 4 | top: F08H5ZZ=149, Z9981=71, F13=46 |
| PRCDR_DT21 | date | str | 99.50 | 11 | format=DD-Mon-YYYY min=22-Sep-2015 max=15-Dec-2022 |
| ICD_PRCDR_CD22 | diagnosis_procedure_code | str | 99.57 | 4 | top: F08H5ZZ=127, Z9981=49, F13=46 |
| PRCDR_DT22 | date | str | 99.57 | 9 | format=DD-Mon-YYYY min=23-Sep-2015 max=16-Dec-2022 |
| ICD_PRCDR_CD23 | diagnosis_procedure_code | str | 99.65 | 4 | top: F08H5ZZ=81, Z9981=50, F13=46 |
| PRCDR_DT23 | date | str | 99.65 | 7 | format=DD-Mon-YYYY min=09-Apr-2020 max=17-Dec-2022 |
| ICD_PRCDR_CD24 | diagnosis_procedure_code | str | 99.77 | 3 | top: F08H5ZZ=57, Z9981=49, Z8616=25 |
| PRCDR_DT24 | date | str | 99.77 | 5 | format=DD-Mon-YYYY min=10-Apr-2020 max=05-Aug-2022 |
| ICD_PRCDR_CD25 | diagnosis_procedure_code | str | 99.86 | 2 | top: F08H5ZZ=57, Z9981=25 |
| PRCDR_DT25 | date | str | 99.86 | 3 | format=DD-Mon-YYYY min=11-Apr-2020 max=24-Jan-2021 |
| IME_OP_CLM_VAL_AMT | categorical_code | int64 | 0.00 | 1 | top: 0=58066 |
| DSH_OP_CLM_VAL_AMT | categorical_code | int64 | 0.00 | 1 | top: 0=58066 |
| CLM_UNCOMPD_CARE_PMT_AMT | amount | float64 | 100.00 | 0 | — |
| CLM_LINE_NUM | categorical_code | int64 | 0.00 | 46 | top: 1=20867, 2=8982, 3=7148 |
| REV_CNTR | categorical_code | int64 | 0.00 | 2 | top: 450=43089, 1=14977 |
| HCPCS_CD | categorical_code | str | 0.00 | 106 | top: 99221=8298, G0444=7990, 96156=5080 |
| REV_CNTR_DDCTBL_COINSRNC_CD | categorical_code | float64 | 14.29 | 4 | top: 3.0=44973, 2.0=4555, 1.0=222 |
