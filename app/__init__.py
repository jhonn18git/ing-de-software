import os
from flask import Flask, send_from_directory
from flask_session import Session
from app.database import init_db


def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')

    app.config['SECRET_KEY']             = os.environ.get('SESSION_SECRET', 'smartschedule-secret-2026')
    app.config['SESSION_TYPE']           = 'filesystem'
    app.config['SESSION_FILE_DIR']       = './flask_sessions'
    app.config['SESSION_PERMANENT']      = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    Session(app)
    init_db()

    from app.routes.auth        import auth_bp
    from app.routes.usuarios    import usuarios_bp
    from app.routes.productos   import productos_bp
    from app.routes.perfil      import perfil_bp
    from app.routes.materias    import materias_bp
    from app.routes.evaluaciones import evaluaciones_bp
    from app.routes.horarios    import horario_bp

    app.register_blueprint(auth_bp,         url_prefix='/api/auth')
    app.register_blueprint(usuarios_bp,     url_prefix='/api/usuarios')
    app.register_blueprint(productos_bp,    url_prefix='/api/productos')
    app.register_blueprint(perfil_bp,       url_prefix='/api/perfil')
    app.register_blueprint(materias_bp,     url_prefix='/api/materias')
    app.register_blueprint(evaluaciones_bp, url_prefix='/api/evaluaciones')
    app.register_blueprint(horario_bp,      url_prefix='/api/horario')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        full = os.path.join(app.static_folder, path)
        if path and os.path.isfile(full):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
