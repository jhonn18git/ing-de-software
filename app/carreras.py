# Varias carreras de la USFX comparten horarios con Ingeniería de Sistemas.
# Las planillas de semestres 1-4 (y algunos superiores) de CIC, TIS, TEL y
# Ciberseguridad están registradas bajo "Ingeniería de Sistemas" en la DB.
CARRERAS_RELACIONADAS = {
    'Ingeniería en Ciencias de la Computación': [
        'Ingeniería de Sistemas',
        'Ingeniería en Ciencias de la Computación',
    ],
    'Ingeniería en Tecnologías de la Información y Seguridad': [
        'Ingeniería de Sistemas',
        'Ingeniería en Tecnologías de la Información y Seguridad',
    ],
    'Ingeniería en Telecomunicaciones': [
        'Ingeniería de Sistemas',
        'Ingeniería en Telecomunicaciones',
    ],
    'Ingeniería de Sistemas': [
        'Ingeniería de Sistemas',
    ],
    'Ingeniería en Diseño y Animación Digital': [
        'Ingeniería en Diseño y Animación Digital',
    ],
    'Ingeniería en Ciberseguridad': [
        'Ingeniería de Sistemas',
        'Ingeniería en Ciberseguridad',
    ],
}


def get_carreras_buscar(carrera):
    """Retorna la lista de carreras donde buscar horarios para una carrera dada."""
    return CARRERAS_RELACIONADAS.get(carrera, [carrera])
