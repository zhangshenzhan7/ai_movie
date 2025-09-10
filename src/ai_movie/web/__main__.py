#!/usr/bin/env python3
"""
AI Movie Generator - Web Application Entry Point

This module allows the web application to be executed directly using:
    python -m ai_movie.web

It starts the Flask development server.
"""

import sys
from . import create_app
from ..core.logging_config import get_logger

logger = get_logger(__name__)

def main():
    """Main web application entry point"""
    try:
        # Create Flask application
        app = create_app()
        
        # Get configuration
        host = app.config.get('FLASK_HOST', '0.0.0.0')
        port = app.config.get('FLASK_PORT', 5002)
        debug = app.config.get('FLASK_DEBUG', False)
        
        logger.info(f"Starting AI Movie Generator Web Server")
        logger.info(f"Server will be available at: http://{host}:{port}")
        
        # Start the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start web application: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()