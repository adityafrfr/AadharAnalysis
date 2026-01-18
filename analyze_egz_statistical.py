import pandas as pd
import os

BASE_DIR = '/home/adifr/Documents/Code/Aaadhar/2'
OUTPUT_DIR = BASE_DIR

def analyze_statistics():
    print("Running statistical analysis...")
    
    try:
        df = pd.read_csv(os.path.join(BASE_DIR, 'egz_full_analysis.csv'))
    except FileNotFoundError:
        print("Input file not found. Run analyze_egz_detailed.py first.")
        return

    quartiles = {
        'NMR': df['NMR'].quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_dict()
    }
    
    print(f"Median NMR: {quartiles['NMR'][0.5]:.2f}")
    
    df['NMR_quartile'] = pd.qcut(df['NMR'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    
    corr_nmr_adult = df['NMR'].corr(df['NMR_adult'])
    print(f"Correlation (NMR vs Adult NMR): {corr_nmr_adult:.4f}")
    
    bins = [-1, 0, 1, 2, 5, 10, 20, 50, 120]
    labels = ['<0', '0-1', '1-2', '2-5', '5-10', '10-20', '20-50', '50+']
    df['NMR_bin'] = pd.cut(df['NMR'], bins=bins, labels=labels)
    
    distribution = df['NMR_bin'].value_counts().sort_index()
    
    df['area_type'] = pd.cut(
        df['total_enrollments'], 
        bins=[0, 100, 500, 1000, float('inf')],
        labels=['Low', 'Medium', 'High', 'Very High']
    )
    
    area_stats = df.groupby('area_type').agg({
        'NMR': ['mean', 'median', 'std', 'count']
    })
    
    state_stats = df.groupby('state').agg({
        'NMR': ['min', 'median', 'max', 'mean', 'count']
    }).sort_values(('NMR', 'median'), ascending=False)
    
    mean_val = df['NMR'].mean()
    std_val = df['NMR'].std()
    upper = mean_val + 3 * std_val
    lower = mean_val - 3 * std_val
    
    anomalies = df[(df['NMR'] > upper) | (df['NMR'] < lower)]
    df['is_anomaly'] = df.index.isin(anomalies.index)
    
    q_df = pd.DataFrame.from_dict(quartiles['NMR'], orient='index', columns=['Value'])
    q_df.to_csv(os.path.join(OUTPUT_DIR, 'egz_quartile_analysis.csv'))
    
    state_stats.to_csv(os.path.join(OUTPUT_DIR, 'egz_state_statistics.csv'))
    distribution.to_csv(os.path.join(OUTPUT_DIR, 'egz_distribution.csv'))
    df.to_csv(os.path.join(OUTPUT_DIR, 'egz_full_statistical_analysis.csv'), index=False)
    
    with open(os.path.join(OUTPUT_DIR, 'egz_final_report.md'), 'w') as f:
        f.write("# Final Statistical Report\n\n")
        f.write(f"Processed {len(df)} records.\n\n")
        
        f.write("## Key Metrics\n")
        f.write(f"- Median NMR: {quartiles['NMR'][0.5]:.2f}\n")
        f.write(f"- Correlation (Total vs Adult): {corr_nmr_adult:.4f}\n")
        f.write(f"- Anomalies Found: {len(anomalies)}\n\n")
        
        f.write("## Distribution\n")
        for label, count in distribution.items():
            pct = count / len(df) * 100
            f.write(f"- {label}: {count} ({pct:.1f}%)\n")

    print("Statistical analysis complete.")

if __name__ == "__main__":
    analyze_statistics()
