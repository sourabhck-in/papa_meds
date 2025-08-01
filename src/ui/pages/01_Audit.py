# src/ui/pages/audit.py
"""
Analytics and Reporting Page for Medical Schedule Management System

Comprehensive reporting and analytics for management insights
with proper logging and modular architecture.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import calendar
from typing import Dict, List, Any, Optional, Tuple

# Import our modular components
from src.utils.logging_config import get_logger, setup_logging
from src.utils.config import (
    APP_ICON,
    POC_TEAM_LEADER,
    POC_DOCTORS,
    WEEKEND_DAYS,
    get_streamlit_config,
    is_debug_mode,
)
from src.infrastructure.sheets.sheets_ops import (
    load_submissions,
    format_doctor_name,
    get_sheets_stats,
    validate_sheets_connection,
)
from src.core.validators.validation import (
    calculate_total_duration,
    is_weekend,
)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# =============================================================================
# APP CONFIGURATION
# =============================================================================


def setup_audit_app() -> None:
    """Configure Streamlit app for audit page"""
    logger.info("Setting up audit page...")

    try:
        config = get_streamlit_config()
        config["page_title"] = "Schedule Analytics & Audit"
        st.set_page_config(**config)

        # Validate Google Sheets connection
        if not validate_sheets_connection():
            st.error("❌ Google Sheets connection failed. Cannot load audit data.")
            logger.error("Google Sheets connection failed on audit page")
            st.stop()

        logger.info("Audit page setup complete")

    except Exception as e:
        logger.error(f"Failed to setup audit page: {str(e)}")
        st.error(f"❌ Audit page setup failed: {str(e)}")
        st.stop()


# =============================================================================
# FILTER COMPONENTS
# =============================================================================


def render_audit_header() -> None:
    """Render the audit page header"""
    logger.debug("Rendering audit page header")

    st.title("📊 Schedule Analytics & Audit")

    if is_debug_mode():
        with st.expander("🔧 Debug Information", expanded=False):
            render_audit_debug_info()


def render_audit_debug_info() -> None:
    """Render debug information for audit page"""
    try:
        stats = get_sheets_stats()
        st.json({"sheets_stats": stats})
    except Exception as e:
        st.error(f"Debug info error: {str(e)}")
        logger.error(f"Error rendering audit debug info: {str(e)}")


def render_filter_section() -> Tuple[str, str, str, str]:
    """
    Render filter controls for the audit page.

    Returns:
        Tuple of (selected_tl, selected_doctor, selected_month, selected_month_label)
    """
    logger.debug("Rendering filter section")

    st.subheader("📊 Schedule Analytics & Audit")

    with st.container(border=True):
        st.write("**Filters**")
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_tl = render_team_leader_filter()

        with col2:
            selected_doctor = render_doctor_filter()

        with col3:
            selected_month, selected_month_label = render_month_filter()

    logger.debug(
        f"Filters selected - TL: {selected_tl}, Doctor: {selected_doctor}, Month: {selected_month}"
    )
    return selected_tl, selected_doctor, selected_month, selected_month_label


def render_team_leader_filter() -> str:
    """Render team leader filter"""
    tl_options = ["All Team Leaders", POC_TEAM_LEADER["name"]]
    selected_tl = st.selectbox(
        "Team Leader:", options=tl_options, key="audit_tl_filter"
    )
    return selected_tl


def render_doctor_filter() -> str:
    """Render doctor filter"""
    doctor_options = ["All Doctors"] + [format_doctor_name(doc) for doc in POC_DOCTORS]
    selected_doctor = st.selectbox(
        "Doctor:", options=doctor_options, key="audit_doctor_filter"
    )
    return selected_doctor


def render_month_filter() -> Tuple[str, str]:
    """
    Render month filter with past and future months.

    Returns:
        Tuple of (selected_month_value, selected_month_label)
    """
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
    return selected_month, selected_month_label


# =============================================================================
# DATA LOADING AND FILTERING
# =============================================================================


def get_filtered_audit_data(
    selected_tl: str, selected_doctor: str, selected_month: str
) -> List[Dict]:
    """
    Get filtered submission data based on audit selections.

    Args:
        selected_tl: Selected team leader
        selected_doctor: Selected doctor
        selected_month: Selected month (YYYY-MM format)

    Returns:
        List of filtered submission dictionaries
    """
    logger.info(
        f"Loading filtered audit data - TL: {selected_tl}, Doctor: {selected_doctor}, Month: {selected_month}"
    )

    try:
        # Load all submissions from Google Sheets
        all_submissions = load_submissions()

        if not all_submissions:
            logger.warning("No submissions found for audit")
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
            selected_doctor_id = find_doctor_id_by_name(selected_doctor)
            if selected_doctor_id:
                df = df[df["doctor_id"] == selected_doctor_id]

        filtered_data = df.to_dict("records")
        logger.info(f"Filtered to {len(filtered_data)} submissions for audit")
        return filtered_data

    except Exception as e:
        logger.error(f"Error getting filtered audit data: {str(e)}")
        return []


def find_doctor_id_by_name(doctor_name: str) -> Optional[str]:
    """
    Find doctor ID by formatted name.

    Args:
        doctor_name: Formatted doctor name

    Returns:
        Doctor ID or None
    """
    for doc in POC_DOCTORS:
        if format_doctor_name(doc) == doctor_name:
            return doc["id"]
    return None


# =============================================================================
# ANALYTICS CALCULATIONS
# =============================================================================


def calculate_comprehensive_analytics(
    filtered_data: List[Dict], selected_month: str
) -> Dict[str, Any]:
    """
    Calculate comprehensive analytics from filtered data.

    Args:
        filtered_data: List of filtered submission dictionaries
        selected_month: Selected month for calculations

    Returns:
        Dictionary with calculated analytics
    """
    logger.info(f"Calculating analytics for {len(filtered_data)} submissions")

    try:
        if not filtered_data:
            return get_empty_analytics_result()

        # Convert to DataFrame for analysis
        df = pd.DataFrame(filtered_data)
        df["date"] = pd.to_datetime(df["date"])
        df["weekday"] = df["date"].dt.day_name()
        df["is_weekend"] = df["date"].dt.weekday.isin(WEEKEND_DAYS)

        # Calculate session durations
        df = calculate_session_durations(df)

        # Calculate analytics
        analytics = {
            "total_sessions": len(df),
            "total_hours": round(df["duration_hours"].sum(), 2),
            "weekend_sessions": len(df[df["is_weekend"] == True]),
            "weekday_sessions": len(df[df["is_weekend"] == False]),
            "average_session_duration": (
                round(df["duration_minutes"].mean(), 1) if len(df) > 0 else 0
            ),
        }

        # Calculate day-based metrics
        analytics.update(calculate_day_metrics(df, selected_month))

        # Calculate doctor breakdown
        analytics["doctor_breakdown"] = calculate_doctor_breakdown(df)

        logger.info(
            f"Analytics calculated: {analytics['total_sessions']} sessions, {analytics['total_hours']} hours"
        )
        return analytics

    except Exception as e:
        logger.error(f"Error calculating analytics: {str(e)}")
        return get_empty_analytics_result()


def get_empty_analytics_result() -> Dict[str, Any]:
    """Get empty analytics result for error cases"""
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
        "daily_breakdown": pd.DataFrame(),
    }


def calculate_session_durations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate session durations and add to DataFrame.

    Args:
        df: DataFrame with session data

    Returns:
        DataFrame with duration columns added
    """
    durations = []
    for _, row in df.iterrows():
        try:
            start = datetime.strptime(row["start_time"], "%H:%M")
            end = datetime.strptime(row["end_time"], "%H:%M")
            duration_minutes = (end - start).total_seconds() / 60
            durations.append(duration_minutes)
        except Exception as e:
            logger.warning(f"Error calculating duration for session: {str(e)}")
            durations.append(0)

    df["duration_minutes"] = durations
    df["duration_hours"] = df["duration_minutes"] / 60
    return df


def calculate_day_metrics(df: pd.DataFrame, selected_month: str) -> Dict[str, Any]:
    """
    Calculate day-based metrics for analytics.

    Args:
        df: DataFrame with session data
        selected_month: Selected month string

    Returns:
        Dictionary with day-based metrics
    """
    try:
        # Daily breakdown
        daily_stats = (
            df.groupby("date")
            .agg({"duration_hours": "sum", "doctor_id": "count"})
            .rename(columns={"doctor_id": "session_count"})
        )

        # Calculate days with/without sessions
        month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
        month_end = month_start.replace(
            month=month_start.month % 12 + 1, day=1
        ) - timedelta(days=1)

        all_days_in_month = pd.date_range(month_start, month_end, freq="D")
        days_with_sessions = len(daily_stats)
        days_without_sessions = len(all_days_in_month) - days_with_sessions

        # Find busiest day and most hours day
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

        return {
            "days_with_sessions": days_with_sessions,
            "days_without_sessions": days_without_sessions,
            "busiest_day": busiest_day,
            "most_hours_day": most_hours_day,
            "daily_breakdown": daily_stats,
            "all_days_in_month": all_days_in_month,
        }

    except Exception as e:
        logger.error(f"Error calculating day metrics: {str(e)}")
        return {
            "days_with_sessions": 0,
            "days_without_sessions": 0,
            "busiest_day": None,
            "most_hours_day": None,
            "daily_breakdown": pd.DataFrame(),
            "all_days_in_month": [],
        }


def calculate_doctor_breakdown(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Calculate doctor performance breakdown.

    Args:
        df: DataFrame with session data

    Returns:
        Dictionary with doctor breakdown
    """
    try:
        doctor_breakdown = (
            df.groupby("doctor_name")
            .agg({"duration_hours": "sum", "doctor_id": "count"})
            .rename(columns={"doctor_id": "session_count"})
            .to_dict("index")
        )

        logger.debug(f"Calculated doctor breakdown for {len(doctor_breakdown)} doctors")
        return doctor_breakdown

    except Exception as e:
        logger.error(f"Error calculating doctor breakdown: {str(e)}")
        return {}


# =============================================================================
# ANALYTICS DISPLAY COMPONENTS
# =============================================================================


def render_key_metrics_overview(analytics: Dict[str, Any]) -> None:
    """
    Render key metrics and notable days in compact layout.

    Args:
        analytics: Analytics dictionary
    """
    logger.debug("Rendering key metrics overview")

    st.subheader("📈 Analytics Overview")

    with st.container(border=True):
        left_col, right_col = st.columns([3, 2])

        with left_col:
            render_key_metrics(analytics)

        with right_col:
            render_notable_days(analytics)


def render_key_metrics(analytics: Dict[str, Any]) -> None:
    """Render key metrics section"""
    st.write("**Key Metrics**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Sessions", analytics["total_sessions"])
    with col2:
        st.metric("Total Hours", f"{analytics['total_hours']:.1f}h")
    with col3:
        st.metric("Days w/Sessions", analytics["days_with_sessions"])
    with col4:
        st.metric("Avg Duration", f"{analytics['average_session_duration']:.0f}min")


def render_notable_days(analytics: Dict[str, Any]) -> None:
    """Render notable days section"""
    st.write("**Notable Days**")

    if analytics["busiest_day"]:
        busiest = analytics["busiest_day"]
        st.write(f"🔥 **Busiest:** {busiest['date']} ({busiest['sessions']} sessions)")

    if analytics["most_hours_day"]:
        most_hours = analytics["most_hours_day"]
        st.write(
            f"⏰ **Most Hours:** {most_hours['date']} ({most_hours['hours']:.1f}h)"
        )


def render_monthly_calendar(analytics: Dict[str, Any], selected_month: str) -> None:
    """
    Render compact week-wise calendar view.

    Args:
        analytics: Analytics dictionary
        selected_month: Selected month string
    """
    logger.debug(f"Rendering monthly calendar for {selected_month}")

    st.subheader("🗓️ Monthly Calendar")

    with st.container(border=True):
        if analytics["daily_breakdown"].empty:
            st.info("No sessions found for the selected period")
            return

        try:
            calendar_data = generate_calendar_data(analytics, selected_month)
            render_calendar_grid(calendar_data)

        except Exception as e:
            logger.error(f"Error rendering monthly calendar: {str(e)}")
            st.error("❌ Error rendering calendar. Please try again.")


def generate_calendar_data(
    analytics: Dict[str, Any], selected_month: str
) -> List[Dict]:
    """
    Generate calendar data for the month.

    Args:
        analytics: Analytics dictionary
        selected_month: Selected month string

    Returns:
        List of day data dictionaries
    """
    logger.debug(f"Generating calendar data for {selected_month}")

    # Legend
    st.write(
        "**Legend:** 🟢 Days with Sessions | ⚪ Weekdays without Sessions | 🟡 Weekends without Sessions | S=Sessions, h=Hours"
    )

    # Create calendar data
    month_start = datetime.strptime(selected_month + "-01", "%Y-%m-%d")
    month_end = month_start.replace(
        month=month_start.month % 12 + 1, day=1
    ) - timedelta(days=1)

    # Convert breakdown to usable format
    breakdown_dates = {}
    if not analytics["daily_breakdown"].empty:
        for dt_index, row in analytics["daily_breakdown"].iterrows():
            date_key = dt_index.date() if hasattr(dt_index, "date") else dt_index
            breakdown_dates[date_key] = {
                "session_count": row["session_count"],
                "duration_hours": row["duration_hours"],
            }

    # Generate all days in month
    all_days = []
    current_date = month_start.date()

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

        # Choose color
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

    return all_days


def render_calendar_grid(all_days: List[Dict]) -> None:
    """
    Render the calendar grid.

    Args:
        all_days: List of day data dictionaries
    """
    # Group into weeks
    weeks = group_days_into_weeks(all_days)

    # Display calendar
    weekday_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Header row
    header_cols = st.columns(7)
    for i, day_name in enumerate(weekday_headers):
        with header_cols[i]:
            st.write(f"**{day_name}**")

    # Week rows
    for week_data in weeks:
        week_cols = st.columns(7)

        for i, day_info in enumerate(week_data):
            with week_cols[i]:
                render_calendar_day(day_info)


def group_days_into_weeks(all_days: List[Dict]) -> List[List[Dict]]:
    """
    Group days into weeks for calendar display.

    Args:
        all_days: List of day data dictionaries

    Returns:
        List of weeks (each week is a list of day dictionaries)
    """
    if not all_days:
        return []

    weeks = []
    current_week = []

    # Add empty spaces for days before month starts
    first_weekday = all_days[0]["weekday"]
    for i in range(first_weekday):
        current_week.append({"color": "-", "day": "", "sessions": 0, "hours": 0})

    # Add all days
    for day_data in all_days:
        current_week.append(day_data)

        # If Sunday (weekday 6) or end of days, complete the week
        if day_data["weekday"] == 6 or day_data == all_days[-1]:
            # Fill remaining spots if needed
            while len(current_week) < 7:
                current_week.append(
                    {"color": "-", "day": "", "sessions": 0, "hours": 0}
                )

            weeks.append(current_week)
            current_week = []

    return weeks


def render_calendar_day(day_info: Dict) -> None:
    """
    Render a single calendar day.

    Args:
        day_info: Day information dictionary
    """
    if day_info["color"] == "-":
        st.write("-")
    else:
        display_text = f"{day_info['color']} {day_info['day']}"
        if day_info["sessions"] > 0:
            st.write(display_text)
            st.caption(f"{day_info['sessions']}s, {day_info['hours']}h")
        else:
            st.write(display_text)


def render_performance_analytics(
    analytics: Dict[str, Any], filtered_data: List[Dict]
) -> None:
    """
    Render doctor performance and trends analytics.

    Args:
        analytics: Analytics dictionary
        filtered_data: Filtered submission data
    """
    logger.debug("Rendering performance analytics")

    st.subheader("📊 Performance & Trends")

    with st.container(border=True):
        left_col, right_col = st.columns(2)

        with left_col:
            render_doctor_performance(analytics)

        with right_col:
            render_day_of_week_breakdown(filtered_data)


def render_doctor_performance(analytics: Dict[str, Any]) -> None:
    """Render doctor performance section"""
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


def render_day_of_week_breakdown(filtered_data: List[Dict]) -> None:
    """Render day-of-week breakdown"""
    st.write("**Day-of-Week Breakdown**")

    if filtered_data:
        try:
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

        except Exception as e:
            logger.error(f"Error rendering day-of-week breakdown: {str(e)}")
            st.error("Error calculating day breakdown")
    else:
        st.info("No trend data available")


def render_session_distribution(analytics: Dict[str, Any]) -> None:
    """
    Render session distribution metrics.

    Args:
        analytics: Analytics dictionary
    """
    logger.debug("Rendering session distribution")

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


def render_export_section() -> None:
    """Render export options section"""
    logger.debug("Rendering export section")

    st.subheader("📤 Export Options")

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Go to Excel Export", use_container_width=True):
                st.switch_page("src/ui/pages/export.py")

        with col2:
            st.info("🚧 Additional export formats coming soon!")


# =============================================================================
# MAIN AUDIT PAGE FUNCTION
# =============================================================================


def render_audit_page() -> None:
    """Main audit page rendering function"""
    logger.info("Rendering audit page")

    try:
        # Render header
        render_audit_header()

        # Filter section
        selected_tl, selected_doctor, selected_month, selected_month_label = (
            render_filter_section()
        )

        st.markdown("---")

        # Get filtered data
        with st.spinner("Loading audit data..."):
            filtered_data = get_filtered_audit_data(
                selected_tl, selected_doctor, selected_month
            )

        # Calculate analytics
        analytics = calculate_comprehensive_analytics(filtered_data, selected_month)

        # Display results
        if analytics["total_sessions"] == 0:
            render_no_data_message(selected_month_label)
            return

        # Render analytics sections
        render_key_metrics_overview(analytics)
        st.markdown("---")

        render_monthly_calendar(analytics, selected_month)
        st.markdown("---")

        render_session_distribution(analytics)
        st.markdown("---")

        render_performance_analytics(analytics, filtered_data)
        st.markdown("---")

        render_export_section()

        logger.info("Audit page rendering complete")

    except Exception as e:
        logger.error(f"Error rendering audit page: {str(e)}")
        st.error("❌ An error occurred while loading the audit page. Please refresh.")


def render_no_data_message(selected_month_label: str) -> None:
    """
    Render message when no data is available.

    Args:
        selected_month_label: Selected month label for display
    """
    st.warning(f"No sessions found for the selected filters ({selected_month_label})")
    st.info("Try selecting a different month or adjusting the filters.")

    # Show connection status
    try:
        stats = get_sheets_stats()
        if stats["total_submissions"] > 0:
            st.info(f"📊 Total submissions in system: {stats['total_submissions']}")
        else:
            st.info("📊 No submissions found in the system")
    except Exception as e:
        logger.warning(f"Could not load sheets stats: {str(e)}")


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================


def main() -> None:
    """Main audit application entry point"""
    logger.info("Starting audit page application")

    try:
        # Setup app
        setup_audit_app()

        # Render audit page
        render_audit_page()

    except Exception as e:
        logger.critical(f"Critical error in audit application: {str(e)}")
        st.error("❌ Critical error in audit page. Please check logs.")

        if is_debug_mode():
            st.exception(e)


if __name__ == "__main__":
    main()
