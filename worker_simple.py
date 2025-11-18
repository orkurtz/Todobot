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
from src.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerProcess:
    def __init__(self):
        self.running = True
        # Explicitly create app with worker role
        self.app = create_app(process_role='worker')
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down worker...")
        self.running = False
    
    def start(self):
        """Start the worker process"""
        logger.info("Starting simplified worker process...")
        logger.info(f"Worker PID: {os.getpid()}")
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info("Worker ready (scheduler initialized via create_app)...")
        
        # We need to keep the main thread alive to allow the background scheduler threads to run
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
