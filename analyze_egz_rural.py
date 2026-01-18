import pandas as pd
import os

BASE_DIR = '/home/adifr/Documents/Code/Aaadhar/2'
PINCODE_FILE = 'pincode_offices.csv'
CANDIDATES_FILE = 'egz_candidates_with_location.csv'
OUTPUT_FILE = 'egz_candidates_rural.csv'

def main():
    print("=" * 60)
    print("EGZ RURAL ANALYSIS")
    print("=" * 60)
    
    # 1. Load Pincode Directory
    print("Loading pincode directory...")
    try:
        df_geo = pd.read_csv(os.path.join(BASE_DIR, PINCODE_FILE), encoding='latin1')
    except Exception as e:
        print(f"Error loading {PINCODE_FILE}: {e}")
        return

    # Normalize columns
    df_geo.columns = [c.strip() for c in df_geo.columns]
    
    # 2. Classify Pincodes
    # Logic: 
    # - Rural: Contains at least one 'B.O' (Branch Office)
    # - Urban: Contains 'H.O' (Head Office)
    # - If multiple types, prioritize Urban tag if H.O exists, otherwise Rural if B.O exists.
    
    print("Classifying pincodes...")
    
    def classify_group(group):
        types = set(group['officeType'].unique())
        if 'H.O' in types:
            return 'Urban'
        if 'B.O' in types:
            return 'Rural'
        return 'Semi-Urban' # S.O only or other
        
    pincode_class = df_geo.groupby('pincode').apply(classify_group).reset_index(name='classification')
    
    print(f"Classified {len(pincode_class)} pincodes.")
    print("Distribution:")
    print(pincode_class['classification'].value_counts())
    
    # 3. Load EGZ Candidates
    print("\nLoading EGZ candidates...")
    try:
        df_candidates = pd.read_csv(os.path.join(BASE_DIR, CANDIDATES_FILE))
    except FileNotFoundError:
        print("Candidates file not found.")
        return
        
    # 4. Merge and Filter
    merged = pd.merge(df_candidates, pincode_class, on='pincode', how='left')
    
    # Fill missing classifications as 'Unknown' (or assume rural per user request? No, keep it clean)
    merged['classification'] = merged['classification'].fillna('Unknown')
    
    # Filter for RURAL
    rural_candidates = merged[merged['classification'] == 'Rural'].copy()
    
    print(f"\nTotal EGZ Candidates: {len(df_candidates)}")
    print(f"Rural EGZ Candidates: {len(rural_candidates)}")
    
    if len(rural_candidates) == 0:
        print("No Rural candidates found. Check mapping coverage.")
        # Debug
        print("Sample classifications in merged data:")
        print(merged[['pincode', 'classification']].head())
        return

    # 5. Export
    output_path = os.path.join(BASE_DIR, OUTPUT_FILE)
    rural_candidates.to_csv(output_path, index=False)
    print(f"Exported to: {output_path}")
    
    # 6. Generate Summary
    summary_file = os.path.join(BASE_DIR, 'egz_rural_report.md')
    with open(summary_file, 'w') as f:
        f.write("# Rural EGZ Analysis Report\n\n")
        f.write(f"**Total Rural Candidates**: {len(rural_candidates)}\n\n")
        
        f.write("## Top Rural Growth Districts\n")
        dist_counts = rural_candidates.groupby(['state', 'district']).size().reset_index(name='count')
        dist_counts = dist_counts.sort_values('count', ascending=False).head(20)
        
        f.write("| State | District | Rural EGZ Count |\n")
        f.write("|---|---|---|\n")
        for _, row in dist_counts.iterrows():
            f.write(f"| {row['state']} | {row['district']} | {row['count']} |\n")
            
        f.write("\n## Top Rural Pincodes by Adult In-Migration (UER 18+)\n")
        top_pincodes = rural_candidates.nlargest(10, 'UER_18_plus')
        f.write("| Pincode | State | District | UER 18+ | Total Updates |\n")
        f.write("|---|---|---|---|---|\n")
        for _, row in top_pincodes.iterrows():
            f.write(f"| {row['pincode']} | {row['state']} | {row['district']} | {row['UER_18_plus']:.2f} | {row['total_updates']} |\n")

    print("\nAnalysis Complete.")

if __name__ == "__main__":
    main()
