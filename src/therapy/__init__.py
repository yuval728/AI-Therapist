"""Enhanced therapy module with comprehensive flow management and monitoring."""

# Core therapy flow
from .graphs.therapy_flow import build_therapy_graph

# Flow handlers
from .flow_handlers import (
    InputHandler,
    ResponseHandler,
    ClassificationHandler,
    JournalHandler,
    SafetyHandler
)

# Services
from .services.therapy_service import (
    TherapyService,
    TherapyContext,
    get_therapy_service
)

# Memory management
from .memory.memory_manager import (
    MemoryManager,
    MemorySearchResult,
    MemoryStats,
    append_to_memory,
    get_memory,
    save_to_long_term_memory,
    search_long_term_memory,
    prune_messages
)

# Tools
from .tools.emotions_analyzer import emotion_tool
from .tools.crisis_detector import crisis_tool
from .tools.journal_tool import journal_tool

__all__ = [
    # Core flow
    "build_therapy_graph",
    
    # Handlers
    "InputHandler",
    "ResponseHandler", 
    "ClassificationHandler",
    "JournalHandler",
    "SafetyHandler",
    
    # Services
    "TherapyService",
    "TherapyContext",
    "get_therapy_service",
    
    # Memory management
    "MemoryManager",
    "MemorySearchResult",
    "MemoryStats",
    "append_to_memory",
    "get_memory",
    "save_to_long_term_memory",
    "search_long_term_memory",
    "prune_messages",
    
    # Tools
    "emotion_tool",
    "crisis_tool", 
    "journal_tool"
]
