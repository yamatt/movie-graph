import { createDbWorker } from 'sql.js-httpvfs';

let db;
const DB_URL = 'https://pub-d577c0bdf2fd46bfbd7838e1e18b3ad3.r2.dev/imdb-compact.db';

// Type mapping
const TYPE_MAP = {
    1: 'Movie',
    2: 'TV Series',
    3: 'TV Mini-Series'
};

async function loadDatabase() {
    try {
        document.getElementById('loading-status').textContent = 'Initializing database...';

        const workerUrl = new URL(
            'sql.js-httpvfs/dist/sqlite.worker.js',
            import.meta.url
        );
        const wasmUrl = new URL(
            'sql.js-httpvfs/dist/sql-wasm.wasm',
            import.meta.url
        );

        db = await createDbWorker(
            [
                {
                    from: "inline",
                    config: {
                        serverMode: "full",
                        url: DB_URL,
                        requestChunkSize: 4096,
                    }
                }
            ],
            workerUrl.toString(),
            wasmUrl.toString()
        );

        await showStats();
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').classList.add('loaded');
    } catch (error) {
        console.error('Error loading database:', error);
        document.getElementById('loading').innerHTML =
            `<div class="error">Failed to load database: ${error.message}</div>`;
    }
}

async function showStats() {
    const titles = await db.db.query('SELECT COUNT(*) as count FROM titles');
    const people = await db.db.query('SELECT COUNT(*) as count FROM people');
    const crew = await db.db.query('SELECT COUNT(*) as count FROM crew');

    document.getElementById('stats').innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">${titles[0].count.toLocaleString()}</div>
                <div class="stat-label">Titles</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${people[0].count.toLocaleString()}</div>
                <div class="stat-label">People</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${crew[0].count.toLocaleString()}</div>
                <div class="stat-label">Crew Credits</div>
            </div>
        </div>
    `;
}

// Tab switching
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('tab')) {
        const tabId = e.target.dataset.tab;

        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.query-section').forEach(s => s.classList.remove('active'));

        e.target.classList.add('active');
        document.getElementById(tabId).classList.add('active');
    }
});

// Actor crossover search
document.getElementById('actor-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const actor1 = document.getElementById('actor1').value.trim();
    const actor2 = document.getElementById('actor2').value.trim();
    const resultsDiv = document.getElementById('actor-results');

    resultsDiv.innerHTML = '<p>Searching...</p>';

    try {
        const query = `
            SELECT DISTINCT t.title_id, t.original_title, t.type, t.premiered
            FROM titles t
            JOIN crew c1 ON t.title_id = c1.title_id
            JOIN people p1 ON c1.person_id = p1.person_id
            JOIN crew c2 ON t.title_id = c2.title_id
            JOIN people p2 ON c2.person_id = p2.person_id
            WHERE p1.name LIKE '%${actor1}%'
              AND p2.name LIKE '%${actor2}%'
              AND p1.person_id != p2.person_id
            ORDER BY t.premiered DESC
        `;

        const result = await db.db.query(query);

        if (!result.length) {
            resultsDiv.innerHTML = '<div class="no-results">No common titles found. Try partial names or check spelling.</div>';
            return;
        }

        const html = `
            <h3>Found ${result.length} title(s):</h3>
            ${result.map(row => `
                <div class="result-item">
                    <div class="result-title">${row.original_title}</div>
                    <div class="result-meta">
                        ${TYPE_MAP[row.type] || 'Unknown'}
                        ${row.premiered ? `• ${row.premiered}` : ''}
                        • <a href="https://www.imdb.com/title/${row.title_id}/" target="_blank">View on IMDb</a>
                    </div>
                </div>
            `).join('')}
        `;

        resultsDiv.innerHTML = html;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
});

// Film crossover search
document.getElementById('film-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const film1 = document.getElementById('film1').value.trim();
    const film2 = document.getElementById('film2').value.trim();
    const resultsDiv = document.getElementById('film-results');

    resultsDiv.innerHTML = '<p>Searching...</p>';

    try {
        const query = `
            SELECT DISTINCT p.person_id, p.name, c1.category
            FROM people p
            JOIN crew c1 ON p.person_id = c1.person_id
            JOIN titles t1 ON c1.title_id = t1.title_id
            JOIN crew c2 ON p.person_id = c2.person_id
            JOIN titles t2 ON c2.title_id = t2.title_id
            WHERE t1.original_title LIKE '%${film1}%'
              AND t2.original_title LIKE '%${film2}%'
              AND t1.title_id != t2.title_id
            ORDER BY p.name
        `;

        const result = await db.db.query(query);

        if (!result.length) {
            resultsDiv.innerHTML = '<div class="no-results">No common actors found. Try partial titles or check spelling.</div>';
            return;
        }

        const html = `
            <h3>Found ${result.length} person(s):</h3>
            ${result.map(row => `
                <div class="result-item">
                    <div class="result-title">${row.name}</div>
                    <div class="result-meta">
                        ${row.category.charAt(0).toUpperCase() + row.category.slice(1)}
                        • <a href="https://www.imdb.com/name/${row.person_id}/" target="_blank">View on IMDb</a>
                    </div>
                </div>
            `).join('')}
        `;

        resultsDiv.innerHTML = html;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
});

// Load database on page load
loadDatabase();
