"""
Log broadcaster for real-time WebSocket log streaming.
"""
import asyncio
import json
import logging
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Log level enum."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogMessage:
    """Structured log message for WebSocket clients."""
    level: LogLevel
    message: str
    scraper: str | None = None
    timestamp: str | None = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self))


class LogBroadcaster:
    """
    Singleton broadcaster for streaming logs to WebSocket clients.
    
    Uses asyncio queues to distribute messages to all connected clients.
    """
    
    _instance: "LogBroadcaster | None" = None
    
    def __new__(cls) -> "LogBroadcaster":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        logger.info("LogBroadcaster initialized")
    
    async def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to log messages.
        
        Returns:
            Queue that will receive log messages
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(queue)
        logger.debug(f"New subscriber added. Total: {len(self._subscribers)}")
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from log messages.
        
        Args:
            queue: Queue to remove
        """
        async with self._lock:
            self._subscribers.discard(queue)
        logger.debug(f"Subscriber removed. Total: {len(self._subscribers)}")
    
    async def broadcast(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        scraper: str | None = None,
    ) -> None:
        """
        Broadcast a log message to all subscribers.
        
        Args:
            message: Log message text
            level: Log level (info, success, warning, error)
            scraper: Optional scraper name
        """
        log_msg = LogMessage(level=level, message=message, scraper=scraper)
        json_msg = log_msg.to_json()
        
        async with self._lock:
            dead_queues = []
            for queue in self._subscribers:
                try:
                    queue.put_nowait(json_msg)
                except asyncio.QueueFull:
                    # Queue is full, client is too slow
                    dead_queues.append(queue)
            
            # Remove dead/slow queues
            for queue in dead_queues:
                self._subscribers.discard(queue)
    
    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self._subscribers)


# Global broadcaster instance
broadcaster = LogBroadcaster()
