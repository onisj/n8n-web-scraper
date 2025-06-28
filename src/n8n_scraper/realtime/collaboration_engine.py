"""
Real-time collaboration engine for n8n-scraper.

This module provides WebSocket-based real-time collaboration features including:
- Live presence indicators
- Real-time comments and annotations
- Collaborative editing
- Live activity feeds
- Real-time notifications
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

try:
    import socketio
    import redis.asyncio as redis
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    socketio = None
    redis = None
    FastAPI = None
    WebSocket = None
    WebSocketDisconnect = None
    CORSMiddleware = None

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of real-time events."""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    USER_TYPING = "user_typing"
    COMMENT_ADD = "comment_add"
    COMMENT_UPDATE = "comment_update"
    COMMENT_DELETE = "comment_delete"
    ANNOTATION_ADD = "annotation_add"
    ANNOTATION_UPDATE = "annotation_update"
    ANNOTATION_DELETE = "annotation_delete"
    DOCUMENT_UPDATE = "document_update"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    NOTIFICATION = "notification"
    ACTIVITY_UPDATE = "activity_update"


@dataclass
class User:
    """User information for collaboration."""
    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    color: str = "#3B82F6"
    role: str = "viewer"
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.utcnow()


@dataclass
class Comment:
    """Comment data structure."""
    id: str
    user_id: str
    document_id: str
    content: str
    position: Dict[str, Any]  # Line number, character position, etc.
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved: bool = False
    replies: List['Comment'] = None
    
    def __post_init__(self):
        if self.replies is None:
            self.replies = []


@dataclass
class Annotation:
    """Annotation data structure."""
    id: str
    user_id: str
    document_id: str
    type: str  # highlight, note, bookmark, etc.
    content: str
    position: Dict[str, Any]
    style: Dict[str, Any]  # Color, background, etc.
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class Activity:
    """Activity feed item."""
    id: str
    user_id: str
    type: str
    description: str
    metadata: Dict[str, Any]
    timestamp: datetime
    document_id: Optional[str] = None


class CollaborationEngine:
    """Real-time collaboration engine."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.active_users: Dict[str, User] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.session_users: Dict[str, str] = {}  # session_id -> user_id
        self.document_users: Dict[str, Set[str]] = {}  # document_id -> user_ids
        self.comments: Dict[str, Comment] = {}
        self.annotations: Dict[str, Annotation] = {}
        self.activities: List[Activity] = []
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        
        # WebSocket connections
        self.connections: Dict[str, WebSocket] = {}
        
        # Socket.IO server (if available)
        self.sio: Optional[socketio.AsyncServer] = None
        if socketio:
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                logger=logger,
                engineio_logger=logger
            )
            self._setup_socketio_handlers()
    
    async def initialize(self):
        """Initialize the collaboration engine."""
        if redis:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis for real-time collaboration")
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_inactive_users())
        logger.info("Collaboration engine initialized")
    
    def _setup_socketio_handlers(self):
        """Setup Socket.IO event handlers."""
        if not self.sio:
            return
        
        @self.sio.event
        async def connect(sid, environ, auth):
            logger.info(f"Client connected: {sid}")
            
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client disconnected: {sid}")
            await self._handle_user_disconnect(sid)
        
        @self.sio.event
        async def join_document(sid, data):
            user_id = data.get('user_id')
            document_id = data.get('document_id')
            user_info = data.get('user_info', {})
            
            if user_id and document_id:
                await self._handle_user_join(sid, user_id, document_id, user_info)
        
        @self.sio.event
        async def leave_document(sid, data):
            user_id = data.get('user_id')
            document_id = data.get('document_id')
            
            if user_id and document_id:
                await self._handle_user_leave(sid, user_id, document_id)
        
        @self.sio.event
        async def add_comment(sid, data):
            await self._handle_add_comment(sid, data)
        
        @self.sio.event
        async def update_comment(sid, data):
            await self._handle_update_comment(sid, data)
        
        @self.sio.event
        async def delete_comment(sid, data):
            await self._handle_delete_comment(sid, data)
        
        @self.sio.event
        async def add_annotation(sid, data):
            await self._handle_add_annotation(sid, data)
        
        @self.sio.event
        async def cursor_move(sid, data):
            await self._handle_cursor_move(sid, data)
        
        @self.sio.event
        async def user_typing(sid, data):
            await self._handle_user_typing(sid, data)
    
    async def _handle_user_join(self, session_id: str, user_id: str, document_id: str, user_info: Dict):
        """Handle user joining a document."""
        # Create or update user
        user = User(
            id=user_id,
            name=user_info.get('name', f'User {user_id[:8]}'),
            email=user_info.get('email', ''),
            avatar_url=user_info.get('avatar_url'),
            color=user_info.get('color', '#3B82F6'),
            role=user_info.get('role', 'viewer'),
            last_seen=datetime.utcnow()
        )
        
        self.active_users[user_id] = user
        
        # Track sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        self.session_users[session_id] = user_id
        
        # Track document users
        if document_id not in self.document_users:
            self.document_users[document_id] = set()
        self.document_users[document_id].add(user_id)
        
        # Join Socket.IO room
        if self.sio:
            await self.sio.enter_room(session_id, f"document_{document_id}")
        
        # Broadcast user join event
        await self._broadcast_event(
            document_id,
            EventType.USER_JOIN,
            {
                'user': asdict(user),
                'document_id': document_id,
                'timestamp': datetime.utcnow().isoformat()
            },
            exclude_session=session_id
        )
        
        # Send current document state to new user
        await self._send_document_state(session_id, document_id)
        
        # Log activity
        await self._log_activity(
            user_id,
            "user_join",
            f"{user.name} joined the document",
            {'document_id': document_id},
            document_id
        )
    
    async def _handle_user_leave(self, session_id: str, user_id: str, document_id: str):
        """Handle user leaving a document."""
        # Remove from document users
        if document_id in self.document_users:
            self.document_users[document_id].discard(user_id)
            if not self.document_users[document_id]:
                del self.document_users[document_id]
        
        # Remove session tracking
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
                # Remove user if no active sessions
                if user_id in self.active_users:
                    user = self.active_users[user_id]
                    del self.active_users[user_id]
                    
                    # Broadcast user leave event
                    await self._broadcast_event(
                        document_id,
                        EventType.USER_LEAVE,
                        {
                            'user_id': user_id,
                            'user_name': user.name,
                            'document_id': document_id,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    )
        
        if session_id in self.session_users:
            del self.session_users[session_id]
        
        # Leave Socket.IO room
        if self.sio:
            await self.sio.leave_room(session_id, f"document_{document_id}")
    
    async def _handle_user_disconnect(self, session_id: str):
        """Handle user disconnection."""
        if session_id in self.session_users:
            user_id = self.session_users[session_id]
            
            # Find all documents this user was in
            documents_to_leave = []
            for doc_id, users in self.document_users.items():
                if user_id in users:
                    documents_to_leave.append(doc_id)
            
            # Leave all documents
            for doc_id in documents_to_leave:
                await self._handle_user_leave(session_id, user_id, doc_id)
    
    async def _handle_add_comment(self, session_id: str, data: Dict):
        """Handle adding a comment."""
        user_id = self.session_users.get(session_id)
        if not user_id:
            return
        
        comment = Comment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_id=data['document_id'],
            content=data['content'],
            position=data['position'],
            created_at=datetime.utcnow()
        )
        
        self.comments[comment.id] = comment
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.hset(
                f"comments:{comment.document_id}",
                comment.id,
                json.dumps(asdict(comment), default=str)
            )
        
        # Broadcast comment
        await self._broadcast_event(
            comment.document_id,
            EventType.COMMENT_ADD,
            {
                'comment': asdict(comment),
                'user': asdict(self.active_users[user_id]),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        # Log activity
        await self._log_activity(
            user_id,
            "comment_add",
            f"Added a comment: {comment.content[:50]}...",
            {'comment_id': comment.id, 'position': comment.position},
            comment.document_id
        )
    
    async def _handle_add_annotation(self, session_id: str, data: Dict):
        """Handle adding an annotation."""
        user_id = self.session_users.get(session_id)
        if not user_id:
            return
        
        annotation = Annotation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            document_id=data['document_id'],
            type=data['type'],
            content=data['content'],
            position=data['position'],
            style=data.get('style', {}),
            created_at=datetime.utcnow()
        )
        
        self.annotations[annotation.id] = annotation
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.hset(
                f"annotations:{annotation.document_id}",
                annotation.id,
                json.dumps(asdict(annotation), default=str)
            )
        
        # Broadcast annotation
        await self._broadcast_event(
            annotation.document_id,
            EventType.ANNOTATION_ADD,
            {
                'annotation': asdict(annotation),
                'user': asdict(self.active_users[user_id]),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def _handle_cursor_move(self, session_id: str, data: Dict):
        """Handle cursor movement."""
        user_id = self.session_users.get(session_id)
        if not user_id:
            return
        
        # Broadcast cursor position
        await self._broadcast_event(
            data['document_id'],
            EventType.CURSOR_MOVE,
            {
                'user_id': user_id,
                'position': data['position'],
                'timestamp': datetime.utcnow().isoformat()
            },
            exclude_session=session_id
        )
    
    async def _handle_user_typing(self, session_id: str, data: Dict):
        """Handle user typing indicator."""
        user_id = self.session_users.get(session_id)
        if not user_id:
            return
        
        # Broadcast typing indicator
        await self._broadcast_event(
            data['document_id'],
            EventType.USER_TYPING,
            {
                'user_id': user_id,
                'is_typing': data['is_typing'],
                'position': data.get('position'),
                'timestamp': datetime.utcnow().isoformat()
            },
            exclude_session=session_id
        )
    
    async def _broadcast_event(self, document_id: str, event_type: EventType, data: Dict, exclude_session: str = None):
        """Broadcast an event to all users in a document."""
        if self.sio:
            room = f"document_{document_id}"
            await self.sio.emit(
                event_type.value,
                data,
                room=room,
                skip_sid=exclude_session
            )
        
        # Store in Redis for persistence
        if self.redis_client:
            event_data = {
                'type': event_type.value,
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            }
            await self.redis_client.lpush(
                f"events:{document_id}",
                json.dumps(event_data, default=str)
            )
            # Keep only last 1000 events
            await self.redis_client.ltrim(f"events:{document_id}", 0, 999)
    
    async def _send_document_state(self, session_id: str, document_id: str):
        """Send current document state to a user."""
        if not self.sio:
            return
        
        # Get active users in document
        active_users = []
        if document_id in self.document_users:
            for user_id in self.document_users[document_id]:
                if user_id in self.active_users:
                    active_users.append(asdict(self.active_users[user_id]))
        
        # Get comments for document
        document_comments = [
            asdict(comment) for comment in self.comments.values()
            if comment.document_id == document_id
        ]
        
        # Get annotations for document
        document_annotations = [
            asdict(annotation) for annotation in self.annotations.values()
            if annotation.document_id == document_id
        ]
        
        # Send state
        await self.sio.emit(
            'document_state',
            {
                'document_id': document_id,
                'active_users': active_users,
                'comments': document_comments,
                'annotations': document_annotations,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=session_id
        )
    
    async def _log_activity(self, user_id: str, activity_type: str, description: str, metadata: Dict, document_id: str = None):
        """Log an activity."""
        activity = Activity(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=activity_type,
            description=description,
            metadata=metadata,
            timestamp=datetime.utcnow(),
            document_id=document_id
        )
        
        self.activities.append(activity)
        
        # Keep only last 1000 activities
        if len(self.activities) > 1000:
            self.activities = self.activities[-1000:]
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.lpush(
                "activities",
                json.dumps(asdict(activity), default=str)
            )
            await self.redis_client.ltrim("activities", 0, 999)
        
        # Broadcast activity update
        if document_id:
            await self._broadcast_event(
                document_id,
                EventType.ACTIVITY_UPDATE,
                {
                    'activity': asdict(activity),
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    async def _cleanup_inactive_users(self):
        """Cleanup inactive users periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)
                inactive_users = [
                    user_id for user_id, user in self.active_users.items()
                    if user.last_seen < cutoff_time
                ]
                
                for user_id in inactive_users:
                    # Remove from all documents
                    documents_to_clean = []
                    for doc_id, users in self.document_users.items():
                        if user_id in users:
                            documents_to_clean.append(doc_id)
                    
                    for doc_id in documents_to_clean:
                        self.document_users[doc_id].discard(user_id)
                        if not self.document_users[doc_id]:
                            del self.document_users[doc_id]
                    
                    # Remove user
                    if user_id in self.active_users:
                        del self.active_users[user_id]
                    
                    # Clean up sessions
                    if user_id in self.user_sessions:
                        del self.user_sessions[user_id]
                
                logger.info(f"Cleaned up {len(inactive_users)} inactive users")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_fastapi_app(self) -> Optional[FastAPI]:
        """Get FastAPI app with Socket.IO integration."""
        if not FastAPI or not self.sio:
            return None
        
        app = FastAPI(title="n8n-scraper Real-time Collaboration")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount Socket.IO
        import socketio
        sio_app = socketio.ASGIApp(self.sio, app)
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        @app.get("/api/v1/documents/{document_id}/users")
        async def get_document_users(document_id: str):
            """Get active users in a document."""
            users = []
            if document_id in self.document_users:
                for user_id in self.document_users[document_id]:
                    if user_id in self.active_users:
                        users.append(asdict(self.active_users[user_id]))
            return {"users": users}
        
        @app.get("/api/v1/documents/{document_id}/comments")
        async def get_document_comments(document_id: str):
            """Get comments for a document."""
            comments = [
                asdict(comment) for comment in self.comments.values()
                if comment.document_id == document_id
            ]
            return {"comments": comments}
        
        @app.get("/api/v1/activities")
        async def get_activities(limit: int = 50):
            """Get recent activities."""
            recent_activities = self.activities[-limit:] if self.activities else []
            return {
                "activities": [asdict(activity) for activity in reversed(recent_activities)]
            }
        
        return sio_app


# Global collaboration engine instance
collaboration_engine: Optional[CollaborationEngine] = None


def get_collaboration_engine() -> Optional[CollaborationEngine]:
    """Get the global collaboration engine instance."""
    global collaboration_engine
    if collaboration_engine is None and socketio and redis:
        collaboration_engine = CollaborationEngine()
    return collaboration_engine


async def initialize_collaboration():
    """Initialize the collaboration engine."""
    engine = get_collaboration_engine()
    if engine:
        await engine.initialize()
        logger.info("Real-time collaboration initialized")
    else:
        logger.warning("Real-time collaboration not available (missing dependencies)")


if __name__ == "__main__":
    import uvicorn
    
    async def main():
        engine = get_collaboration_engine()
        if engine:
            await engine.initialize()
            app = engine.get_fastapi_app()
            if app:
                config = uvicorn.Config(
                    app,
                    host="0.0.0.0",
                    port=8001,
                    log_level="info"
                )
                server = uvicorn.Server(config)
                await server.serve()
            else:
                logger.error("Failed to create FastAPI app")
        else:
            logger.error("Failed to initialize collaboration engine")
    
    asyncio.run(main())