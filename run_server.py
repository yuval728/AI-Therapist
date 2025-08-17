"""Development server runner for AI Therapist API."""
import uvicorn
import sys
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config import get_settings

def main():
    """Run the development server."""
    settings = get_settings()
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.is_development,
        log_level=settings.logging.level.lower(),
        access_log=True,
        use_colors=True,
        loop="asyncio"
    )

if __name__ == "__main__":
    main()
