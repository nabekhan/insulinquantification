from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

def average_glucose(glucose_data: dict, start_time: datetime, end_time: datetime) -> float:
    """
    Calculate the average glucose value between two datetime points (inclusive).

    Parameters:
        glucose_data (dict): Dictionary of {datetime: glucose_value}
        start_time (datetime): Start time (inclusive)
        end_time (datetime): End time (inclusive)

    Returns:
        float: Average glucose value, or None if no data in range.
    """
    if start_time > end_time:
        start_time, end_time = end_time, start_time  # Ensure proper ordering

    # Filter values between start_time and end_time (inclusive)
    values_in_range = [
        value for time, value in glucose_data.items()
        if start_time <= time <= end_time
    ]

    if not values_in_range:
        return None  # Or raise an error / return 0, depending on your use case

    return sum(values_in_range) / len(values_in_range)


def avg_glucose_plot(glucose_data: dict, start_datetime: datetime, end_datetime: datetime, minutes, tz):
    # Convert to DataFrame
    df = pd.DataFrame(list(glucose_data.items()), columns=['datetime', 'glucose'])
    df.set_index('datetime', inplace=True)

    # Convert timezone
    df.index = df.index.tz_convert(tz)

    df.sort_index(inplace=True)

    # Filter to the selected datetime range
    df = df.loc[start_datetime:end_datetime]

    # Resample to 30-minute intervals
    resampled = df.resample(f"{minutes}T").mean()

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(resampled.index, resampled['glucose'], marker='o')
    ax.set_title(f"Average Glucose Every {minutes} Minutes")
    ax.set_xlabel("Datetime")
    ax.set_ylabel("Average Glucose")
    ax.grid(True)
    ax.set_ylim(0, 22)

    return fig
