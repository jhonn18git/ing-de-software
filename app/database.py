import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

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

    # TEMP: forzar recarga del seed con datos CIC semestres 2-10.
    # Quitar este bloque después de confirmar que funciona en Render.
    try:
        conn.execute("DELETE FROM horarios_usfx")
        conn.commit()
    except Exception:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            image TEXT DEFAULT 'default.jpg',
            rol TEXT CHECK(rol IN ('admin','ofertante','demandante')) DEFAULT 'demandante',
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
            status TEXT CHECK(status IN ('pendiente','aprobado','rechazado')) DEFAULT 'pendiente',
            ofertante_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ofertante_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS horarios_usfx (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carrera TEXT NOT NULL,
            semestre INTEGER NOT NULL,
            grupo TEXT NOT NULL,
            dia TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            materia_codigo TEXT NOT NULL,
            materia_nombre TEXT,
            aula TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS perfil_academico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            carrera TEXT NOT NULL,
            semestre INTEGER NOT NULL,
            grupo TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS materias_estudiante (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            materia_codigo TEXT NOT NULL,
            materia_nombre TEXT NOT NULL,
            dificultad INTEGER CHECK(dificultad BETWEEN 1 AND 5) DEFAULT 3,
            horas_semana INTEGER DEFAULT 2,
            color TEXT DEFAULT '#3182ce',
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(usuario_id, materia_codigo)
        )
    ''')

    # Migrar evaluaciones si tiene esquema viejo (columna materia_id)
    old_cols = [r[1] for r in c.execute("PRAGMA table_info(evaluaciones)").fetchall()]
    if old_cols and 'materia_id' in old_cols:
        c.execute("DROP TABLE evaluaciones")
        logger.info("Tabla evaluaciones migrada al nuevo esquema")

    c.execute('''
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            materia_codigo TEXT NOT NULL,
            materia_nombre TEXT NOT NULL,
            titulo TEXT NOT NULL,
            fecha DATE NOT NULL,
            tipo TEXT CHECK(tipo IN ('examen','trabajo','practica','otro')) DEFAULT 'examen',
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS horario_estudio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            horario_json TEXT NOT NULL,
            generado_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Seed inicial
    count = c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if count == 0:
        seed_users = [
            ('Jhonn Llanos Rojas',       'jhonn',  'jhonn@smartschedule.com',  '123', 'admin'),
            ('Camila Montecinos Solis',   'camila', 'camila@smartschedule.com', '123', 'ofertante'),
            ('Erick Arancibia Flores',    'erick',  'erick@smartschedule.com',  '123', 'demandante'),
        ]
        c.executemany(
            'INSERT INTO users (name, username, email, password, rol) VALUES (?, ?, ?, ?, ?)',
            seed_users
        )

    conn.commit()

    from app.seed_horarios import seed_horarios
    seed_horarios(conn)

    count = conn.execute("SELECT COUNT(*) FROM horarios_usfx").fetchone()[0]
    print(f"DEBUG init_db - horarios_usfx tiene {count} filas al finalizar init_db")

    conn.close()
