# run_app.py
"""
Simple startup script for Medical Schedule Management System.
Run this from the project root directory.
"""

import sys
import os
from pathlib import Path

# Ensure we're running from project root
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEBUG_MODE", "true")

if __name__ == "__main__":
    print("🏥 Starting Medical Schedule Management System...")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Working directory: {os.getcwd()}")

    # Import and run the main app
    try:
        import streamlit.web.cli as stcli

        sys.argv = ["streamlit", "run", "src/ui/Main.py"]
        sys.exit(stcli.main())
    except ImportError:
        print("❌ Streamlit not installed. Please run: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        sys.exit(1)
