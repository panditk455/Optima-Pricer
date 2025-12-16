# OptimaPricer Flask Application

Complete Flask application for price optimization with integrated frontend.

## Features

- **Full-stack Flask application** - No separate frontend needed
- **Session-based authentication** - Secure user management
- **Product management** - Add, edit, delete products
- **Price scanning** - Automated competitor price scraping
- **AI-powered recommendations** - Intelligent pricing suggestions
- **Dashboard** - Overview of pricing metrics and trends

## Setup

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY (use a strong random string)
```

4. **Run the application:**
```bash
python run.py
```

The application will be available at `http://localhost:5001`

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models
│   ├── auth.py              # Authentication setup
│   ├── utils.py             # Utility functions
│   ├── templates/           # Jinja2 templates (frontend)
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   ├── optimization.html
│   │   ├── settings.html
│   │   └── auth/
│   │       ├── signin.html
│   │       └── register.html
│   ├── static/              # Static files (CSS, JS)
│   │   ├── css/
│   │   └── js/
│   ├── blueprints/          # API route blueprints
│   │   ├── main.py         # Frontend routes
│   │   ├── auth.py         # Authentication routes
│   │   ├── products.py     # Product management
│   │   ├── stores.py       # Store management
│   │   └── recommendations.py
│   └── services/            # Business logic
│       ├── scraper.py
│       └── price_optimizer.py
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Routes

### Frontend Routes
- `/` - Redirects to dashboard or signin
- `/dashboard` - Main dashboard
- `/products` - Product management
- `/optimization` - Price optimization recommendations
- `/settings` - Store and account settings
- `/auth/signin` - Sign in page
- `/auth/register` - Registration page

### API Routes
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user
- `GET /api/stores` - Get all stores
- `POST /api/stores` - Create a store
- `GET /api/products` - Get all products
- `POST /api/products` - Create a product
- `GET /api/products/<id>` - Get a product
- `PATCH /api/products/<id>` - Update a product
- `DELETE /api/products/<id>` - Delete a product
- `POST /api/products/<id>/scan` - Scan prices for a product
- `GET /api/recommendations` - Get all recommendations
- `POST /api/recommendations` - Create a recommendation
- `PATCH /api/recommendations/<id>` - Update a recommendation

## Database

The application uses SQLite by default. The database file will be created automatically on first run.

To use PostgreSQL or MySQL, update the `DATABASE_URL` in your `.env` file.

## Frontend

The frontend is built with:
- **Jinja2 templates** - Server-side rendering
- **Tailwind CSS** - Styling (via CDN)
- **Vanilla JavaScript** - No framework dependencies
- **Chart.js** - For data visualization

All frontend code is in `app/templates/` and `app/static/`.

## Authentication

The application uses Flask-Login for session-based authentication. Users must be logged in to access protected routes.

## Development

Run in debug mode:
```bash
python run.py
```

The app will automatically reload on code changes.

## Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 'app:create_app()'
```

## Notes

- All API endpoints require authentication (except register/login)
- CORS is configured for development (can be adjusted in `app/__init__.py`)
- The scraper uses rate limiting to avoid being blocked
- Price recommendations are generated using AI algorithms
