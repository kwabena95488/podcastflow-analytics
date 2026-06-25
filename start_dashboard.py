#!/usr/bin/env python3
"""
Start PodcastFlow Analytics Dashboard
Simple script to start BigQuery emulator and Streamlit dashboard
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def start_bigquery_emulator():
    """Start BigQuery emulator using gcloud CLI"""
    print("🚀 Starting BigQuery emulator...")
    
    try:
        # Start BigQuery emulator
        emulator_process = subprocess.Popen([
            'gcloud', 'beta', 'emulators', 'bigtable', 'start',
            '--host-port=localhost:9050'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("✅ BigQuery emulator started on localhost:9050")
        return emulator_process
    except Exception as e:
        print(f"❌ Failed to start BigQuery emulator: {e}")
        print("💡 Using fallback mock server...")
        return None

def start_mock_bigquery():
    """Start a simple mock BigQuery server"""
    print("🔧 Starting mock BigQuery server...")
    
    mock_server_code = '''
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class MockBigQueryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if '/queries' in self.path:
            # Mock BigQuery response
            response = {
                "kind": "bigquery#queryResponse",
                "jobComplete": True,
                "rows": [
                    {"f": [{"v": "8"}]},  # Sample data
                    {"f": [{"v": "324"}, {"v": "55.8"}, {"v": "45"}]},
                    {"f": [{"v": "50"}, {"v": "0.677"}]}
                ]
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Mock BigQuery Emulator Running')

def run_server():
    server = HTTPServer(('localhost', 9050), MockBigQueryHandler)
    server.serve_forever()

if __name__ == "__main__":
    print("Mock BigQuery server starting on localhost:9050...")
    run_server()
'''
    
    # Write mock server to file
    with open('mock_bigquery.py', 'w') as f:
        f.write(mock_server_code)
    
    try:
        mock_process = subprocess.Popen([
            sys.executable, 'mock_bigquery.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("✅ Mock BigQuery server started on localhost:9050")
        return mock_process
    except Exception as e:
        print(f"❌ Failed to start mock server: {e}")
        return None

def install_streamlit():
    """Install Streamlit if not available"""
    try:
        import streamlit
        print("✅ Streamlit is available")
        return True
    except ImportError:
        print("📦 Installing Streamlit...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'streamlit', 'plotly', 'requests'])
            print("✅ Streamlit installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install Streamlit: {e}")
            return False

def start_streamlit():
    """Start Streamlit dashboard"""
    print("🎯 Starting Streamlit dashboard...")
    
    # Ensure we're in the right directory
    dashboard_dir = Path(__file__).parent / 'dashboard'
    if not dashboard_dir.exists():
        print(f"❌ Dashboard directory not found: {dashboard_dir}")
        return None
    
    try:
        # Set environment variables for BigQuery emulator
        env = os.environ.copy()
        env['BIGQUERY_EMULATOR_HOST'] = 'localhost'
        env['BIGQUERY_EMULATOR_PORT'] = '9050'
        
        streamlit_process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port=8501',
            '--server.address=localhost',
            '--browser.gatherUsageStats=false'
        ], cwd=dashboard_dir, env=env)
        
        print("✅ Streamlit dashboard started on http://localhost:8501")
        return streamlit_process
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return None

def main():
    """Main function to start the complete dashboard"""
    print("🎧 PodcastFlow Analytics Dashboard Startup")
    print("=" * 50)
    
    processes = []
    
    try:
        # Check if ports are available
        if not check_port(9050):
            print("⚠️  Port 9050 is already in use")
        
        # Install Streamlit if needed
        if not install_streamlit():
            print("❌ Cannot proceed without Streamlit")
            return
        
        # Start BigQuery emulator (or mock)
        emulator_process = start_bigquery_emulator()
        if not emulator_process:
            emulator_process = start_mock_bigquery()
        
        if emulator_process:
            processes.append(emulator_process)
            time.sleep(2)  # Give emulator time to start
        
        # Start Streamlit dashboard
        streamlit_process = start_streamlit()
        if streamlit_process:
            processes.append(streamlit_process)
        
        if not processes:
            print("❌ Failed to start any services")
            return
        
        print("\n🎉 Dashboard is ready!")
        print("📊 Streamlit Dashboard: http://localhost:8501")
        print("🗄️  BigQuery Emulator: http://localhost:9050")
        print("\nPress Ctrl+C to stop all services...")
        
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if any process has died
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    print(f"⚠️  Process {i} has stopped")
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    
    finally:
        # Clean up processes
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Clean up temporary files
        if os.path.exists('mock_bigquery.py'):
            os.remove('mock_bigquery.py')
        
        print("✅ All services stopped")

if __name__ == "__main__":
    main() 