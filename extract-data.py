import pandas as pd

def extract_advanced_metrics(log_file, output_file):
    # Read the log file
    df = pd.read_csv(log_file)

    # Calculate total requests
    df['total_requests'] = df.filter(like='_success').sum(axis=1) + df.filter(like='_fail').sum(axis=1)

    # Calculate average request size
    df['average_request_size'] = df['bytes_sent'] / df['total_requests'].replace(0, 1)

    # Calculate error rate
    df['error_rate'] = df.filter(like='_fail').sum(axis=1) / df['total_requests'].replace(0, 1)

    # Save to new CSV
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    log_file = "advanced_attack_log.csv"
    output_file = "detailed_attack_data.csv"
    extract_advanced_metrics(log_file, output_file)
