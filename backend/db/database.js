const { DatabaseSync } = require('node:sqlite');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', '..', 'smartschedule.db');
const db = new DatabaseSync(DB_PATH);

db.exec('PRAGMA journal_mode = WAL');
db.exec('PRAGMA foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    image TEXT DEFAULT 'default.jpg',
    rol TEXT CHECK(rol IN ('admin', 'ofertante', 'demandante')) DEFAULT 'demandante',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT NOT NULL,
    status TEXT CHECK(status IN ('pendiente', 'aprobado', 'rechazado')) DEFAULT 'pendiente',
    ofertante_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ofertante_id) REFERENCES users(id) ON DELETE CASCADE
  );
`);

const existingUsers = db.prepare('SELECT COUNT(*) as count FROM users').get();
if (existingUsers.count === 0) {
  const insert = db.prepare(
    'INSERT INTO users (name, username, email, password, rol) VALUES (?, ?, ?, ?, ?)'
  );
  insert.run('Jhonn Llanos Rojas', 'jhonn', 'jhonn@smartschedule.com', '123', 'admin');
  insert.run('Camila Montecinos Solis', 'camila', 'camila@smartschedule.com', '123', 'ofertante');
  insert.run('Erick Arancibia Flores', 'erick', 'erick@smartschedule.com', '123', 'demandante');
}

module.exports = db;
