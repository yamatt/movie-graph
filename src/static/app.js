let db;
const DB_URL = 'imdb-compact.db';

// Type mapping
const TYPE_MAP = {
    1: 'Movie',
    2: 'TV Series',
    3: 'TV Mini-Series'
};

async function loadDatabase() {
    try {
        document.getElementById('loading-status').textContent = 'Downloading database...';

        const response = await fetch(DB_URL);
        if (!response.ok) throw new Error('Failed to load database');

        const contentLength = response.headers.get('content-length');
        const total = parseInt(contentLength, 10);
        let loaded = 0;

        const reader = response.body.getReader();
        const chunks = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            chunks.push(value);
            loaded += value.length;

            if (total) {
                const progress = Math.round((loaded / total) * 100);
                document.getElementById('loading-status').textContent =
                    `Downloading: ${progress}% (${(loaded / 1024 / 1024).toFixed(1)} MB / ${(total / 1024 / 1024).toFixed(1)} MB)`;
            }
        }

        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const buffer = new Uint8Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            buffer.set(chunk, offset);
            offset += chunk.length;
        }

        document.getElementById('loading-status').textContent = 'Initializing database...';

        const SQL = await window.initSqlJs({
            locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
        });

        db = new SQL.Database(buffer);

        showStats();
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').classList.add('loaded');
    } catch (error) {
        console.error('Error loading database:', error);
        document.getElementById('loading').innerHTML =
            `<div class="error">Failed to load database: ${error.message}</div>`;
    }
}

function showStats() {
    const titles = db.exec('SELECT COUNT(*) FROM titles')[0].values[0][0];
    const people = db.exec('SELECT COUNT(*) FROM people')[0].values[0][0];
    const crew = db.exec('SELECT COUNT(*) FROM crew')[0].values[0][0];

    document.getElementById('stats').innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">${titles.toLocaleString()}</div>
                <div class="stat-label">Titles</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${people.toLocaleString()}</div>
                <div class="stat-label">People</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${crew.toLocaleString()}</div>
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

        const result = db.exec(query);

        if (!result.length || !result[0].values.length) {
            resultsDiv.innerHTML = '<div class="no-results">No common titles found. Try partial names or check spelling.</div>';
            return;
        }

        const html = `
            <h3>Found ${result[0].values.length} title(s):</h3>
            ${result[0].values.map(([id, title, type, premiered]) => `
                <div class="result-item">
                    <div class="result-title">${title}</div>
                    <div class="result-meta">
                        ${TYPE_MAP[type] || 'Unknown'}
                        ${premiered ? `• ${premiered}` : ''}
                        • <a href="https://www.imdb.com/title/${id}/" target="_blank">View on IMDb</a>
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

        const result = db.exec(query);

        if (!result.length || !result[0].values.length) {
            resultsDiv.innerHTML = '<div class="no-results">No common actors found. Try partial titles or check spelling.</div>';
            return;
        }

        const html = `
            <h3>Found ${result[0].values.length} person(s):</h3>
            ${result[0].values.map(([id, name, category]) => `
                <div class="result-item">
                    <div class="result-title">${name}</div>
                    <div class="result-meta">
                        ${category.charAt(0).toUpperCase() + category.slice(1)}
                        • <a href="https://www.imdb.com/name/${id}/" target="_blank">View on IMDb</a>
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
