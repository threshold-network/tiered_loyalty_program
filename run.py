import os
import asyncio
import logging
from src.app import create_app, main

async def run_main():
    await main()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    app = create_app()
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    
    # Run the main loop in the background
    asyncio.run(run_main())
    
    logger.info(f"Starting Flask app on port {port}")
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)