"""Mock websocket manager for claudable_helper.

This module provides a mock implementation of the websocket manager
that was originally imported from app.core.websocket.manager.
"""
from typing import Any, Dict, List, Optional
import asyncio
import json


class MockWebSocketManager:
    """Mock WebSocket manager for handling real-time communication."""
    
    def __init__(self):
        self.connections: Dict[str, List[Any]] = {}
        self.active = False
    
    async def connect(self, websocket: Any, client_id: str) -> None:
        """Mock connect a WebSocket client."""
        if client_id not in self.connections:
            self.connections[client_id] = []
        self.connections[client_id].append(websocket)
        self.active = True
    
    async def disconnect(self, websocket: Any, client_id: str) -> None:
        """Mock disconnect a WebSocket client."""
        if client_id in self.connections:
            try:
                self.connections[client_id].remove(websocket)
                if not self.connections[client_id]:
                    del self.connections[client_id]
            except ValueError:
                pass  # WebSocket not in list
        
        if not self.connections:
            self.active = False
    
    async def send_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Mock send message to a specific client."""
        if client_id not in self.connections:
            return
        
        message_str = json.dumps(message)
        for websocket in self.connections[client_id][:]:  # Copy list to avoid modification during iteration
            try:
                # In a real implementation, this would be:
                # await websocket.send_text(message_str)
                # For mock, we'll just log it
                print(f"[WebSocket] Sending to {client_id}: {message_str}")
            except Exception as e:
                print(f"[WebSocket] Error sending to {client_id}: {e}")
                # Remove broken connection
                try:
                    self.connections[client_id].remove(websocket)
                except ValueError:
                    pass
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Mock broadcast message to all connected clients."""
        message_str = json.dumps(message)
        for client_id in list(self.connections.keys()):
            await self.send_message(client_id, message)
    
    def is_active(self) -> bool:
        """Check if there are active connections."""
        return self.active and bool(self.connections)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(websockets) for websockets in self.connections.values())
    
    def get_client_ids(self) -> List[str]:
        """Get list of connected client IDs."""
        return list(self.connections.keys())


# Create singleton instance
manager = MockWebSocketManager()