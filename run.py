"""
run.py
Convenience launcher for the IPL Analytics Full-Stack Application.
Run with: python run.py
"""
import os
import sys
import subprocess
import webbrowser

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "ipl.db")

    if not os.path.exists(db_path):
        print("⚡ Database not found. Building ipl.db from CSVs...")
        subprocess.run([sys.executable, os.path.join(base_dir, "01_build_database.py")], check=True)

    print("\n" + "="*60)
    print("🏏 IPL MATCH & PERFORMANCE ANALYTICS PLATFORM")
    print("="*60)
    print("🚀 Starting FastAPI Server & Interactive Dashboard...")
    print("🌐 Dashboard URL: http://localhost:8000")
    print("📖 API Swagger Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server.")
    print("="*60 + "\n")

    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
