# Cholera Environmental Surveillance System

An integrated surveillance system for monitoring cholera risk in Cross River State, Nigeria. This application combines satellite environmental data (flooding, rainfall) with epidemiological case data to calculate and visualize cholera outbreak risk at the LGA (Local Government Area) level.

## Features

- **Interactive Risk Map**: Choropleth map showing all 18 LGAs color-coded by risk level
- **Real-time Risk Scoring**: Algorithm combining flood indicators, rainfall, case counts, and vulnerability factors
- **Time-series Analytics**: Charts showing cases, deaths, rainfall, and risk trends over time
- **Data Upload**: CSV/Excel file upload for case and environmental data
- **Satellite Integration**: Google Earth Engine and NASA GPM integration for environmental data
- **LGA Search**: Quick search and selection of LGAs

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, Leaflet, Recharts |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, GeoAlchemy2 |
| Database | PostgreSQL with PostGIS |
| Satellite APIs | Google Earth Engine, NASA GPM, OpenWeatherMap |

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL 14+ with PostGIS extension
- (Optional) Google Earth Engine service account
- (Optional) NASA Earthdata account
- (Optional) OpenWeatherMap API key

## Quick Start

### 1. Clone and Setup

```bash
cd flooding-cholera
```

### 2. Database Setup

Install PostgreSQL and PostGIS, then create the database:

```bash
# macOS (using Homebrew)
brew install postgresql postgis

# Start PostgreSQL
brew services start postgresql

# Create database
createdb cholera_surveillance

# Enable PostGIS extension
psql cholera_surveillance -c "CREATE EXTENSION postgis;"
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Seed the database with sample data
python -m app.seed_database

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5173

## Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cholera_surveillance

# Google Earth Engine (optional)
GEE_SERVICE_ACCOUNT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GEE_PRIVATE_KEY_PATH=./gee-private-key.json

# NASA Earthdata (optional)
NASA_EARTHDATA_USERNAME=your-username
NASA_EARTHDATA_PASSWORD=your-password

# OpenWeatherMap (optional)
OPENWEATHERMAP_API_KEY=your-api-key

# App settings
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Satellite API Credentials

#### Google Earth Engine
1. Create a GCP project: https://console.cloud.google.com/
2. Enable Earth Engine API
3. Create a service account with Earth Engine access
4. Download the JSON key and place it in the backend directory
5. Register the service account: https://signup.earthengine.google.com/

#### NASA Earthdata
1. Register at: https://urs.earthdata.nasa.gov/
2. Add credentials to your `.env` file

#### OpenWeatherMap
1. Register at: https://openweathermap.org/api
2. Get a free API key
3. Add to your `.env` file

## Project Structure

```
flooding-cholera/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings
│   │   ├── database.py          # Database connection
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── schemas/             # Pydantic schemas
│   │   └── seed_database.py     # Database seeder
│   ├── data/
│   │   └── cross_river_lgas.geojson
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/             # Leaflet map components
│   │   │   ├── Dashboard/       # Dashboard & charts
│   │   │   ├── Search/          # LGA search
│   │   │   └── Upload/          # Data upload
│   │   ├── hooks/               # React hooks
│   │   ├── store/               # Zustand store
│   │   └── types/               # TypeScript types
│   └── package.json
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lgas` | GET | List all LGAs |
| `/api/lgas/geojson` | GET | Get LGAs as GeoJSON with risk scores |
| `/api/lgas/dashboard` | GET | Get dashboard summary |
| `/api/lgas/{id}` | GET | Get single LGA details |
| `/api/lgas/{id}/cases` | GET | Get case history for LGA |
| `/api/analytics/lga/{id}` | GET | Get analytics for LGA |
| `/api/analytics/risk-scores` | GET | Get all current risk scores |
| `/api/upload` | POST | Upload CSV/Excel data |
| `/api/risk-scores/calculate` | POST | Trigger risk recalculation |
| `/api/satellite/latest` | GET | Get latest satellite data |

## Risk Calculation

The risk score is calculated using a weighted formula:

```
Risk Score = (Flood × 0.4) + (Rainfall × 0.2) + (Cases × 0.3) + (Vulnerability × 0.1)
```

**Risk Levels:**
- 🟢 Green (Low): Score < 0.3
- 🟡 Yellow (Medium): Score 0.3 - 0.6
- 🔴 Red (High): Score > 0.6

**Components:**
- **Flood Score**: Based on NDWI and flood extent from satellite imagery
- **Rainfall Score**: Based on 7-day cumulative precipitation
- **Case Score**: Based on recent cholera cases and deaths
- **Vulnerability Score**: Based on water/sanitation infrastructure coverage

## Uploading Data

### Case Data CSV Format

```csv
lga_name,report_date,new_cases,deaths,suspected_cases,confirmed_cases
Calabar Municipal,2024-01-15,5,0,3,2
Odukpani,2024-01-15,3,1,2,1
```

### Environmental Data CSV Format

```csv
lga_name,observation_date,rainfall_mm,ndwi,flood_observed
Calabar Municipal,2024-01-15,25.5,0.35,true
Odukpani,2024-01-15,20.0,0.25,false
```

## Data Sources & Setup

The system has nationwide coverage: all 774 LGAs across 37 states plus the Federal Capital Territory (FCT). The datasets and commands below populate the database with real boundaries, flood observations, and cholera case records.

### Data Sources

- **LGA boundaries (nationwide):** Nigerian Local Government Area administrative boundaries from the HDX COD-AB (Common Operational Dataset - Administrative Boundaries) dataset. These geometries underpin the choropleth map and all LGA-based joins.
- **Groundsource flood data:** Flood extent observations from the Groundsource dataset on Zenodo (`https://zenodo.org/records/18647054`, ~667 MB, licensed CC BY 4.0). Provided as a Parquet file and imported via the admin endpoint described below.
- **Real cholera cases:** Epidemiological case data for 2020–2025 at `backend/data/cholera_real/nigeria_cholera_2020_2025.csv`. This CSV is imported by the cholera seed command.

### Setup Commands

From the `backend` directory (with the virtual environment activated), run the following to load nationwide data and recompute risk scores:

```bash
# 1. Seed default alert rules
python -m app.seed_alert_rules

# 2. Import the real cholera CSV into the database
python -m app.seed_cholera

# 3. Backfill risk v2.0 scores across the date range
python -m app.backfill_risks --start 2020-01-01 --end 2025-12-01
```

### Groundsource Import

To import a Groundsource Parquet file after the server is running, call the admin endpoint:

```bash
curl -X POST http://localhost:8000/api/admin/data/groundsource-import \
  -H "Content-Type: application/json" \
  -d '{"path": "/absolute/path/to/groundsource.parquet"}'
```

The sibling endpoint `POST /api/admin/data/cholera-import` (same body shape, pointing at a cholera CSV) is also available for ad-hoc imports.

### `SEED_DEMO` Flag

The `SEED_DEMO` environment variable controls whether demo/seed data is loaded at startup. Set `SEED_DEMO=false` (or unset it) for production deployments that should rely solely on the real datasets above; leave it enabled for local development and quick demos.

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

### Code Formatting

```bash
# Backend
cd backend
black app/
isort app/

# Frontend
cd frontend
npm run lint
```

## Cross River State LGAs

The system monitors all 18 Local Government Areas:

1. Abi
2. Akamkpa
3. Akpabuyo
4. Bakassi
5. Bekwarra
6. Biase
7. Boki
8. Calabar Municipal
9. Calabar South
10. Etung
11. Ikom
12. Obanliku
13. Obubra
14. Obudu
15. Odukpani
16. Ogoja
17. Yakuur
18. Yala

## License

This project is developed for public health surveillance purposes. Please ensure appropriate data handling and privacy practices when deploying with real epidemiological data.

## Acknowledgments

- Nigeria Centre for Disease Control (NCDC)
- Cross River State Ministry of Health
- Google Earth Engine
- NASA Global Precipitation Measurement
# Trigger redeploy Sun Jan 25 00:52:06 WAT 2026
