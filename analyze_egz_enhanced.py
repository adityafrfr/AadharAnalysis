import pandas as pd
import glob
import os

# Configuration
BASE_DIR = '/home/adifr/Documents/Code/Aaadhar/2'
ENROLMENT_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_enrolment')
DEMOGRAPHIC_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_demographic')
OUTPUT_DIR = BASE_DIR

def load_enrolment_with_location(directory):
    """Load enrolment data preserving state/district info."""
    all_files = glob.glob(os.path.join(directory, "*.csv"))
    print(f"Loading {len(all_files)} enrolment files...")
    
    df_list = []
    for filename in all_files:
        df = pd.read_csv(filename)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        df_list.append(df)
    
    full_df = pd.concat(df_list, ignore_index=True)
    
    # Aggregate by pincode-year, keeping state/district (take first occurrence)
    agg_df = full_df.groupby(['pincode', 'year']).agg({
        'state': 'first',
        'district': 'first',
        'age_0_5': 'sum',
        'age_5_17': 'sum',
        'age_18_greater': 'sum'
    }).reset_index()
    
    agg_df['total_enrollments'] = agg_df['age_0_5'] + agg_df['age_5_17'] + agg_df['age_18_greater']
    print(f"Aggregated enrolment data: {len(agg_df)} pincode-year records.")
    return agg_df

def load_demographic_with_location(directory):
    """Load demographic data preserving state/district info."""
    all_files = glob.glob(os.path.join(directory, "*.csv"))
    print(f"Loading {len(all_files)} demographic files...")
    
    df_list = []
    for filename in all_files:
        df = pd.read_csv(filename)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        df_list.append(df)
        
    full_df = pd.concat(df_list, ignore_index=True)
    
    agg_df = full_df.groupby(['pincode', 'year']).agg({
        'state': 'first',
        'district': 'first',
        'demo_age_5_17': 'sum',
        'demo_age_17_': 'sum'
    }).reset_index()
    
    agg_df.rename(columns={
        'demo_age_5_17': 'updates_5_17',
        'demo_age_17_': 'updates_18_plus'
    }, inplace=True)
    
    agg_df['total_updates'] = agg_df['updates_5_17'] + agg_df['updates_18_plus']
    print(f"Aggregated demographic data: {len(agg_df)} pincode-year records.")
    return agg_df

def main():
    print("=" * 60)
    print("ENHANCED EGZ ANALYSIS WITH STATE/DISTRICT BREAKDOWN")
    print("=" * 60)
    
    # 1. Load Data with Location
    df_enrol = load_enrolment_with_location(ENROLMENT_DIR)
    df_demo = load_demographic_with_location(DEMOGRAPHIC_DIR)
    
    # 2. Merge
    merged_df = pd.merge(
        df_enrol, 
        df_demo[['pincode', 'year', 'updates_5_17', 'updates_18_plus', 'total_updates']], 
        on=['pincode', 'year'], 
        how='inner'
    )
    print(f"\nMerged Data: {len(merged_df)} records.")

    # 3. Sanity Filter
    filtered_df = merged_df[merged_df['total_enrollments'] >= 30].copy()
    print(f"After E >= 30 filter: {len(filtered_df)} records.")

    # 4. Calculate Ratios
    filtered_df['UER'] = filtered_df['total_updates'] / filtered_df['total_enrollments']
    filtered_df['UER_18_plus'] = filtered_df['updates_18_plus'] / filtered_df['total_enrollments']
    
    # 5. Identify Candidates
    candidates_list = []
    for year in sorted(filtered_df['year'].unique()):
        year_data = filtered_df[filtered_df['year'] == year].copy()
        p90_uer = year_data['UER'].quantile(0.90)
        p90_uer18 = year_data['UER_18_plus'].quantile(0.90)
        
        candidates = year_data[
            (year_data['UER'] > p90_uer) & 
            (year_data['UER_18_plus'] > p90_uer18)
        ].copy()
        candidates['p90_uer_threshold'] = p90_uer
        candidates['p90_uer18_threshold'] = p90_uer18
        candidates_list.append(candidates)
    
    final_candidates = pd.concat(candidates_list)
    
    # 6. Export Full Candidates with Location
    output_path = os.path.join(OUTPUT_DIR, 'egz_candidates_with_location.csv')
    final_candidates.to_csv(output_path, index=False)
    print(f"\nExported {len(final_candidates)} candidates to: {output_path}")
    
    # =========================================================
    # STATE-LEVEL ANALYSIS
    # =========================================================
    print("\n" + "=" * 60)
    print("STATE-LEVEL EGZ CONCENTRATION")
    print("=" * 60)
    
    state_summary = final_candidates.groupby('state').agg({
        'pincode': 'count',
        'UER': 'mean',
        'UER_18_plus': 'mean',
        'total_enrollments': 'sum',
        'total_updates': 'sum'
    }).rename(columns={'pincode': 'egz_candidate_count'})
    
    state_summary = state_summary.sort_values('egz_candidate_count', ascending=False)
    state_summary['avg_UER'] = state_summary['UER'].round(2)
    state_summary['avg_UER_18+'] = state_summary['UER_18_plus'].round(2)
    
    print("\nTop 15 States by EGZ Candidate Count:")
    print(state_summary[['egz_candidate_count', 'avg_UER', 'avg_UER_18+']].head(15).to_string())
    
    state_output = os.path.join(OUTPUT_DIR, 'egz_state_summary.csv')
    state_summary.to_csv(state_output)
    print(f"\nState summary saved to: {state_output}")
    
    # =========================================================
    # DISTRICT-LEVEL ANALYSIS
    # =========================================================
    print("\n" + "=" * 60)
    print("DISTRICT-LEVEL EGZ HOTSPOTS")
    print("=" * 60)
    
    district_summary = final_candidates.groupby(['state', 'district']).agg({
        'pincode': 'count',
        'UER': 'mean',
        'UER_18_plus': 'mean'
    }).rename(columns={'pincode': 'egz_candidate_count'})
    
    district_summary = district_summary.sort_values('egz_candidate_count', ascending=False)
    
    print("\nTop 20 Districts by EGZ Candidate Count:")
    print(district_summary.head(20).to_string())
    
    district_output = os.path.join(OUTPUT_DIR, 'egz_district_summary.csv')
    district_summary.to_csv(district_output)
    print(f"\nDistrict summary saved to: {district_output}")
    
    # =========================================================
    # GENERATE COMPREHENSIVE REPORT
    # =========================================================
    report_path = os.path.join(OUTPUT_DIR, 'egz_comprehensive_report.md')
    with open(report_path, 'w') as f:
        f.write("# EGZ Comprehensive Analysis Report\n\n")
        f.write(f"**Analysis Date**: 2026-01-18\n")
        f.write(f"**Data Year**: 2025\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Pincodes Analyzed**: {len(filtered_df):,}\n")
        f.write(f"- **EGZ Candidates Identified**: {len(final_candidates):,}\n")
        f.write(f"- **States with EGZ Candidates**: {final_candidates['state'].nunique()}\n")
        f.write(f"- **Districts with EGZ Candidates**: {final_candidates['district'].nunique()}\n\n")
        
        f.write("## Methodology\n\n")
        f.write("A pincode is classified as an EGZ candidate if:\n")
        f.write("1. It has ≥30 new Aadhaar enrollments (statistical validity)\n")
        f.write("2. Its UER (Update-to-Enrollment Ratio) exceeds the 90th percentile\n")
        f.write("3. Its Adult UER (18+ updates / enrollments) exceeds the 90th percentile\n\n")
        
        f.write("## State-Level Concentration\n\n")
        f.write("| State | EGZ Count | Avg UER | Avg UER 18+ |\n")
        f.write("|-------|-----------|---------|-------------|\n")
        for state, row in state_summary.head(15).iterrows():
            f.write(f"| {state} | {int(row['egz_candidate_count'])} | {row['avg_UER']:.1f} | {row['avg_UER_18+']:.1f} |\n")
        
        f.write("\n## Top 20 District Hotspots\n\n")
        f.write("| State | District | EGZ Count |\n")
        f.write("|-------|----------|----------|\n")
        for (state, district), row in district_summary.head(20).iterrows():
            f.write(f"| {state} | {district} | {int(row['egz_candidate_count'])} |\n")
        
        f.write("\n## Top 10 Pincodes by Adult Migration Signal\n\n")
        f.write("| Pincode | State | District | UER 18+ |\n")
        f.write("|---------|-------|----------|--------|\n")
        top_pincodes = final_candidates.nlargest(10, 'UER_18_plus')
        for _, row in top_pincodes.iterrows():
            f.write(f"| {row['pincode']} | {row['state']} | {row['district']} | {row['UER_18_plus']:.1f} |\n")
        
        f.write("\n---\n*Generated by analyze_egz_enhanced.py*\n")
    
    print(f"\nComprehensive report saved to: {report_path}")
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
