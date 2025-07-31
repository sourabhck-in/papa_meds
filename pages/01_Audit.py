# audit.py - Analytics and Reporting Page for Medical Schedule Management
# Comprehensive reporting and analytics for management insights

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import calendar
from typing import Dict, List, Any

from config import POC_TEAM_LEADER, POC_DOCTORS, WEEKEND_DAYS
from data_ops import load_submissions, format_doctor_name
from validation import calculate_total_duration, is_weekend

# =============================================================================
# APP CONFIGURATION AND INITIALIZATION
# =============================================================================


def setup_app():
    """Configure Streamlit app"""
    st.set_page_config(
        page_title="Audit & Analytics",
        # page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================


def render_filter_section():
    """Render filter controls for the audit page"""
    st.subheader("📊 Schedule Analytics & Audit")

    with st.container(border=True):
        st.write("**Filters**")
        col1, col2, col3 = st.columns(3)

        with col1:
            # Team Leader filter
            tl_options = ["All Team Leaders", POC_TEAM_LEADER["name"]]
            selected_tl = st.selectbox(
                "Team Leader:", options=tl_options, key="audit_tl_filter"
            )

        with col2:
            # Doctor filter
            doctor_options = ["All Doctors"] + [
                format_doctor_name(doc) for doc in POC_DOCTORS
            ]
            selected_doctor = st.selectbox(
                "Doctor:", options=doctor_options, key="audit_doctor_filter"
            )

        with col3:
            # Month filter
            current_date = datetime.now()
            month_options = []

            # Generate last 12 months + next 6 months
            for i in range(-12, 7):
                month_date = current_date.replace(day=1) + timedelta(days=32 * i)
                month_date = month_date.replace(day=1)  # First day of month
                month_label = month_date.strftime("%B %Y")
                month_value = month_date.strftime("%Y-%m")
                month_options.append((month_label, month_value))

            # Default to current month
            current_month_value = current_date.strftime("%Y-%m")
            current_month_label = current_date.strftime("%B %Y")

            month_labels = [opt[0] for opt in month_options]
            month_values = [opt[1] for opt in month_options]

            try:
                default_index = month_values.index(current_month_value)
            except ValueError:
                default_index = 0

            selected_month_label = st.selectbox(
                "Month:",
                options=month_labels,
                index=default_index,
                key="audit_month_filter",
            )

            selected_month = month_values[month_labels.index(selected_month_label)]

    return selected_tl, selected_doctor, selected_month, selected_month_label


def get_filtered_data(selected_tl, selected_doctor, selected_month):
    """Get filtered submission data based on selections"""
    # Load all submissions
    all_submissions = load_submissions()

    if not all_submissions:
        return []

    # Convert to DataFrame for easier filtering
    df = pd.DataFrame(all_submissions)

    # Filter by month
    df["date"] = pd.to_datetime(df["date"])
    month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
    month_end = month_start.replace(
        month=month_start.month % 12 + 1, day=1
    ) - timedelta(days=1)

    df = df[(df["date"] >= month_start) & (df["date"] <= month_end)]

    # Filter by team leader (if not "All")
    if selected_tl != "All Team Leaders":
        # For POC, all doctors belong to John Smith, so no additional filtering needed
        pass

    # Filter by doctor (if not "All")
    if selected_doctor != "All Doctors":
        # Find doctor ID from selected name
        selected_doctor_id = None
        for doc in POC_DOCTORS:
            if format_doctor_name(doc) == selected_doctor:
                selected_doctor_id = doc["id"]
                break

        if selected_doctor_id:
            df = df[df["doctor_id"] == selected_doctor_id]

    return df.to_dict("records")


# =============================================================================
# ANALYTICS FUNCTIONS
# =============================================================================


def calculate_analytics(filtered_data, selected_month):
    """Calculate comprehensive analytics from filtered data"""
    if not filtered_data:
        return {
            "total_sessions": 0,
            "total_hours": 0,
            "days_with_sessions": 0,
            "days_without_sessions": 0,
            "weekend_sessions": 0,
            "weekday_sessions": 0,
            "busiest_day": None,
            "most_hours_day": None,
            "average_session_duration": 0,
            "doctor_breakdown": {},
            "daily_breakdown": {},
        }

    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(filtered_data)
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.weekday.isin(WEEKEND_DAYS)

    # Calculate session durations
    durations = []
    for _, row in df.iterrows():
        try:
            start = datetime.strptime(row["start_time"], "%H:%M")
            end = datetime.strptime(row["end_time"], "%H:%M")
            duration_minutes = (end - start).total_seconds() / 60
            durations.append(duration_minutes)
        except:
            durations.append(0)

    df["duration_minutes"] = durations
    df["duration_hours"] = df["duration_minutes"] / 60

    # Basic statistics
    total_sessions = len(df)
    total_hours = df["duration_hours"].sum()
    weekend_sessions = len(df[df["is_weekend"] == True])
    weekday_sessions = len(df[df["is_weekend"] == False])

    # Daily breakdown
    daily_stats = (
        df.groupby("date")
        .agg({"duration_hours": "sum", "doctor_id": "count"})
        .rename(columns={"doctor_id": "session_count"})
    )

    # Days with/without sessions
    month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
    month_end = month_start.replace(
        month=month_start.month % 12 + 1, day=1
    ) - timedelta(days=1)

    all_days_in_month = pd.date_range(month_start, month_end, freq="D")
    days_with_sessions = len(daily_stats)
    days_without_sessions = len(all_days_in_month) - days_with_sessions

    # Busiest day and most hours day
    busiest_day = None
    most_hours_day = None

    if not daily_stats.empty:
        busiest_day_date = daily_stats["session_count"].idxmax()
        busiest_day = {
            "date": busiest_day_date.strftime("%Y-%m-%d"),
            "sessions": daily_stats.loc[busiest_day_date, "session_count"],
            "hours": daily_stats.loc[busiest_day_date, "duration_hours"],
        }

        most_hours_day_date = daily_stats["duration_hours"].idxmax()
        most_hours_day = {
            "date": most_hours_day_date.strftime("%Y-%m-%d"),
            "hours": daily_stats.loc[most_hours_day_date, "duration_hours"],
            "sessions": daily_stats.loc[most_hours_day_date, "session_count"],
        }

    # Doctor breakdown
    doctor_breakdown = (
        df.groupby("doctor_name")
        .agg({"duration_hours": "sum", "doctor_id": "count"})
        .rename(columns={"doctor_id": "session_count"})
        .to_dict("index")
    )

    # Average session duration
    average_session_duration = df["duration_minutes"].mean() if len(df) > 0 else 0

    return {
        "total_sessions": total_sessions,
        "total_hours": round(total_hours, 2),
        "days_with_sessions": days_with_sessions,
        "days_without_sessions": days_without_sessions,
        "weekend_sessions": weekend_sessions,
        "weekday_sessions": weekday_sessions,
        "busiest_day": busiest_day,
        "most_hours_day": most_hours_day,
        "average_session_duration": round(average_session_duration, 1),
        "doctor_breakdown": doctor_breakdown,
        "daily_breakdown": daily_stats,
        "all_days_in_month": all_days_in_month,
    }


# =============================================================================
# DISPLAY FUNCTIONS
# =============================================================================


def render_key_metrics_and_notable_days(analytics):
    """Render key metrics and notable days in compact layout"""
    st.subheader("📈 Analytics Overview")

    with st.container(border=True):
        # Split into two main sections
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.write("**Key Metrics**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Sessions", analytics["total_sessions"])
            with col2:
                st.metric("Total Hours", f"{analytics['total_hours']:.1f}h")
            with col3:
                st.metric("Days w/Sessions", analytics["days_with_sessions"])
            with col4:
                st.metric(
                    "Avg Duration", f"{analytics['average_session_duration']:.0f}min"
                )

        with right_col:
            st.write("**Notable Days**")
            if analytics["busiest_day"]:
                st.write(
                    f"🔥 **Busiest:** {analytics['busiest_day']['date']} ({analytics['busiest_day']['sessions']} sessions)"
                )
            if analytics["most_hours_day"]:
                st.write(
                    f"⏰ **Most Hours:** {analytics['most_hours_day']['date']} ({analytics['most_hours_day']['hours']:.1f}h)"
                )


# def render_compact_calendar_view(analytics, selected_month):
#     """Render compact week-wise calendar view"""
#     st.subheader("🗓️ Monthly Calendar")

#     with st.container(border=True):
#         if analytics["daily_breakdown"].empty:
#             st.info("No sessions found for the selected period")
#             return

#         st.write(
#             "**Legend:** 🟢 Days with Sessions | ⚪ Weekdays without Sessions | 🟡 Weekends without Sessions"
#         )

#         # Create calendar data
#         month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
#         month_end = month_start.replace(
#             month=month_start.month % 12 + 1, day=1
#         ) - timedelta(days=1)

#         # Get first day of week (Monday = 0)
#         first_weekday = month_start.weekday()

#         # Convert breakdown index to date objects for comparison
#         breakdown_dates = {}
#         if not analytics["daily_breakdown"].empty:
#             for dt_index, row in analytics["daily_breakdown"].iterrows():
#                 date_key = dt_index.date() if hasattr(dt_index, "date") else dt_index
#                 breakdown_dates[date_key] = {
#                     "session_count": row["session_count"],
#                     "duration_hours": row["duration_hours"],
#                 }

#         # Debug: Let's see what dates are in the breakdown
#         st.write("**Debug Info:**")
#         st.write("Breakdown dates:", list(breakdown_dates.keys()))

#         # Create all days in month
#         all_days = []
#         current_date = month_start.date()  # Convert to date object
#         while current_date <= month_end.date():
#             is_weekend_day = current_date.weekday() in WEEKEND_DAYS

#             # Debug for July 27th specifically
#             if current_date.day == 27:
#                 st.write(f"Debug July 27: current_date={current_date}")
#                 st.write(f"Is in breakdown dates: {current_date in breakdown_dates}")

#             if current_date in breakdown_dates:
#                 sessions = int(breakdown_dates[current_date]["session_count"])
#                 hours = breakdown_dates[current_date]["duration_hours"]
#                 has_sessions = sessions > 0
#             else:
#                 sessions = 0
#                 hours = 0
#                 has_sessions = False

#             # Debug for July 27th
#             if current_date.day == 27:
#                 st.write(
#                     f"July 27 - sessions: {sessions}, has_sessions: {has_sessions}, is_weekend: {is_weekend_day}"
#                 )

#             # Choose color: Green if sessions (any day), Yellow if weekend without sessions, White if weekday without sessions
#             if has_sessions:
#                 color = "🟢"  # Any day with sessions = Green
#             elif is_weekend_day:
#                 color = "🟡"  # Weekend without sessions = Yellow
#             else:
#                 color = "⚪"  # Weekday without sessions = White

#             # Debug for July 27th
#             if current_date.day == 27:
#                 st.write(f"July 27 final color: {color}")

#             all_days.append(
#                 {
#                     "date": current_date,
#                     "day": current_date.day,
#                     "color": color,
#                     "sessions": sessions,
#                     "hours": round(hours, 1),
#                     "weekday": current_date.weekday(),
#                 }
#             )

#             current_date += timedelta(days=1)

#         # Group into weeks
#         weeks = []
#         current_week = []

#         # Add empty spaces for days before month starts
#         for i in range(first_weekday):
#             current_week.append({"color": "-", "day": "", "sessions": 0, "hours": 0})

#         # Add all days
#         for day_data in all_days:
#             current_week.append(day_data)

#             # If Sunday (weekday 6) or end of days, complete the week
#             if day_data["weekday"] == 6 or day_data == all_days[-1]:
#                 # Fill remaining spots with empty if needed
#                 while len(current_week) < 7:
#                     current_week.append(
#                         {"color": "-", "day": "", "sessions": 0, "hours": 0}
#                     )

#                 weeks.append(current_week)
#                 current_week = []

#         # Display weeks
#         weekday_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

#         # Header row
#         header_cols = st.columns(7)
#         for i, day_name in enumerate(weekday_headers):
#             with header_cols[i]:
#                 st.write(f"**{day_name}**")

#         # Week rows
#         for week_num, week_data in enumerate(weeks):
#             week_cols = st.columns(7)

#             for i, day_info in enumerate(week_data):
#                 with week_cols[i]:
#                     if day_info["color"] == "-":
#                         st.write("-")
#                     else:
#                         display_text = f"{day_info['color']} {day_info['day']}"
#                         if day_info["sessions"] > 0:
#                             st.write(display_text)
#                             st.caption(f"{day_info['sessions']}s, {day_info['hours']}h")
#                         else:
#                             st.write(display_text)


def render_compact_calendar_view(analytics, selected_month):
    """Render compact week-wise calendar view"""
    st.subheader("🗓️ Monthly Calendar")

    with st.container(border=True):
        if analytics["daily_breakdown"].empty:
            st.info("No sessions found for the selected period")
            return

        st.write(
            "**Legend:** 🟢 Days with Sessions | ⚪ Weekdays without Sessions | 🟡 Weekends without Sessions | S=Sessions, h=Hours"
        )

        # Create calendar data
        month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
        month_end = month_start.replace(
            month=month_start.month % 12 + 1, day=1
        ) - timedelta(days=1)

        # Get first day of week (Monday = 0)
        first_weekday = month_start.weekday()

        # Convert breakdown index to date objects for comparison
        breakdown_dates = {}
        if not analytics["daily_breakdown"].empty:
            for dt_index, row in analytics["daily_breakdown"].iterrows():
                date_key = dt_index.date() if hasattr(dt_index, "date") else dt_index
                breakdown_dates[date_key] = {
                    "session_count": row["session_count"],
                    "duration_hours": row["duration_hours"],
                }

        # Create all days in month
        all_days = []
        current_date = month_start.date()  # Convert to date object
        while current_date <= month_end.date():
            is_weekend_day = current_date.weekday() in WEEKEND_DAYS

            if current_date in breakdown_dates:
                sessions = int(breakdown_dates[current_date]["session_count"])
                hours = breakdown_dates[current_date]["duration_hours"]
                has_sessions = sessions > 0
            else:
                sessions = 0
                hours = 0
                has_sessions = False

            # Choose color: Green if sessions (any day), Yellow if weekend without sessions, White if weekday without sessions
            if has_sessions:
                color = "🟢"  # Any day with sessions = Green
            elif is_weekend_day:
                color = "🟡"  # Weekend without sessions = Yellow
            else:
                color = "⚪"  # Weekday without sessions = White

            all_days.append(
                {
                    "date": current_date,
                    "day": current_date.day,
                    "color": color,
                    "sessions": sessions,
                    "hours": round(hours, 1),
                    "weekday": current_date.weekday(),
                }
            )

            current_date += timedelta(days=1)

        # Group into weeks
        weeks = []
        current_week = []

        # Add empty spaces for days before month starts
        for i in range(first_weekday):
            current_week.append({"color": "-", "day": "", "sessions": 0, "hours": 0})

        # Add all days
        for day_data in all_days:
            current_week.append(day_data)

            # If Sunday (weekday 6) or end of days, complete the week
            if day_data["weekday"] == 6 or day_data == all_days[-1]:
                # Fill remaining spots with empty if needed
                while len(current_week) < 7:
                    current_week.append(
                        {"color": "-", "day": "", "sessions": 0, "hours": 0}
                    )

                weeks.append(current_week)
                current_week = []

        # Display weeks
        weekday_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Header row
        header_cols = st.columns(7)
        for i, day_name in enumerate(weekday_headers):
            with header_cols[i]:
                st.write(f"**{day_name}**")

        # Week rows
        for week_num, week_data in enumerate(weeks):
            week_cols = st.columns(7)

            for i, day_info in enumerate(week_data):
                with week_cols[i]:
                    if day_info["color"] == "-":
                        st.write("-")
                    else:
                        display_text = f"{day_info['color']} {day_info['day']}"
                        if day_info["sessions"] > 0:
                            st.write(display_text)
                            st.caption(f"{day_info['sessions']}s, {day_info['hours']}h")
                        else:
                            st.write(display_text)


def render_analytics_summary(analytics, filtered_data):
    """Render doctor performance and trends in compact layout"""
    st.subheader("📊 Performance & Trends")

    with st.container(border=True):
        left_col, right_col = st.columns(2)

        with left_col:
            st.write("**Doctor Performance**")
            if analytics["doctor_breakdown"]:
                doctor_data = []
                for doctor_name, stats in analytics["doctor_breakdown"].items():
                    # Shorten doctor names for compact display
                    short_name = (
                        doctor_name.split("|")[-1].strip()
                        if "|" in doctor_name
                        else doctor_name
                    )
                    doctor_data.append(
                        {
                            "Doctor": short_name,
                            "Sessions": stats["session_count"],
                            "Hours": f"{stats['duration_hours']:.1f}h",
                        }
                    )

                df_doctors = pd.DataFrame(doctor_data)
                st.dataframe(df_doctors, use_container_width=True, hide_index=True)
            else:
                st.info("No doctor data available")

        with right_col:
            st.write("**Day-of-Week Breakdown**")
            if filtered_data:
                df = pd.DataFrame(filtered_data)
                df["date"] = pd.to_datetime(df["date"])
                df["weekday"] = df["date"].dt.day_name()

                weekday_counts = df["weekday"].value_counts()
                weekday_order = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ]

                for day in weekday_order:
                    count = weekday_counts.get(day, 0)
                    if count > 0:
                        st.write(f"**{day[:3]}:** {count} sessions")
                    else:
                        st.write(f"{day[:3]}: {count} sessions")
            else:
                st.info("No trend data available")


def render_session_distribution(analytics):
    """Render session distribution metrics"""
    st.subheader("📈 Session Distribution")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Days w/o Sessions", analytics["days_without_sessions"])

        with col2:
            st.metric("Weekend Sessions", analytics["weekend_sessions"])

        with col3:
            st.metric("Weekday Sessions", analytics["weekday_sessions"])

        with col4:
            weekend_percentage = (
                (analytics["weekend_sessions"] / analytics["total_sessions"] * 100)
                if analytics["total_sessions"] > 0
                else 0
            )
            st.metric("Weekend %", f"{weekend_percentage:.0f}%")


# =============================================================================
# MAIN AUDIT PAGE
# =============================================================================


def render_audit_page():
    """Main audit page function"""
    st.title("📊 Schedule Analytics & Audit")

    # Filter section
    selected_tl, selected_doctor, selected_month, selected_month_label = (
        render_filter_section()
    )

    st.markdown("---")

    # Get filtered data
    filtered_data = get_filtered_data(selected_tl, selected_doctor, selected_month)

    # Calculate analytics
    analytics = calculate_analytics(filtered_data, selected_month)

    # Display results
    if analytics["total_sessions"] == 0:
        st.warning(
            f"No sessions found for the selected filters ({selected_month_label})"
        )
        st.info("Try selecting a different month or adjusting the filters.")
        return

    # Compact layout - everything in less space
    render_key_metrics_and_notable_days(analytics)

    st.markdown("---")

    # Compact calendar view
    render_compact_calendar_view(analytics, selected_month)

    st.markdown("---")

    # Session distribution
    render_session_distribution(analytics)

    st.markdown("---")

    # Combined analytics
    render_analytics_summary(analytics, filtered_data)

    st.markdown("---")

    # Export placeholder
    st.subheader("📤 Export Options")
    with st.container(border=True):
        st.info("🚧 Excel Export functionality will be implemented next")
        st.button("📊 Export to Excel", disabled=True, help="Coming soon!")


if __name__ == "__main__":
    setup_app()
    render_audit_page()
