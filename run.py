import os
from app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    
    print(f"==================================================")
    print(f"  API SENTINEL - Real-Time API Health Platform")
    print(f"  Running on: http://{host}:{port}")
    print(f"==================================================")
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)
