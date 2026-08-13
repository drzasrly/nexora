import http.server
import socketserver
import webbrowser
import threading
import time
import os

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local data fetching and disable caching for active development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def open_browser():
    # Wait for the server to spin up, then open browser
    time.sleep(1.0)
    print(f"\n[LAUNCH] Opening browser at http://localhost:{PORT}/dashboard/ ...")
    webbrowser.open(f"http://localhost:{PORT}/dashboard/")

if __name__ == "__main__":
    # Set current working directory to script location to ensure correct paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Launch browser thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Launch HTTP Server
    print("=" * 60)
    print(f"HEAL-CITY DASHBOARD LOCAL SERVER")
    print(f"Root Directory: {script_dir}")
    print(f"Serving at: http://localhost:{PORT}/dashboard/")
    print("=" * 60)
    print("Press Ctrl+C to terminate the server.\n")
    
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server cleanly...")
            httpd.server_close()
