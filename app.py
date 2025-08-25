"""
Main entry point for WhatsApp Todo Bot
This file maintains compatibility with existing deployment configuration
"""

from src.app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)