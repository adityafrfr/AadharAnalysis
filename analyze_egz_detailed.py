import pandas as pd
import glob
import os

BASE_DIR = '/home/adifr/Documents/Code/Aaadhar/2'
ENROLMENT_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_enrolment')
DEMOGRAPHIC_DIR = os.path.join(BASE_DIR, 'api_data_aadhar_demographic')
OUTPUT_DIR = BASE_DIR

def get_enrolment_data(path):
    files = glob.glob(os.path.join(path, "*.csv"))
    dfs = []
    
    for f in files:
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    
    grouped = combined.groupby(['pincode', 'year']).agg({
        'state': 'first',
        'district': 'first',
        'age_0_5': 'sum',
        'age_5_17': 'sum',
        'age_18_greater': 'sum'
    }).reset_index()
    
    grouped['total_enrollments'] = grouped['age_0_5'] + grouped['age_5_17'] + grouped['age_18_greater']
    return grouped

def get_demographic_data(path):
    files = glob.glob(os.path.join(path, "*.csv"))
    dfs = []
    
    for f in files:
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        df['year'] = df['date'].dt.year
        dfs.append(df)
        
    combined = pd.concat(dfs, ignore_index=True)
    
    grouped = combined.groupby(['pincode', 'year']).agg({
        'state': 'first',
        'district': 'first',
        'demo_age_5_17': 'sum',
        'demo_age_17_': 'sum'
    }).reset_index()
    
    grouped = grouped.rename(columns={
        'demo_age_5_17': 'updates_5_17',
        'demo_age_17_': 'updates_18_plus'
    })
    
    grouped['total_updates'] = grouped['updates_5_17'] + grouped['updates_18_plus']
    return grouped

def get_migration_category(ratio):
    if ratio > 10:
        return 'extreme_attraction'
    if ratio > 5:
        return 'very_high_attraction'
    if ratio > 1:
        return 'high_attraction'
    if ratio > 0:
        return 'moderate_attraction'
    if ratio > -0.5:
        return 'stable'
    return 'net_outflow'

def run_analysis():
    print("Starting EGZ analysis...")
    
    enrolment = get_enrolment_data(ENROLMENT_DIR)
    demographic = get_demographic_data(DEMOGRAPHIC_DIR)
    
    merged = pd.merge(
        enrolment, 
        demographic[['pincode', 'year', 'updates_5_17', 'updates_18_plus', 'total_updates']], 
        on=['pincode', 'year'], 
        how='inner'
    )

    data = merged[merged['total_enrollments'] >= 30].copy()
    print(f"Processing {len(data)} records after filtering...")

    data['UER'] = data['total_updates'] / data['total_enrollments']
    data['UER_18_plus'] = data['updates_18_plus'] / data['total_enrollments']
    
    data['NMR'] = data['UER'] - 1
    data['NMR_adult'] = data['UER_18_plus'] - 1
    
    data['migration_category'] = data['NMR'].apply(get_migration_category)
    
    print(f"Mean NMR: {data['NMR'].mean():.2f}")
    
    state_stats = data.groupby('state').agg({
        'pincode': 'count',
        'NMR': ['mean', 'median', 'std'],
        'NMR_adult': 'mean',
        'total_enrollments': 'sum',
        'total_updates': 'sum'
    })
    
    state_stats.columns = ['pincode_count', 'mean_NMR', 'median_NMR', 'std_NMR', 
                           'mean_NMR_adult', 'total_enrollments', 'total_updates']
    
    state_stats['state_NMR'] = (state_stats['total_updates'] - state_stats['total_enrollments']) / state_stats['total_enrollments']
    state_stats = state_stats.sort_values('state_NMR', ascending=False)
    
    district_stats = data.groupby(['state', 'district']).agg({
        'pincode': 'count',
        'NMR': 'mean',
        'NMR_adult': 'mean',
        'total_enrollments': 'sum',
        'total_updates': 'sum'
    }).reset_index()
    
    district_stats.columns = ['state', 'district', 'pincode_count', 'mean_NMR', 
                              'mean_NMR_adult', 'total_enrollments', 'total_updates']
    
    district_stats['district_NMR'] = (district_stats['total_updates'] - district_stats['total_enrollments']) / district_stats['total_enrollments']
    district_stats = district_stats[district_stats['pincode_count'] >= 5]
    
    data.to_csv(os.path.join(OUTPUT_DIR, 'egz_full_analysis.csv'), index=False)
    state_stats.to_csv(os.path.join(OUTPUT_DIR, 'egz_state_nmr_analysis.csv'))
    district_stats.to_csv(os.path.join(OUTPUT_DIR, 'egz_district_nmr_analysis.csv'), index=False)
    
    with open(os.path.join(OUTPUT_DIR, 'egz_detailed_analysis.md'), 'w') as report:
        report.write("# EGZ Analysis Report\n\n")
        report.write("## Overview\n")
        report.write(f"Analyzed {len(data)} pincodes.\n")
        report.write(f"Average Net Migration Ratio: {data['NMR'].mean():.2f}\n\n")
        
        report.write("## Top States by Net Attraction\n")
        report.write("| State | NMR | Pincodes |\n")
        report.write("|---|---|---|\n")
        for state, row in state_stats.head(10).iterrows():
            report.write(f"| {state} | {row['state_NMR']:.2f} | {int(row['pincode_count'])} |\n")
            
    print("Analysis complete. Files saved.")

if __name__ == "__main__":
    run_analysis()
