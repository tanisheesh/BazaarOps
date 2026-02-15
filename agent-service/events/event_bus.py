from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Callable

@dataclass
class Event:
    """An event that triggers agents"""
    type: str
    store_id: str
    payload: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventBus:
    """Manages events and notifies agents"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        """Agent subscribes to an event"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        print(f"📡 Subscribed to: {event_type}")
    
    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        print(f"🔔 Event: {event.type} for store {event.store_id}")
        
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    await handler(event)
                except Exception as e:
                    print(f"❌ Handler error: {e}")

# Global instance
event_bus = EventBus()