import subprocess
import sys
import time
import os
import signal

def run_servers():
    print("Starting servers...")
    
    # Store process objects
    processes = []
    
    try:
        # Start API Details on 8000 (ImageToItemdetails.py)
        p0 = subprocess.Popen([sys.executable, "ImageToItemdetails.py"])
        processes.append(p0)
        print("API Details starting on port 8000...")

        # Start Item Master on 8002
        p1 = subprocess.Popen([sys.executable, "ItemMaster.py"])
        processes.append(p1)
        print("Item Master starting on port 8002...")
        
        # Start Invoice Creation on 8003
        p2 = subprocess.Popen([sys.executable, "InvoiceCreation.py"])
        processes.append(p2)
        print("Invoice Creation starting on port 8003...")
        
        # Start Home Page on 8004
        p3 = subprocess.Popen([sys.executable, "HomePage.py"])
        processes.append(p3)
        print("Home Page starting on port 8004...")
        
        print("\nAll servers started! Open http://localhost:8004 to view the Home Page.")
        print("Press Ctrl+C to stop all servers.\n")
        
        # Wait for all processes (this runs indefinitely until interrupted)
        for p in processes:
            p.wait()
            
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        for p in processes:
            p.terminate()
        sys.exit(0)

if __name__ == "__main__":
    run_servers()