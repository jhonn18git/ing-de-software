"""
Genera seed_horarios.py parseando los CSVs crudos de las 5 planillas USFX.
Ejecutar: py -3 gen_seed.py
"""
import csv, io, re, glob, unicodedata
from collections import defaultdict


def _norm_key(s: str) -> str:
    """Remove accents + uppercase, collapse spaces → canonical match key."""
    nfd = unicodedata.normalize('NFD', s)
    no_acc = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', no_acc.upper().strip())


# ── Mapeo de nombres de carrera (CSV → canónico DB), usando _norm_key ─────────
# Keys are already normalized (no accents, uppercase)
_CARRERA_MAP_NORM = {
    _norm_key('ING. DE SISTEMAS'):                                        'Ingeniería de Sistemas',
    _norm_key('INGENIERIA DE SISTEMAS'):                                  'Ingeniería de Sistemas',
    _norm_key('ING. EN SISTEMAS'):                                        'Ingeniería de Sistemas',
    _norm_key('ING. EN CIENCIAS DE LA COMPUTACION'):                      'Ingeniería en Ciencias de la Computación',
    _norm_key('INGENIERIA EN CIENCIAS DE LA COMPUTACION'):                'Ingeniería en Ciencias de la Computación',
    _norm_key('INGENIERIA EN TELECOMUNICACIONES'):                        'Ingeniería de Telecomunicaciones',
    _norm_key('INGENIERIA EN DISEÑO Y ANIMACION DIGITAL'):                'Ing. Diseño y Automatización Digital',
    _norm_key('INGENIERIA EN DISEÑO Y ANIMACION DIGITAL'):                'Ing. Diseño y Automatización Digital',
    _norm_key('ING. EN CIBERSEGURIDAD'):                                  'Ingeniería en Ciberseguridad',
    _norm_key('INGENIERIA EN CIBERSEGURIDAD'):                            'Ingeniería en Ciberseguridad',
    _norm_key('ING. TECNOLOGIAS DE LA INFORMACION Y SEGURIDAD'):          'Ingeniería en Tecnologías de la Información y Seguridad',
    _norm_key('ING TECNOLOGIAS DE LA INFORMACION Y SEGURIDAD'):           'Ingeniería en Tecnologías de la Información y Seguridad',
    _norm_key('INGENIERIA EN TECNOLOGIAS DE LA INFORMACION Y SEGURIDAD'): 'Ingeniería en Tecnologías de la Información y Seguridad',
}


def lookup_carrera(raw: str):
    return _CARRERA_MAP_NORM.get(_norm_key(raw))

SEM_MAP = {
    'PRIMERO': 1, 'SEGUNDO': 2, 'TERCERO': 3, 'CUARTO': 4,  'QUINTO': 5,
    'SEXTO':   6, 'SEPTIMO': 7, 'OCTAVO':  8, 'NOVENO': 9,  'DECIMO': 10,
}

DIAS     = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
DAY_COLS = [4, 6, 8, 10, 12, 14]   # materia col per day; sec = col+1


def norm_hora(h: str) -> str:
    h = h.strip()
    return ('0' + h) if re.match(r'^\d:\d\d$', h) else h


def parse_csv(path: str) -> list:
    """
    Parsea un sheet CSV de planilla USFX.
    Retorna lista de tuplas:
      (carrera, semestre, materia, materia, seccion, profesor, dia, hi, hf, aula)
    Solo incluye grupos GESTION 01/2026.
    """
    with open(path, encoding='utf-8', errors='replace') as f:
        raw = f.read()
    rows = list(csv.reader(io.StringIO(raw)))

    records = set()
    current_sem  = None
    current_car  = None   # canonical
    skip_group   = False

    i = 0
    while i < len(rows):
        row = rows[i]
        # Pad row so index access doesn't fail
        while len(row) < 20:
            row.append('')

        # ── FACULTAD row: contains "SEMESTRE: XXXX" ───────────────────────
        cell0 = row[0].strip().upper()
        if 'FACULTAD' in cell0 or 'UNIVERSIDAD' in cell0:
            for cell in row:
                m = re.search(r'SEMESTRE:\s*(\w+)', cell.upper())
                if m:
                    current_sem = SEM_MAP.get(m.group(1))
            i += 1
            continue

        # ── CARRERA row ───────────────────────────────────────────────────
        if cell0.startswith('CARRERA:'):
            raw_car = row[3].strip()
            current_car = lookup_carrera(raw_car)

            # Check gestion
            gestion_str = ' '.join(row).upper()
            has_2026 = '2026' in gestion_str
            # Also skip multi-carrera entries like "SIS, CIC, TIS, TEL"
            raw_car_up = raw_car.upper()
            is_multi = ',' in raw_car_up and len(raw_car_up) < 40
            skip_group = (not has_2026) or is_multi or (current_car is None)
            i += 1
            continue

        # ── Materia row ───────────────────────────────────────────────────
        col3 = row[3].strip()
        if col3 == 'Materia:' and not skip_group and current_sem and current_car:
            hi = norm_hora(row[0])
            hf = norm_hora(row[2])
            # Next row should be Profesor
            prow = rows[i+1] if i+1 < len(rows) else []
            while len(prow) < 20:
                prow.append('')

            for d_idx, d_col in enumerate(DAY_COLS):
                mat = row[d_col].strip()
                sec = row[d_col+1].strip()
                if not mat:
                    continue
                # Ignore legend area (spurious values at col >= 16 are legend, not data)
                # We only process cols 4-15 via DAY_COLS, so this is already safe.
                prof = prow[d_col].strip()
                aula = prow[d_col+1].strip()
                records.add((
                    current_car, current_sem,
                    mat, mat,          # codigo, nombre (planilla only has codigo)
                    sec, prof,
                    DIAS[d_idx], hi, hf, aula,
                ))

        i += 1

    return list(records)


def merge_records(records: list) -> list:
    """
    Merge consecutive 1-hour sub-blocks into complete blocks.
    Group by (carrera, sem, materia, seccion, dia) then merge where hf[i]==hi[i+1].
    """
    groups = defaultdict(list)
    for r in records:
        key = (r[0], r[1], r[2], r[4], r[6])   # carrera,sem,mat,sec,dia
        groups[key].append(r)

    merged = []
    for key, slots in groups.items():
        slots.sort(key=lambda x: x[7])          # sort by hora_inicio
        block = list(slots[0])
        for s in slots[1:]:
            if s[7] == block[8]:                # s.hi == current.hf → extend
                block[8] = s[8]                 # extend hf
                # keep profesor/aula from first sub-block
            else:
                merged.append(tuple(block))
                block = list(s)
        merged.append(tuple(block))

    merged.sort(key=lambda x: (x[0], x[1], x[2], x[4], x[6], x[7]))
    return merged


def main():
    all_records = set()
    csv_files = sorted(
        glob.glob('D:/SIS_gid=*.csv') +
        glob.glob('D:/CIC_gid=*.csv') +
        glob.glob('D:/TEL_gid=*.csv') +
        glob.glob('D:/DAD_gid=*.csv') +
        glob.glob('D:/CIB_gid=*.csv')
    )
    # Also include D:/tmp_cic5.csv if present
    for path in csv_files:
        recs = parse_csv(path)
        all_records.update(recs)
        print(f"  {len(recs):4d} raw  {path.split('/')[-1]}")

    records_list = list(all_records)
    merged = merge_records(records_list)

    print(f"\nTotal merged blocks: {len(merged)}")

    # Print summary by carrera+semestre
    summary = defaultdict(int)
    for r in merged:
        summary[(r[0], r[1])] += 1
    for k in sorted(summary):
        print(f"  {k[0][:35]:<35} sem {k[1]:2d} -> {summary[k]:3d} bloques")

    # Write seed_horarios.py
    out_path = 'app/seed_horarios.py'
    lines = [
        'import logging\n',
        '\n',
        'logger = logging.getLogger(__name__)\n',
        '\n',
        '\n',
        'def seed_horarios(conn):\n',
        '    rows = [\n',
    ]
    for r in merged:
        carrera, sem, mat_cod, mat_nom, sec, prof, dia, hi, hf, aula = r
        lines.append(
            f"        ({carrera!r}, {sem}, {mat_cod!r}, {mat_nom!r}, "
            f"{sec!r}, {prof!r}, {dia!r}, {hi!r}, {hf!r}, {aula!r}),\n"
        )
    lines += [
        '    ]\n',
        '    conn.executemany(\n',
        '        """\n',
        '        INSERT OR IGNORE INTO horarios_usfx\n',
        '            (carrera, semestre, materia_codigo, materia_nombre, seccion, profesor,\n',
        '             dia, hora_inicio, hora_fin, aula)\n',
        '        VALUES (?,?,?,?,?,?,?,?,?,?)\n',
        '        """,\n',
        '        rows\n',
        '    )\n',
        '    logger.info(f"seed_horarios: {len(rows)} bloques insertados")\n',
    ]

    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\nEscrito: {out_path}")


if __name__ == '__main__':
    main()
