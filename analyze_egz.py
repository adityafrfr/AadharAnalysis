import pandas as pd
import glob
import os

# Configuration: Paths to the data folders
BASE_DIR = '/home/adifr/Documents/Code/Aaadhar/2'
ENROLMENT_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_enrolment')
DEMOGRAPHIC_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_demographic')
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_and_aggregate_enrolment(directory):
    """
    Reads all enrolment CSVs, extracts year, and aggregates by Pincode-Year.
    """
    all_files = glob.glob(os.path.join(directory, "*.csv"))
    print(f"Loading {len(all_files)} enrolment files...")
    
    df_list = []
    for filename in all_files:
        df = pd.read_csv(filename)
        # Parse Dates (Format seems to be DD-MM-YYYY based on file preview)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        df_list.append(df)
    
    if not df_list:
        print("No enrolment files found.")
        return pd.DataFrame()

    full_df = pd.concat(df_list, ignore_index=True)
    
    # Selecting relevant columns and aggregating
    # Columns: pincode, age_0_5, age_5_17, age_18_greater
    agg_df = full_df.groupby(['pincode', 'year'])[[
        'age_0_5', 'age_5_17', 'age_18_greater'
    ]].sum().reset_index()
    
    # Calculate Total Enrollments (E_it)
    agg_df['total_enrollments'] = agg_df['age_0_5'] + agg_df['age_5_17'] + agg_df['age_18_greater']
    
    print(f"Aggregated enrolment data: {len(agg_df)} pincode-year records.")
    return agg_df

def load_and_aggregate_demographic(directory):
    """
    Reads all demographic CSVs, extracts year, and aggregates by Pincode-Year.
    """
    all_files = glob.glob(os.path.join(directory, "*.csv"))
    print(f"Loading {len(all_files)} demographic files...")
    
    df_list = []
    for filename in all_files:
        df = pd.read_csv(filename)
        # Parse Dates
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        df_list.append(df)
        
    if not df_list:
        print("No demographic files found.")
        return pd.DataFrame()
        
    full_df = pd.concat(df_list, ignore_index=True)
    
    # Columns: demo_age_5_17, demo_age_17_ (assuming demo_age_17_ is 18+)
    # Note: 0-5 is missing, as identified in analysis.
    agg_df = full_df.groupby(['pincode', 'year'])[[
        'demo_age_5_17', 'demo_age_17_'
    ]].sum().reset_index()
    
    # Rename columns for clarity
    agg_df.rename(columns={
        'demo_age_5_17': 'updates_5_17',
        'demo_age_17_': 'updates_18_plus'
    }, inplace=True)
    
    # Calculate Total Updates (U_it) - Note: U_0_5 is effectively 0 here due to missing data
    agg_df['total_updates'] = agg_df['updates_5_17'] + agg_df['updates_18_plus']
    
    print(f"Aggregated demographic data: {len(agg_df)} pincode-year records.")
    return agg_df

def main():
    print("Starting EGZ Analysis...")
    
    # 1. Ingest Data
    df_enrol = load_and_aggregate_enrolment(ENROLMENT_DIR)
    df_demo = load_and_aggregate_demographic(DEMOGRAPHIC_DIR)
    
    if df_enrol.empty or df_demo.empty:
        print("CRITICAL ERROR: Data missing.")
        return

    # 2. Merge Datasets
    # We want valid intersections to calculate ratios, but outer join allows us to see gaps.
    # The methodology implies we need both Enrollments and Updates to calculate UER.
    merged_df = pd.merge(df_enrol, df_demo, on=['pincode', 'year'], how='inner')
    print(f"Merged Data: {len(merged_df)} records.")

    # 3. Sanity Filter: E_it < 30
    filtered_df = merged_df[merged_df['total_enrollments'] >= 30].copy()
    dropped_count = len(merged_df) - len(filtered_df)
    print(f"Sanity Filter (E >= 30): Dropped {dropped_count} records. Remaining: {len(filtered_df)}")

    # 4. Calculate Ratios
    # UER = Total Updates / Total Enrollments
    filtered_df['UER'] = filtered_df['total_updates'] / filtered_df['total_enrollments']
    
    # Adult-Dominant UER = Updates 18+ / Total Enrollments
    filtered_df['UER_18_plus'] = filtered_df['updates_18_plus'] / filtered_df['total_enrollments']
    
    # 5. Define "High" Thresholds & Identify Candidates
    candidates_list = []
    
    years = filtered_df['year'].unique()
    print("\nYearly Thresholds and Candidates:")
    
    for year in sorted(years):
        year_data = filtered_df[filtered_df['year'] == year].copy()
        
        # Calculate P90 for this year
        p90_uer = year_data['UER'].quantile(0.90)
        p90_uer18 = year_data['UER_18_plus'].quantile(0.90)
        
        print(f"Year {year}: P90(UER) = {p90_uer:.4f}, P90(UER_18+) = {p90_uer18:.4f}")
        
        # Candidate Logic
        candidates = year_data[
            (year_data['UER'] > p90_uer) & 
            (year_data['UER_18_plus'] > p90_uer18)
        ]
        
        print(f"  -> Found {len(candidates)} EGZ candidates.")
        candidates_list.append(candidates)
        
    # 6. Export Results
    final_candidates = pd.concat(candidates_list)
    output_path = os.path.join(OUTPUT_DIR, 'egz_candidates.csv')
    final_candidates.to_csv(output_path, index=False)
    print(f"\nAnalysis Complete. Exported {len(final_candidates)} candidates to:\n{output_path}")

    # Generate Summary Report
    with open('analysis_summary.md', 'w') as f:
        f.write("# EGZ Analysis Summary\n\n")
        f.write(f"- Total candidates identified: {len(final_candidates)}\n")
        f.write("- Years analyzed: " + ", ".join(map(str, sorted(years))) + "\n\n")
        f.write("## Sample Candidates (Top 5 by UER_18+)\n")
        top_5 = final_candidates.sort_values(by='UER_18_plus', ascending=False).head(5)
        f.write(top_5[['pincode', 'year', 'total_enrollments', 'UER', 'UER_18_plus']].to_markdown(index=False))

if __name__ == "__main__":
    main()
