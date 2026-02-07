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
                        requestChunkSize: 1024 * 1024, // 1MB chunks
                    }
                }
            ],
            workerUrl.toString(),
            wasmUrl.toString()
        );

        await showStats();
        initAutocomplete();
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

function debounce(fn, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), wait);
    };
}

function setupAutocomplete({
    inputId,
    minChars,
    fetchSuggestions,
    renderSuggestion,
    onSelect
}) {
    const input = document.getElementById(inputId);
    if (!input) {
        return;
    }

    const list = document.createElement('div');
    list.className = 'autocomplete-list';
    list.style.display = 'none';
    input.parentNode.appendChild(list);

    let activeIndex = -1;
    let items = [];

    const closeList = () => {
        list.style.display = 'none';
        list.innerHTML = '';
        activeIndex = -1;
        items = [];
    };

    const openList = () => {
        if (items.length) {
            list.style.display = 'block';
        }
    };

    const renderList = (suggestions) => {
        items = suggestions;
        list.innerHTML = '';
        activeIndex = -1;
        if (!suggestions.length) {
            closeList();
            return;
        }

        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = renderSuggestion(suggestion);
            item.addEventListener('mousedown', (event) => {
                event.preventDefault();
                onSelect(suggestion);
                closeList();
            });
            item.addEventListener('mousemove', () => {
                const previous = list.querySelector('.autocomplete-item.active');
                if (previous) {
                    previous.classList.remove('active');
                }
                activeIndex = index;
                item.classList.add('active');
            });
            list.appendChild(item);
        });

        openList();
    };

    const updateSuggestions = debounce(async () => {
        const term = input.value.trim();
        if (term.length < minChars) {
            closeList();
            return;
        }

        try {
            const suggestions = await fetchSuggestions(term);
            renderList(suggestions);
        } catch (error) {
            console.error('Autocomplete error:', error);
            closeList();
        }
    }, 200);

    input.addEventListener('input', updateSuggestions);
    input.addEventListener('focus', updateSuggestions);
    input.addEventListener('blur', () => {
        setTimeout(closeList, 150);
    });
    input.addEventListener('keydown', (event) => {
        if (!items.length || list.style.display === 'none') {
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            activeIndex = (activeIndex + 1) % items.length;
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            activeIndex = (activeIndex - 1 + items.length) % items.length;
        } else if (event.key === 'Enter') {
            if (activeIndex >= 0) {
                event.preventDefault();
                onSelect(items[activeIndex]);
                closeList();
            }
            return;
        } else if (event.key === 'Escape') {
            closeList();
            return;
        } else {
            return;
        }

        const previous = list.querySelector('.autocomplete-item.active');
        if (previous) {
            previous.classList.remove('active');
        }
        const next = list.children[activeIndex];
        if (next) {
            next.classList.add('active');
            next.scrollIntoView({ block: 'nearest' });
        }
    });
}

function scoreMatch(value, term) {
    const text = value.toLowerCase();
    const query = term.toLowerCase();

    if (!query) {
        return 0;
    }
    if (text === query) {
        return 1000;
    }
    if (text.startsWith(query)) {
        return 900 - text.length;
    }

    const wordIndex = text.split(/\s+/).findIndex(word => word.startsWith(query));
    if (wordIndex >= 0) {
        return 800 - wordIndex;
    }

    const pos = text.indexOf(query);
    if (pos >= 0) {
        return 700 - pos;
    }

    let lastIndex = -1;
    let streak = 0;
    let score = 0;
    for (const char of query) {
        const idx = text.indexOf(char, lastIndex + 1);
        if (idx === -1) {
            return 0;
        }
        streak = idx === lastIndex + 1 ? streak + 1 : 1;
        score += 10 + streak * 2;
        lastIndex = idx;
    }

    return score;
}

function sortSuggestions(rows, term) {
    return rows
        .map(row => ({
            ...row,
            _score: scoreMatch(row.name || row.original_title || '', term)
        }))
        .filter(row => row._score > 0)
        .sort((a, b) => b._score - a._score);
}

function initAutocomplete() {
    setupAutocomplete({
        inputId: 'actor1',
        minChars: 2,
        fetchSuggestions: async (term) => {
            const rows = await db.db.query(
                'SELECT person_id, name FROM people WHERE name LIKE ? LIMIT 50',
                [`%${term}%`]
            );
            return sortSuggestions(rows, term).slice(0, 8);
        },
        renderSuggestion: (row) => `${row.name}`,
        onSelect: (row) => {
            const input = document.getElementById('actor1');
            input.value = row.name;
            input.dataset.personId = row.person_id;
        }
    });

    setupAutocomplete({
        inputId: 'actor2',
        minChars: 2,
        fetchSuggestions: async (term) => {
            const rows = await db.db.query(
                'SELECT person_id, name FROM people WHERE name LIKE ? LIMIT 50',
                [`%${term}%`]
            );
            return sortSuggestions(rows, term).slice(0, 8);
        },
        renderSuggestion: (row) => `${row.name}`,
        onSelect: (row) => {
            const input = document.getElementById('actor2');
            input.value = row.name;
            input.dataset.personId = row.person_id;
        }
    });

    setupAutocomplete({
        inputId: 'film1',
        minChars: 2,
        fetchSuggestions: async (term) => {
            const rows = await db.db.query(
                'SELECT title_id, original_title, premiered, type FROM titles WHERE original_title LIKE ? LIMIT 50',
                [`%${term}%`]
            );
            return sortSuggestions(rows, term).slice(0, 8);
        },
        renderSuggestion: (row) => {
            const year = row.premiered ? ` (${row.premiered})` : '';
            const type = TYPE_MAP[row.type] ? ` • ${TYPE_MAP[row.type]}` : '';
            return `${row.original_title}<div class="autocomplete-meta">${year}${type}</div>`;
        },
        onSelect: (row) => {
            const input = document.getElementById('film1');
            input.value = row.original_title;
            input.dataset.titleId = row.title_id;
        }
    });

    setupAutocomplete({
        inputId: 'film2',
        minChars: 2,
        fetchSuggestions: async (term) => {
            const rows = await db.db.query(
                'SELECT title_id, original_title, premiered, type FROM titles WHERE original_title LIKE ? LIMIT 50',
                [`%${term}%`]
            );
            return sortSuggestions(rows, term).slice(0, 8);
        },
        renderSuggestion: (row) => {
            const year = row.premiered ? ` (${row.premiered})` : '';
            const type = TYPE_MAP[row.type] ? ` • ${TYPE_MAP[row.type]}` : '';
            return `${row.original_title}<div class="autocomplete-meta">${year}${type}</div>`;
        },
        onSelect: (row) => {
            const input = document.getElementById('film2');
            input.value = row.original_title;
            input.dataset.titleId = row.title_id;
        }
    });

    document.getElementById('film1').addEventListener('input', (event) => {
        event.currentTarget.dataset.titleId = '';
    });
    document.getElementById('film2').addEventListener('input', (event) => {
        event.currentTarget.dataset.titleId = '';
    });
    document.getElementById('actor1').addEventListener('input', (event) => {
        event.currentTarget.dataset.personId = '';
    });
    document.getElementById('actor2').addEventListener('input', (event) => {
        event.currentTarget.dataset.personId = '';
    });
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
    const actor1Id = document.getElementById('actor1').dataset.personId?.trim();
    const actor2Id = document.getElementById('actor2').dataset.personId?.trim();
    const resultsDiv = document.getElementById('actor-results');

    resultsDiv.innerHTML = '<p>Searching...</p>';

    if (actor1.length < 2 || actor2.length < 2) {
        resultsDiv.innerHTML = '<div class="no-results">Please enter at least 2 characters for both actors.</div>';
        return;
    }

    try {
                const queryById = `
                        SELECT DISTINCT t.title_id, t.original_title, t.type, t.premiered
                        FROM titles t
                        JOIN crew c1 ON t.title_id = c1.title_id
                        JOIN people p1 ON c1.person_id = p1.person_id
                        JOIN crew c2 ON t.title_id = c2.title_id
                        JOIN people p2 ON c2.person_id = p2.person_id
                        WHERE p1.person_id = ?
                            AND p2.person_id = ?
                            AND p1.person_id != p2.person_id
                        ORDER BY t.premiered DESC
                `;

                const queryByName = `
                        SELECT DISTINCT t.title_id, t.original_title, t.type, t.premiered
                        FROM titles t
                        JOIN crew c1 ON t.title_id = c1.title_id
                        JOIN people p1 ON c1.person_id = p1.person_id
                        JOIN crew c2 ON t.title_id = c2.title_id
                        JOIN people p2 ON c2.person_id = p2.person_id
                        WHERE p1.name LIKE ?
                            AND p2.name LIKE ?
                            AND p1.person_id != p2.person_id
                        ORDER BY t.premiered DESC
                `;

                const result = (actor1Id && actor2Id)
                        ? await db.db.query(queryById, [actor1Id, actor2Id])
                        : await db.db.query(queryByName, [`%${actor1}%`, `%${actor2}%`]);

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

    const film1Input = document.getElementById('film1');
    const film2Input = document.getElementById('film2');
    const film1 = film1Input.value.trim();
    const film2 = film2Input.value.trim();
    const film1Id = film1Input.dataset.titleId?.trim();
    const film2Id = film2Input.dataset.titleId?.trim();
    const resultsDiv = document.getElementById('film-results');

    resultsDiv.innerHTML = '<p>Searching...</p>';

    if (film1.length < 2 || film2.length < 2) {
        resultsDiv.innerHTML = '<div class="no-results">Please enter at least 2 characters for both titles.</div>';
        return;
    }

    try {
        const queryById = `
            SELECT DISTINCT p.person_id, p.name, c1.category
            FROM people p
            JOIN crew c1 ON p.person_id = c1.person_id
            JOIN titles t1 ON c1.title_id = t1.title_id
            JOIN crew c2 ON p.person_id = c2.person_id
            JOIN titles t2 ON c2.title_id = t2.title_id
            WHERE t1.title_id = ?
              AND t2.title_id = ?
              AND t1.title_id != t2.title_id
              AND c1.category IN ('actor', 'actress')
              AND c2.category IN ('actor', 'actress')
            ORDER BY p.name
        `;

        const queryByTitle = `
            SELECT DISTINCT p.person_id, p.name, c1.category
            FROM people p
            JOIN crew c1 ON p.person_id = c1.person_id
            JOIN titles t1 ON c1.title_id = t1.title_id
            JOIN crew c2 ON p.person_id = c2.person_id
            JOIN titles t2 ON c2.title_id = t2.title_id
            WHERE t1.original_title LIKE ?
              AND t2.original_title LIKE ?
              AND t1.title_id != t2.title_id
              AND c1.category IN ('actor', 'actress')
              AND c2.category IN ('actor', 'actress')
            ORDER BY p.name
        `;

        const result = (film1Id && film2Id)
            ? await db.db.query(queryById, [film1Id, film2Id])
            : await db.db.query(queryByTitle, [`%${film1}%`, `%${film2}%`]);

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
