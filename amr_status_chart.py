import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Read and preprocess the data
df = pd.read_csv('status_log_20250710_130609.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df.sort_values(['Robot_Name', 'Timestamp'], inplace=True)

# Calculate downtime durations
downtimes = []
for name, group in df.groupby('Robot_Name'):
    for i in range(len(group)-1):
        if group.iloc[i]['Event'] == 'Offline' and group.iloc[i+1]['Event'] == 'Online':
            duration = (group.iloc[i+1]['Timestamp'] - group.iloc[i]['Timestamp']).total_seconds() / 60  # minutes
            downtimes.append({
                'Robot_Name': name,
                'Start': group.iloc[i]['Timestamp'],
                'End': group.iloc[i+1]['Timestamp'],
                'Duration': duration
            })
downtime_df = pd.DataFrame(downtimes)

# Plot setup
sns.set_theme(style="whitegrid")
plt.figure(figsize=(12, 8))

# 1. Number of Downtime Events
plt.subplot(2, 2, 1)
event_counts = downtime_df['Robot_Name'].value_counts().reset_index()
sns.barplot(x='count', y='Robot_Name', data=event_counts, palette="Blues_d")
plt.title('Number of Downtime Events')
plt.xlabel('Count')
plt.ylabel('Robot Name')

# 2. Total Downtime Duration
plt.subplot(2, 2, 2)
total_downtime = downtime_df.groupby('Robot_Name')['Duration'].sum().reset_index()
sns.barplot(x='Duration', y='Robot_Name', data=total_downtime, palette="Reds_d")
plt.title('Total Downtime (minutes)')
plt.xlabel('Minutes')
plt.ylabel('')

# 3. Downtime Duration Distribution
plt.subplot(2, 2, 3)
sns.boxplot(x='Robot_Name', y='Duration', data=downtime_df, palette="Set2")
plt.title('Downtime Duration Distribution')
plt.xlabel('Robot Name')
plt.ylabel('Minutes')
plt.yscale('log')  # Log scale for better visualization
plt.ylim(0.1, 1000)

# 4. Latency Distribution
plt.subplot(2, 2, 4)
online_events = df[df['Event'] == 'Online']
sns.boxplot(x='Robot_Name', y='Latency (ms)', data=online_events, palette="Greens_d")
plt.title('Online Event Latency')
plt.xlabel('Robot Name')
plt.ylabel('Milliseconds')

plt.tight_layout()
plt.savefig('robot_status_analysis.png', dpi=300)
plt.show()

# Additional Plot: Timeline of Events
plt.figure(figsize=(14, 8))
event_plot = sns.scatterplot(
    data=df, 
    x='Timestamp', 
    y='Robot_Name', 
    hue='Event',
    style='Event',
    s=100,
    palette={'Online': 'green', 'Offline': 'red'}
)
plt.title('Robot Status Timeline')
plt.xlabel('Timestamp')
plt.ylabel('Robot Name')
plt.grid(True, alpha=0.3)
plt.legend(title='Event Type')
plt.tight_layout()
plt.savefig('status_timeline.png', dpi=300)
plt.show()