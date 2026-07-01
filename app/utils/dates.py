import datetime

def get_current_date_str() -> str:
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.date.today().strftime("%Y-%m-%d")

def get_weekly_folder_name() -> str:
    """Returns the name of the folder for the weekly workflow."""
    return f"{get_current_date_str()}-semana-brandos"
