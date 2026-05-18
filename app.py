"""Streamlit entry point for the Cali crash dashboard."""

from src.dashboard import render_dashboard


def main() -> None:
    """Run the Streamlit dashboard."""
    render_dashboard()


if __name__ == "__main__":
    main()
