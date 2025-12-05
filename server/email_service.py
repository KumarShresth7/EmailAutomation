import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from file_monitor import start_monitoring

if __name__ == "__main__":
    print("📧 EMAIL SERVICE STARTED (IMAP Mode)...")
    try:
        start_monitoring()
    except KeyboardInterrupt:
        print("Stopped.")