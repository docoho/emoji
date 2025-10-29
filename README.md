# Emoji Showcase Platform

A full-stack web application for sharing and curating emojis with community contributions. Users can browse emoji collections, submit new entries with metadata, and manage their submissions through an authenticated platform.

## Features

- 🔐 **User Authentication** - Secure registration and login with JWT tokens
- 📝 **Emoji Submissions** - Submit emojis with title, description, category, and keywords
- 🎨 **Interactive Gallery** - Browse curated emoji collections in a responsive grid
- 🗑️ **Submission Management** - Delete your own emoji entries
- 🔍 **Metadata Support** - Categorize and tag emojis with keywords for better organization
- 👤 **User Profiles** - Track submissions by user with display names

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLModel** - SQL database ORM with Pydantic integration
- **SQLite** - Lightweight database
- **JWT Authentication** - Secure token-based auth with python-jose
- **Bcrypt** - Password hashing
- **Pytest** - Comprehensive test suite

### Frontend
- **Vue 3** - Progressive JavaScript framework with Composition API
- **Vite** - Next-generation frontend build tool
- **Vue Router** - Client-side routing
- **Modern CSS** - Responsive design with custom styling

## Project Structure

```
emoji/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints and dependencies
│   │   ├── core/         # Configuration and security
│   │   ├── models/       # Database models (User, EmojiSubmission)
│   │   ├── schemas/      # Pydantic schemas
│   │   └── main.py       # FastAPI application entry point
│   ├── tests/            # Pytest test suite
│   └── pyproject.toml    # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── components/   # Reusable Vue components
    │   ├── views/        # Page components
    │   ├── composables/  # Vue composables (useAuth)
    │   ├── services/     # API client
    │   └── router/       # Vue Router configuration
    ├── package.json      # npm dependencies
    └── index.html        # Entry HTML
```

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload
# or
make backend

# Run tests
pytest
# or
make backend-test

# Lint code
ruff check app tests
# or
make lint
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
# or
make frontend

# Build for production
npm run build
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and receive JWT token
- `GET /api/auth/me` - Get current user profile

### Emojis
- `GET /api/emojis` - List all emoji submissions
- `POST /api/emojis` - Submit new emoji (authenticated)
- `DELETE /api/emojis/{id}` - Delete emoji (owner only)

## Configuration

Backend settings can be configured via environment variables or `.env` file:

```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./app.db
CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]
```

## Development

The project uses:
- **CORS** enabled for local development
- **Hot reload** on both frontend and backend
- **SQLite** database (automatically created on first run)
- **JWT tokens** stored in localStorage on frontend

## Testing

Backend includes comprehensive tests covering:
- Authentication flows
- Emoji CRUD operations
- Authorization checks
- Legacy data handling

Run with: `pytest` or `make backend-test`

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
