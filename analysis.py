import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def calculate_success_rate(df):
    if 'requests_sent' in df.columns and any(col for col in df.columns if '_success' in col):
        success_counts = df[[col for col in df.columns if '_success' in col]].sum(axis=1)
        fail_counts = df[[col.replace('_success', '_fail') for col in df.columns if '_success' in col]].sum(axis=1)

        df['success_rate'] = success_counts / (success_counts + fail_counts)
        df['error_rate'] = fail_counts / (success_counts + fail_counts)
    else:
        raise ValueError("Required columns are missing in the DataFrame.")

def visualize_attack_vector_performance(df):
    attack_vector_names = [col for col in df.columns if '_success' in col]
    success_counts = df[attack_vector_names].sum().values
    fail_counts = df[[col.replace('_success', '_fail') for col in attack_vector_names]].sum().values

    x = range(len(attack_vector_names))

    plt.figure(figsize=(12, 6))
    plt.bar(x, success_counts, width=0.4, label='Success', color='g', align='center')
    plt.bar([p + 0.4 for p in x], fail_counts, width=0.4, label='Failure', color='r', align='center')
    plt.xlabel('Attack Vectors')
    plt.ylabel('Counts')
    plt.title('Attack Vector Performance')
    plt.xticks([p + 0.2 for p in x], attack_vector_names)
    plt.legend()
    plt.tight_layout()
    plt.savefig("attack_vector_performance.png")
    plt.show()

def visualize_success_rate_distribution(df):
    plt.figure(figsize=(10, 6))
    sns.histplot(df['success_rate'], bins=20, kde=True)
    plt.title('Distribution of Success Rates')
    plt.xlabel('Success Rate')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig("success_rate_distribution.png")
    plt.show()

def visualize_correlation_heatmap(df):
    plt.figure(figsize=(12, 8))
    
    # Select only numeric columns for correlation
    numeric_df = df.select_dtypes(include=['float64', 'int64'])
    
    correlation_matrix = numeric_df.corr()
    sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm')
    plt.title('Correlation Heatmap')
    plt.tight_layout()
    plt.savefig("correlation_heatmap.png")
    plt.show()

def visualize_time_series(df):
    plt.figure(figsize=(14, 7))
    sns.lineplot(data=df, x='timestamp', y='error_rate', label='Error Rate', color='r')
    sns.lineplot(data=df, x='timestamp', y='success_rate', label='Success Rate', color='g')
    plt.title('Error and Success Rates Over Time')
    plt.xticks(rotation=45)
    plt.ylabel('Rate')
    plt.xlabel('Timestamp')
    plt.legend()
    plt.tight_layout()
    plt.savefig("error_success_rates_over_time.png")
    plt.show()

if __name__ == "__main__":
    log_file = "detailed_attack_data.csv"
    df = pd.read_csv(log_file)

    print("Columns in DataFrame:", df.columns)

    calculate_success_rate(df)

    visualize_attack_vector_performance(df)
    visualize_success_rate_distribution(df)
    visualize_correlation_heatmap(df)
    visualize_time_series(df)
