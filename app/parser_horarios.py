import csv
import io
import re
import logging

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)

SHEETS = {
    'SIS':     '1T4ybdpKYDZPRcniKiUS4KrI6Z4nMAC4y',
    'DAD':     '1lhi_WCpYAlvO1gf6hAH4U56YmsC_eUtN',
    'TEL':     '17-ZQBIwR-dO_94kOmK6kHghayh7_FH_E',
    'CIB':     '12nrDStZz4EVHyubwQFH68ta6pxiXaNjo',
    'CIC':     '1vUQnqhAXNiBMoaj8rLQ5ozDoERjRwN_x',
    'LAB_FIS': '1xwWY34Bd-xho6e0uetCa7sN7KD3-XyWb',
}

CARRERA_MAP = {
    'ING. DE SISTEMAS':                                          'Ingeniería de Sistemas',
    'INGENIERÍA DE SISTEMAS':                                    'Ingeniería de Sistemas',
    'INGENIERIA DE SISTEMAS':                                    'Ingeniería de Sistemas',
    'ING. EN CIENCIAS DE LA COMPUTACIÓN':                       'Ingeniería en Ciencias de la Computación',
    'ING. EN CIENCIAS DE LA COMPUTACION':                       'Ingeniería en Ciencias de la Computación',
    'INGENIERÍA EN CIENCIAS DE LA COMPUTACIÓN':                 'Ingeniería en Ciencias de la Computación',
    'ING. EN TELECOMUNICACIONES':                               'Ingeniería en Telecomunicaciones',
    'INGENIERÍA EN TELECOMUNICACIONES':                         'Ingeniería en Telecomunicaciones',
    'ING. EN DISEÑO Y ANIMACIÓN DIGITAL':                       'Ingeniería en Diseño y Animación Digital',
    'ING. EN DISENO Y ANIMACION DIGITAL':                       'Ingeniería en Diseño y Animación Digital',
    'INGENIERÍA EN DISEÑO Y ANIMACIÓN DIGITAL':                 'Ingeniería en Diseño y Animación Digital',
    'ING. EN TECNOLOGÍAS DE LA INFORMACIÓN Y SEGURIDAD':        'Ingeniería en Tecnologías de la Información y Seguridad',
    'ING. EN TECNOLOGIAS DE LA INFORMACION Y SEGURIDAD':        'Ingeniería en Tecnologías de la Información y Seguridad',
    'INGENIERÍA EN TECNOLOGÍAS DE LA INFORMACIÓN Y SEGURIDAD':  'Ingeniería en Tecnologías de la Información y Seguridad',
}

DIA_MAP = {
    'lunes':     'lunes',
    'martes':    'martes',
    'miércoles': 'miercoles',
    'miercoles': 'miercoles',
    'jueves':    'jueves',
    'viernes':   'viernes',
    'sábado':    'sabado',
    'sabado':    'sabado',
}

_HORA_RE    = re.compile(r'^(\d{1,2})[:\.]00$')
_RANGE_RE   = re.compile(r'(\d{1,2})[:\.]00\s*[-–]\s*(\d{1,2})[:\.]00')
_CODE_RE    = re.compile(r'^([A-Z]{2,4}\d{2,3}[A-Z]?)\s*(.*)')


def _normalize_carrera(raw: str) -> str:
    key = raw.upper().strip()
    return CARRERA_MAP.get(key, raw.strip())


def _fmt_hour(h: int) -> str:
    return f'{h:02d}:00'


def _download_csv(sheet_id: str) -> str | None:
    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
    try:
        resp = _requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        logger.warning('No se pudo descargar sheet %s: %s', sheet_id, exc)
        return None


def _parse_csv(content: str, label: str) -> list[dict]:
    """
    Parsea el CSV de un horario USFX.

    Formato esperado (export de Google Sheets):
      - Fila de metadata: celdas con "CARRERA:", "SEMESTRE:", "GRUPO"
      - Fila de encabezado de días: Lunes, Martes, Miércoles, Jueves, Viernes, Sábado
      - Fila de franja horaria: col[0]="HH:00", col[1]="-", col[2]="HH:00"
        (o col[0]="HH:00-HH:00", o solo col[0]="HH:00")
      - Fila "Materia:" inmediatamente debajo de la franja:
        col[0]="Materia:", luego para cada columna de día: código/nombre de materia
        col siguiente = aula
    """
    rows = list(csv.reader(io.StringIO(content)))
    records: list[dict] = []

    carrera = None
    semestre = None
    grupo = None
    day_cols: dict[int, str] = {}   # col_index → 'lunes'
    hora_inicio = None
    hora_fin = None

    for row in rows:
        cells = [c.strip() for c in row]

        # ── Detectar metadata en cualquier celda ──────────────────────────
        row_upper = ' '.join(cells).upper()

        for i, cell in enumerate(cells):
            cu = cell.upper()
            if 'CARRERA:' in cu:
                raw = re.sub(r'.*CARRERA:\s*', '', cell, flags=re.IGNORECASE).strip()
                if raw:
                    carrera = _normalize_carrera(raw)
            if 'SEMESTRE:' in cu:
                m = re.search(r'\d+', cell)
                if m:
                    semestre = int(m.group())
            if re.search(r'\bGRUPO\b', cu):
                m = re.search(r'GRUPO\s*[:\-]?\s*([A-Z0-9])', cu)
                if m:
                    grupo = m.group(1)

        # ── Detectar fila de encabezado de días ──────────────────────────
        row_lower = [c.lower() for c in cells]
        dia_found = any(d in row_lower for d in DIA_MAP)
        if dia_found:
            day_cols = {}
            for j, cell in enumerate(cells):
                cl = cell.lower()
                if cl in DIA_MAP:
                    day_cols[j] = DIA_MAP[cl]
            hora_inicio = None
            hora_fin = None
            continue

        if not day_cols:
            continue

        # ── Detectar fila de franja horaria ──────────────────────────────
        # Formato A: "07:00", "-", "08:00"
        if (len(cells) >= 3
                and _HORA_RE.match(cells[0])
                and cells[1] == '-'
                and _HORA_RE.match(cells[2])):
            hi = int(cells[0].split(':')[0])
            hf = int(cells[2].split(':')[0])
            hora_inicio = _fmt_hour(hi)
            hora_fin    = _fmt_hour(hf)
            continue

        # Formato B: "07:00-08:00" en una sola celda
        if cells and _RANGE_RE.match(cells[0]):
            m = _RANGE_RE.match(cells[0])
            hora_inicio = _fmt_hour(int(m.group(1)))
            hora_fin    = _fmt_hour(int(m.group(2)))
            continue

        # Formato C: solo "07:00" (bloque de 1 h)
        if cells and _HORA_RE.match(cells[0]):
            hi = int(cells[0].split(':')[0])
            hora_inicio = _fmt_hour(hi)
            hora_fin    = _fmt_hour(hi + 1)
            continue

        # ── Detectar fila "Materia:" ──────────────────────────────────────
        if not hora_inicio:
            continue

        first = cells[0].lower() if cells else ''
        is_materia_row = first.startswith('materia')

        # También aceptar filas donde las columnas de día tienen datos
        # aunque no empiece con "Materia:"
        if not is_materia_row:
            # Intentar si hay contenido de código de materia en cols de día
            if not any(cells[j] for j in day_cols if j < len(cells)):
                continue

        for col_idx, dia in day_cols.items():
            if col_idx >= len(cells):
                continue
            cell_val = cells[col_idx]
            if not cell_val:
                continue

            # Intentar separar código y nombre
            m = _CODE_RE.match(cell_val)
            if m:
                codigo = m.group(1)
                nombre = m.group(2).strip() or cell_val
            else:
                codigo = cell_val[:15]
                nombre = cell_val

            # Aula: columna siguiente
            aula = ''
            if col_idx + 1 < len(cells):
                aula = cells[col_idx + 1]

            if carrera and semestre is not None and grupo:
                records.append({
                    'carrera':        carrera,
                    'semestre':       semestre,
                    'grupo':          grupo,
                    'dia':            dia,
                    'hora_inicio':    hora_inicio,
                    'hora_fin':       hora_fin,
                    'materia_codigo': codigo,
                    'materia_nombre': nombre,
                    'aula':           aula,
                })

        if is_materia_row:
            hora_inicio = None
            hora_fin = None

    logger.info('[%s] Registros extraídos: %d', label, len(records))
    return records


def parsear_y_cargar_horarios(db_path: str) -> int:
    """
    Descarga y parsea las planillas USFX e inserta en horarios_usfx.
    Solo ejecuta si la tabla está vacía.
    Retorna el número de registros insertados.
    """
    import sqlite3

    if not HAS_REQUESTS:
        logger.warning('requests no instalado — se omite carga de horarios USFX')
        return 0

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute('SELECT COUNT(*) FROM horarios_usfx').fetchone()[0]
        if count > 0:
            logger.info('horarios_usfx ya tiene %d registros — se omite parseo', count)
            return 0

        total = 0
        for label, sheet_id in SHEETS.items():
            content = _download_csv(sheet_id)
            if not content:
                continue
            records = _parse_csv(content, label)
            if not records:
                logger.warning('[%s] No se extrajeron registros', label)
                continue
            conn.executemany(
                '''INSERT INTO horarios_usfx
                   (carrera, semestre, grupo, dia, hora_inicio, hora_fin,
                    materia_codigo, materia_nombre, aula)
                   VALUES (:carrera, :semestre, :grupo, :dia, :hora_inicio, :hora_fin,
                           :materia_codigo, :materia_nombre, :aula)''',
                records
            )
            total += len(records)
            logger.info('[%s] Insertados %d registros', label, len(records))

        conn.commit()
        logger.info('Total insertado en horarios_usfx: %d', total)
        return total
    except Exception as exc:
        logger.error('Error al cargar horarios USFX: %s', exc)
        return 0
    finally:
        conn.close()
