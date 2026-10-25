import uvicorn
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🚀 Starting TGM Reporting Studio Agency Portal")
    print("🎯 Pipeline: Meta | Google | LinkedIn | TikTok | Snapchat")
    print("📊 Destination: Google BigQuery & Looker Studio")
    print("🌐 Dashboard URL: http://localhost:8000")
    print("=" * 65 + "\n")
    
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
