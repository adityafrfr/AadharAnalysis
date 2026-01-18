# Economic Growth Zone (EGZ) Identification

This project identifies Economic Growth Zones (EGZ) across India by analyzing Aadhaar enrollment and demographic update data. It detects migration patterns by calculating the Net Migration Ratio (NMR), pinpointing areas where the number of adults updating their details significantly outpaces new enrollments.

## Methodology

The core metric is the **Net Migration Ratio (NMR)**:

```
NMR = (Total Updates - Total Enrollments) / Total Enrollments
```

- **NMR > 0**: Net In-migration (Attraction)
- **NMR < 0**: Net Outflow
- **High Signals**: NMR > 5 suggests very high economic migration.

## Scripts

The analysis is split into progressive stages:

1.  **`analyze_egz.py`**: Initial ingestion and basic candidate identification (UER thresholds).
2.  **`analyze_egz_enhanced.py`**: Adds state and district-level aggregation.
3.  **`analyze_egz_detailed.py`**: deep dive into Net Migration Ratio (NMR) and categorization.
4.  **`analyze_egz_statistical.py`**: Final statistical breakdown, including outliers, correlations, and quartiles.
5.  **`analyze_egz_rural.py`**: Filters candidates for **Rural** areas using India Post office types (B.O. vs H.O.).

## Usage

Ensure you have a Python environment with `pandas` installed.

```bash
# 1. Basic Analysis
python3 analyze_egz.py

# 2. State & District Breakdown
python3 analyze_egz_enhanced.py

# 3. Detailed NMR Metrics
python3 analyze_egz_detailed.py

# 4. Statistical Summary
python3 analyze_egz_statistical.py

# 5. Rural Analysis (Optional)
python3 analyze_egz_rural.py
```

## Outputs

### Reports
- `egz_final_report.md`: The most comprehensive summary of findings.
- `egz_detailed_analysis.md`: Deep dive into migration categories.
- `egz_comprehensive_report.md`: Geographic breakdown.
- `egz_rural_report.md`: Analysis of purely rural growth zones.

### Data Files
- `egz_full_statistical_analysis.csv`: The master dataset with all calculated metrics.
- `egz_candidates_with_location.csv`: List of primary EGZ candidates.
- `egz_candidates_rural.csv`: Filtered list of **1,335 rural candidates**.
- `egz_state_statistics.csv`: State-level aggregate stats.
- `egz_district_nmr_analysis.csv`: District-level counts and rankings.
