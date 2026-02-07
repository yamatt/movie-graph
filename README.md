# Movie Graph

A compact IMDb database and web application for finding actor and film crossovers.

## Features

- 🎬 **Find Common Films**: Search for films featuring two specific actors
- 👥 **Find Common Actors**: Discover actors who appeared in two different films/shows
- 📊 **Compact Database**: ~21MB SQLite database with 76K+ actors and 5.7K+ titles (40K+ IMDb votes)
- 🌐 **Client-Side Queries**: All searches run in your browser using SQL.js
- 🔄 **Weekly Updates**: Automatically rebuilt every Sunday with latest IMDb data

## Development

### Building the Database

```bash
# Install Python dependencies
uv sync

# Build database (default: 40,000 minimum votes)
uv run -m src.movie-graph

# Custom vote threshold
uv run -m src.movie-graph --min-votes 60000

# Rebuild compact database without re-downloading IMDb data
uv run -m src.movie-graph --skip-download
```

### Web Application

```bash
# Install dependencies
npm install

# Build for production
npm run build

# Development mode (watch)
npm run dev
```

The built files will be in `dist/`:
- `index.html` - HTML page
- `style.css` - Styles
- `bundle.js` - Bundled JavaScript
- `imdb-compact.db` - SQLite database (copied during deployment)

## Technology Stack

**Backend:**
- Python 3.12
- SQLite3
- [imdb-sqlite](https://github.com/cjlee/imdb-sqlite) for downloading IMDb datasets
- uv for dependency management

**Frontend:**
- Vanilla JavaScript
- [SQL.js](https://github.com/sql-js/sql.js) for client-side SQLite
- Webpack 5 for bundling

**Infrastructure:**
- GitHub Actions for CI/CD
- GitHub Pages for hosting

## Database Details

**Configuration:**
- Minimum votes: 40,000 (configurable via `--min-votes`)
- Types: Movies, TV Series, TV Mini-Series
- Crew categories: actor, actress (normalized to 'actor')
- Includes episode crew for guest star crossovers

**Optimizations:**
- WITHOUT ROWID tables
- Type stored as integer (1=movie, 2=tvSeries, 3=tvMiniSeries)
- Composite primary keys
- Strategic indexing
- VACUUM and ANALYZE
```

This will:
1. Download only the necessary IMDb data tables (titles, ratings, people, crew)
2. Filter for popular content based on vote counts (50,000+ votes)
3. Create a compact database (~10MB) at `imdb-compact.db`

### Options

```bash
# Specify custom paths
uv run -m src.movie-graph --source-db imdb-full.db --target-db my-compact.db

# Use a different cache directory
uv run -m src.movie-graph --cache-dir /path/to/cache

# Skip re-downloading if you already have the source database
uv run -m src.movie-graph --skip-download
```

## Database Schema

The compact database contains:

- **titles**: Movies and TV series with ratings and metadata
- **people**: Actors, directors, writers, producers
- **crew**: Relationships between people and titles (who worked on what)

## Querying Examples

```sql
-- Find movies starring a specific actor (exact match)
SELECT t.original_title, t.rating, t.premiered
FROM titles t
JOIN crew c ON t.title_id = c.title_id
JOIN people p ON c.person_id = p.person_id
WHERE p.name LIKE '%Tom Hanks%'
  AND c.category IN ('actor', 'actress')
  AND t.type = 'movie'
ORDER BY t.rating DESC;

-- Fuzzy search for actor names (partial matching)
SELECT name, born, died
FROM people
WHERE name LIKE '%Hank%'  -- Finds "Tom Hanks", "Hank Azaria", etc.
ORDER BY name;

-- Phonetic matching using SOUNDEX (finds similar-sounding names)
SELECT name, born, died
FROM people
WHERE SOUNDEX(name) = SOUNDEX('Tom Hanks')
   OR name LIKE '%Hanks%';

-- Case-insensitive search for actors
SELECT DISTINCT p.name, p.born
FROM people p
WHERE LOWER(p.name) LIKE LOWER('%hanks%');

-- Find all titles where both actors appeared together (with fuzzy matching)
SELECT
    t.original_title,
    t.type,
    t.premiered,
    t.rating,
    t.votes,
    p1.name as actor1_name,
    p2.name as actor2_name
FROM titles t
JOIN crew c1 ON t.title_id = c1.title_id
JOIN crew c2 ON t.title_id = c2.title_id
JOIN people p1 ON c1.person_id = p1.person_id
JOIN people p2 ON c2.person_id = p2.person_id
WHERE p1.name LIKE '%Hanks%'  -- Fuzzy: matches "Tom Hanks", etc.
  AND p2.name LIKE '%Ryan%'    -- Fuzzy: matches "Meg Ryan", "Ryan Gosling", etc.
  AND c1.category IN ('actor', 'actress')
  AND c2.category IN ('actor', 'actress')
ORDER BY t.premiered DESC;

-- Find popular TV series
SELECT original_title, rating, premiered, votes
FROM titles
WHERE type = 'tvSeries'
ORDER BY rating DESC, votes DESC
LIMIT 20;

-- Search for a title using fuzzy matching (no AKAs needed)
SELECT original_title, type, premiered, rating
FROM titles
WHERE original_title LIKE '%Matrix%'
ORDER BY votes DESC;
```

## Customization

To adjust the filtering thresholds, edit the constants in [src/movie-graph/compact.py](src/movie-graph/compact.py):

```python
MIN_VOTES = 50000      # Minimum number of votes (adjust to include more/fewer titles)
MIN_YEAR = 1980        # Earliest year to include
```
