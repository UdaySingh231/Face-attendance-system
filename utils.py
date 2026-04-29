import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def generate_attendance_pie_chart(total_students, present_students):
    """Generates a pie chart of attendance."""
    labels = ['Present', 'Absent']
    values = [present_students, max(0, total_students - present_students)]
    
    fig = px.pie(names=labels, values=values, title=f"Today's Attendance ({datetime.now().strftime('%Y-%m-%d')})")
    fig.update_traces(marker=dict(colors=['#00CC96', '#EF553B']))
    return fig

def generate_weekly_bar_chart(attendance_records):
    """Generates a bar chart from attendance records dataframe."""
    if not attendance_records:
        return None
        
    df = pd.DataFrame(attendance_records)
    # Count occurrences per date
    daily_counts = df.groupby('date').size().reset_index(name='Present Students')
    
    fig = px.bar(daily_counts, x='date', y='Present Students', title="Recent Attendance History")
    fig.update_layout(xaxis_title="Date", yaxis_title="Number of Students Present")
    return fig
