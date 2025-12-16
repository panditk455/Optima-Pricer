# OptimaPricer

AI-Powered Pricing Optimization Platform - Flask Application

## Quick Start

### 1. Navigate to backend directory
```bash
cd backend
```

### 2. Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables (optional)
Create a `.env` file in the `backend` directory:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///optima_pricer.db
```

### 5. Run the application
```bash
python run.py
```

The application will be available at `http://localhost:5001`

## Features

- Product Management
- Price Scanning (Google Shopping, Amazon, eBay, Etsy)
- Price Optimization Recommendations
- Dashboard with Real Metrics
- Store Management

## Requirements

- Python 3.8+
- pip
