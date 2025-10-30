#!/usr/bin/env python3
"""
Simplified worker process for background tasks.
This runs separately from the web process.
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime

# Set process role in code (no env)
try:
    from src import app as app_module
    app_module.PROCESS_ROLE = 'worker'
except Exception:
    # Fallback for top-level app import path
    import app as app_module
    app_module.PROCESS_ROLE = 'worker'

# Create app after setting role
from src.app import create_app
app = create_app()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerProcess:
    def __init__(self):
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down worker...")
        self.running = False
    
    def start(self):
        """Start the worker process"""
        logger.info("Starting simplified worker process...")
        logger.info(f"Worker PID: {os.getpid()}")
        logger.info(f"PROCESS_TYPE: {os.getenv('PROCESS_TYPE')}")
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # TODO: Future scheduler/background task implementation will go here
        logger.info("Worker ready (scheduler not implemented yet)...")
        
        try:
            while self.running:
                time.sleep(30)  # Check every 30 seconds
                logger.info("Worker heartbeat")
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        logger.info("Worker process stopped")

if __name__ == "__main__":
    worker = WorkerProcess()
    worker.start()