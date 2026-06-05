import sqlite3
import os

DB_PATH = os.environ.get('DB_PATH', 'smartschedule.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
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
        )
    ''')

    c.execute('''
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
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            dificultad INTEGER CHECK(dificultad BETWEEN 1 AND 5) NOT NULL,
            color TEXT DEFAULT '#3182ce',
            usuario_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS disponibilidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            lunes INTEGER DEFAULT 0,
            martes INTEGER DEFAULT 0,
            miercoles INTEGER DEFAULT 0,
            jueves INTEGER DEFAULT 0,
            viernes INTEGER DEFAULT 0,
            sabado INTEGER DEFAULT 0,
            domingo INTEGER DEFAULT 0,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            materia_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            tipo TEXT CHECK(tipo IN ('examen', 'trabajo', 'practica', 'otro')) DEFAULT 'examen',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (materia_id) REFERENCES materias(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            horario_json TEXT NOT NULL,
            generado_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    count = c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if count == 0:
        seed_users = [
            ('Jhonn Llanos Rojas', 'jhonn', 'jhonn@smartschedule.com', '123', 'admin'),
            ('Camila Montecinos Solis', 'camila', 'camila@smartschedule.com', '123', 'ofertante'),
            ('Erick Arancibia Flores', 'erick', 'erick@smartschedule.com', '123', 'demandante'),
        ]
        c.executemany(
            'INSERT INTO users (name, username, email, password, rol) VALUES (?, ?, ?, ?, ?)',
            seed_users
        )

    conn.commit()
    conn.close()
