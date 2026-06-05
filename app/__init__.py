import os
from flask import Flask, send_from_directory
from flask_session import Session
from flask_cors import CORS
from app.database import init_db


def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')

    app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'smartschedule-secret-2026')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './flask_sessions'
    app.config['SESSION_PERMANENT'] = False

    CORS(app, supports_credentials=True)
    Session(app)

    init_db()

    from app.routes.auth import auth_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.productos import productos_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(productos_bp, url_prefix='/api/productos')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
