# AI Therapist Application

A comprehensive AI-powered therapy application with real-time chat, session management, and advanced safety features.

## Project Structure

```
├── app/                    # React frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/         # Application pages
│   │   └── api.ts         # API client
│   └── package.json
├── src/                   # Python backend
│   ├── api/              # FastAPI routes and middleware
│   │   ├── routes/       # API endpoints
│   │   ├── websocket_routes/ # WebSocket handlers
│   │   └── middleware.py # Security and CORS middleware
│   ├── auth/             # Authentication services
│   ├── config/           # Configuration management
│   ├── core/             # Core utilities and guardrails
│   │   └── guardrails/   # Input/output moderation
│   ├── database/         # Supabase client and operations
│   ├── models/           # Pydantic models and schemas
│   ├── services/         # Business logic layer
│   ├── therapy/          # Therapy-specific components
│   │   ├── graphs/       # LangGraph therapy flow
│   │   ├── memory/       # Memory management
│   │   ├── services/     # Therapy services
│   │   └── tools.py      # Consolidated therapy tools
│   └── utils/            # Utility functions
├── tests/                # Integration tests
├── supabase/            # Database migrations
├── scripts/             # Setup and utility scripts
└── pyproject.toml       # Python dependencies
```

## Key Features

- **Real-time Chat**: WebSocket-based therapy conversations
- **Session Management**: Complete therapy session lifecycle
- **Safety Features**: Crisis detection, input moderation, PII protection
- **Memory System**: Short-term and long-term memory with vector search
- **Authentication**: Supabase-based user management
- **Monitoring**: Comprehensive logging and error handling

## Quick Start

1. **Install Dependencies**:
   ```bash
   # Backend
   pip install -r requirements.txt
   
   # Frontend
   cd app && npm install
   ```

2. **Setup Environment**:
   ```bash
   cp .env.example .env
   # Configure your environment variables
   ```

3. **Run the Application**:
   ```bash
   # Backend
   python run_server.py
   
   # Frontend (in separate terminal)
   cd app && npm run dev
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# LLM Configuration
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## API Endpoints

- **Authentication**: `/api/auth/` - User signup, signin, OAuth
- **Users**: `/api/users/` - Profile management, preferences
- **Sessions**: `/api/sessions/` - Therapy session CRUD operations
- **Health**: `/api/health/` - System health checks
- **WebSocket**: `/ws/chat/{user_id}` - Real-time therapy chat

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

## Architecture

The application follows a clean architecture pattern:

- **API Layer**: FastAPI routes with middleware
- **Service Layer**: Business logic and validation
- **Data Layer**: Supabase integration and models
- **Therapy Engine**: LangGraph-based conversation flow
- **Safety Systems**: Multi-layered content moderation

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation as needed
4. Ensure all safety checks pass

## License

This project is licensed under the MIT License.