# CIC, TEL, TIS comparten horarios con SIS para semestre 1 (sem 1 en DB = SIS).
# CIB semestre 1 tiene datos propios; semestres 2+ usan el currículo de TIS.
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
        'Ingeniería en Ciberseguridad',
        'Ingeniería en Tecnologías de la Información y Seguridad',
        'Ingeniería de Sistemas',
    ],
}


def get_carreras_buscar(carrera):
    """Retorna la lista de carreras donde buscar horarios para una carrera dada."""
    return CARRERAS_RELACIONADAS.get(carrera, [carrera])
