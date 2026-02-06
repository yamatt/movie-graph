const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
    mode: 'production',
    entry: './src/static/app.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'dist'),
        clean: true
    },
    plugins: [
        new CopyWebpackPlugin({
            patterns: [
                { from: 'src/static/index.html', to: 'index.html' },
                { from: 'src/static/style.css', to: 'style.css' },
                {
                    from: 'node_modules/sql.js-httpvfs/dist/sqlite.worker.js',
                    to: 'sql.js-httpvfs/dist/sqlite.worker.js'
                },
                {
                    from: 'node_modules/sql.js-httpvfs/dist/sql-wasm.wasm',
                    to: 'sql.js-httpvfs/dist/sql-wasm.wasm'
                }
            ]
        })
    ]
};
