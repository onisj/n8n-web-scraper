# Implementation Guide: Web Modernization

This guide provides step-by-step instructions and code examples to implement the web modernization plan.

## Quick Start Commands

### 1. Setup Frontend (Next.js)

```bash
# Navigate to project root
cd /Users/user/Projects/n8n-projects/n8n-web-scrapper

# Create Next.js frontend
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
cd frontend

# Install additional dependencies
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install zustand
npm install socket.io-client
npm install recharts
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select
npm install react-hook-form @hookform/resolvers zod
npm install lucide-react
npm install class-variance-authority clsx tailwind-merge
npm install @next/bundle-analyzer

# Development dependencies
npm install -D @types/node @types/react @types/react-dom
npm install -D jest @testing-library/react @testing-library/jest-dom
```

### 2. Backend Enhancement

```bash
# Add new dependencies to requirements.txt
echo "prometheus-client==0.19.0" >> requirements.txt
echo "websockets==12.0" >> requirements.txt
echo "python-socketio==5.10.0" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt

# Install new dependencies
pip install -r requirements.txt
```

### 3. Setup Monitoring

```bash
# Create monitoring directory structure
mkdir -p monitoring/{prometheus,grafana/{dashboards,provisioning}}

# Create Docker Compose for monitoring
touch monitoring/docker-compose.monitoring.yml
```

## Code Examples

### Frontend Components

#### 1. Main Layout Component

```typescript
// frontend/src/components/layout/main-layout.tsx
import { ReactNode } from 'react'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { ThemeProvider } from './theme-provider'

interface MainLayoutProps {
  children: ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <ThemeProvider>
      <div className="flex h-screen bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-auto p-6">
            {children}
          </main>
        </div>
      </div>
    </ThemeProvider>
  )
}
```

#### 2. AI Chat Component

```typescript
// frontend/src/components/chat/chat-interface.tsx
import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send, Bot, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const sendMessage = useMutation({
    mutationFn: async (message: string) => {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      })
      return response.json()
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: data.response,
        role: 'assistant',
        timestamp: new Date()
      }])
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    sendMessage.mutate(input)
    setInput('')
  }

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex items-start gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <Bot className="w-8 h-8 rounded-full bg-primary text-primary-foreground p-1" />
              )}
              <div
                className={`max-w-[70%] rounded-lg p-3 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <span className="text-xs opacity-70">
                  {message.timestamp.toLocaleTimeString()}
                </span>
              </div>
              {message.role === 'user' && (
                <User className="w-8 h-8 rounded-full bg-secondary text-secondary-foreground p-1" />
              )}
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about n8n..."
            disabled={sendMessage.isPending}
          />
          <Button type="submit" disabled={sendMessage.isPending}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}
```

#### 3. Knowledge Browser Component

```typescript
// frontend/src/components/knowledge/knowledge-browser.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, BookOpen } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface KnowledgeItem {
  id: string
  title: string
  content: string
  url: string
  category: string
  lastUpdated: string
}

export function KnowledgeBrowser() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')

  const { data: knowledge, isLoading } = useQuery({
    queryKey: ['knowledge', searchQuery, selectedCategory],
    queryFn: async () => {
      const params = new URLSearchParams({
        q: searchQuery,
        category: selectedCategory
      })
      const response = await fetch(`/api/knowledge/search?${params}`)
      return response.json()
    }
  })

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search knowledge base..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline">
          <Filter className="w-4 h-4 mr-2" />
          Filter
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-3 bg-muted rounded" />
                  <div className="h-3 bg-muted rounded w-5/6" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {knowledge?.items?.map((item: KnowledgeItem) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BookOpen className="w-4 h-4" />
                  {item.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {item.content}
                </p>
                <div className="mt-2 flex justify-between items-center text-xs text-muted-foreground">
                  <span>{item.category}</span>
                  <span>{new Date(item.lastUpdated).toLocaleDateString()}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Backend Enhancements

#### 1. Prometheus Metrics

```python
# src/n8n_scraper/api/middleware/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
import time

# Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

active_users = Gauge('active_users', 'Number of active users')
ai_tokens_used = Counter('ai_tokens_used_total', 'Total AI tokens consumed')
knowledge_base_size = Gauge('knowledge_base_documents', 'Number of documents in knowledge base')

class PrometheusMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.time()
        
        # Process request
        response = await self.app(scope, receive, send)
        
        # Record metrics
        duration = time.time() - start_time
        method = request.method
        endpoint = request.url.path
        status_code = getattr(response, 'status_code', 200)
        
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        api_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response

def get_metrics():
    """Return Prometheus metrics"""
    return Response(generate_latest(), media_type="text/plain")
```

#### 2. WebSocket Support

```python
# src/n8n_scraper/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: str = None):
        self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, user_id: str = None):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data["type"] == "chat":
                # Process AI chat message
                response = await process_ai_message(message_data["content"])
                await manager.send_personal_message(
                    json.dumps({"type": "chat_response", "content": response}),
                    user_id
                )
            elif message_data["type"] == "system_status":
                # Send system status updates
                status = await get_system_status()
                await manager.send_personal_message(
                    json.dumps({"type": "status_update", "data": status}),
                    user_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
```

### Monitoring Configuration

#### 1. Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'n8n-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'n8n-frontend'
    static_configs:
      - targets: ['frontend:3000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'discord-bot'
    static_configs:
      - targets: ['discord-bot:3001']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### 2. Grafana Dashboard

```json
{
  "dashboard": {
    "title": "n8n AI Knowledge System",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Users",
        "type": "singlestat",
        "targets": [
          {
            "expr": "active_users"
          }
        ]
      },
      {
        "title": "AI Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ai_tokens_used_total[1h])",
            "legendFormat": "Tokens per hour"
          }
        ]
      }
    ]
  }
}
```

### Discord Bot Implementation

#### 1. Discord Bot Setup

```javascript
// discord-bot/src/index.js
const { Client, GatewayIntentBits, Collection } = require('discord.js');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v9');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.commands = new Collection();

// Load commands
const commandsPath = path.join(__dirname, 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

for (const file of commandFiles) {
  const filePath = path.join(commandsPath, file);
  const command = require(filePath);
  client.commands.set(command.data.name, command);
}

// Handle interactions
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const command = client.commands.get(interaction.commandName);
  if (!command) return;

  try {
    await command.execute(interaction);
  } catch (error) {
    console.error(error);
    await interaction.reply({
      content: 'There was an error while executing this command!',
      ephemeral: true
    });
  }
});

client.once('ready', () => {
  console.log(`Ready! Logged in as ${client.user.tag}`);
});

client.login(process.env.DISCORD_TOKEN);
```

#### 2. Ask Command

```javascript
// discord-bot/src/commands/ask.js
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const axios = require('axios');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('ask')
    .setDescription('Ask the n8n AI assistant a question')
    .addStringOption(option =>
      option.setName('question')
        .setDescription('Your question about n8n')
        .setRequired(true)
    ),
  
  async execute(interaction) {
    await interaction.deferReply();
    
    try {
      const question = interaction.options.getString('question');
      
      const response = await axios.post(`${process.env.API_BASE_URL}/api/ai/chat`, {
        message: question,
        user_id: interaction.user.id,
        platform: 'discord'
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.API_KEY}`
        }
      });
      
      const aiResponse = response.data;
      
      const embed = new EmbedBuilder()
        .setColor(0x0099FF)
        .setTitle('n8n AI Assistant')
        .setDescription(aiResponse.message)
        .addFields(
          { name: 'Question', value: question, inline: false }
        )
        .setTimestamp()
        .setFooter({ text: 'Powered by n8n AI Knowledge System' });
      
      await interaction.editReply({ embeds: [embed] });
      
    } catch (error) {
      console.error('Error calling AI API:', error);
      await interaction.editReply({
        content: 'Sorry, I encountered an error while processing your question. Please try again later.'
      });
    }
  }
};
```

### Chrome Extension

#### 1. Manifest

```json
{
  "manifest_version": 3,
  "name": "n8n AI Assistant",
  "version": "1.0.0",
  "description": "AI-powered n8n documentation and workflow assistant",
  "permissions": [
    "activeTab",
    "storage",
    "scripting"
  ],
  "host_permissions": [
    "https://docs.n8n.io/*",
    "https://n8n.io/*"
  ],
  "action": {
    "default_popup": "popup/index.html",
    "default_title": "n8n AI Assistant"
  },
  "content_scripts": [{
    "matches": ["https://docs.n8n.io/*", "https://n8n.io/*"],
    "js": ["content/content.js"],
    "css": ["content/content.css"]
  }],
  "background": {
    "service_worker": "background/background.js"
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

#### 2. Popup Interface

```html
<!-- chrome-extension/popup/index.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      width: 350px;
      height: 500px;
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .chat-container {
      height: 400px;
      border: 1px solid #e1e5e9;
      border-radius: 8px;
      overflow-y: auto;
      padding: 12px;
      margin-bottom: 12px;
    }
    .message {
      margin-bottom: 12px;
      padding: 8px 12px;
      border-radius: 12px;
      max-width: 80%;
    }
    .user-message {
      background: #007bff;
      color: white;
      margin-left: auto;
    }
    .ai-message {
      background: #f8f9fa;
      color: #333;
    }
    .input-container {
      display: flex;
      gap: 8px;
    }
    input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid #e1e5e9;
      border-radius: 6px;
      outline: none;
    }
    button {
      padding: 8px 16px;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    button:hover {
      background: #0056b3;
    }
    button:disabled {
      background: #6c757d;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <div class="chat-container" id="chatContainer">
    <div class="message ai-message">
      Hi! I'm your n8n AI assistant. Ask me anything about n8n workflows, nodes, or documentation.
    </div>
  </div>
  
  <div class="input-container">
    <input type="text" id="messageInput" placeholder="Ask about n8n..." />
    <button id="sendButton">Send</button>
  </div>
  
  <script src="popup.js"></script>
</body>
</html>
```

#### 3. Popup JavaScript

```javascript
// chrome-extension/popup/popup.js
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');

const API_BASE_URL = 'http://localhost:8000'; // Configure this

function addMessage(content, isUser = false) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
  messageDiv.textContent = content;
  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;
  
  addMessage(message, true);
  messageInput.value = '';
  sendButton.disabled = true;
  
  try {
    // Get current tab context
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        context: {
          url: tab.url,
          title: tab.title
        },
        platform: 'chrome_extension'
      })
    });
    
    const data = await response.json();
    addMessage(data.message);
    
  } catch (error) {
    console.error('Error:', error);
    addMessage('Sorry, I encountered an error. Please try again.');
  } finally {
    sendButton.disabled = false;
  }
}

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

// Load chat history
chrome.storage.local.get(['chatHistory'], (result) => {
  if (result.chatHistory) {
    result.chatHistory.forEach(msg => {
      addMessage(msg.content, msg.isUser);
    });
  }
});

// Save chat history
function saveChatHistory() {
  const messages = Array.from(chatContainer.children).map(msg => ({
    content: msg.textContent,
    isUser: msg.classList.contains('user-message')
  }));
  chrome.storage.local.set({ chatHistory: messages });
}

// Save history on message add
const observer = new MutationObserver(saveChatHistory);
observer.observe(chatContainer, { childList: true });
```

## Docker Configuration

### Updated Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Backend (FastAPI)
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/n8n_knowledge
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  # Frontend (Next.js)
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    depends_on:
      - backend

  # Discord Bot
  discord-bot:
    build: ./discord-bot
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - API_BASE_URL=http://backend:8000
      - API_KEY=${API_KEY}
    depends_on:
      - backend

  # Database
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=n8n_knowledge
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  grafana_data:
```

## Deployment Commands

```bash
# Build and start all services
docker-compose up -d

# Build only specific services
docker-compose up -d backend frontend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Scale services
docker-compose up -d --scale backend=2

# Update and restart
docker-compose pull
docker-compose up -d --force-recreate
```

## Testing Commands

```bash
# Frontend tests
cd frontend
npm test
npm run test:e2e

# Backend tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Load testing
ab -n 1000 -c 10 http://localhost:8000/api/health
```

This implementation guide provides all the necessary code and configuration files to execute the web modernization plan. Each component is designed to work together while maintaining modularity for easier development and deployment.