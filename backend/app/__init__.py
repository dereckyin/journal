from flask import Flask, jsonify

from .config import Config
from .extensions import cors, db, jwt, limiter, migrate


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # 使用 Bearer JWT（Authorization header），不依賴 cookie → 不需 credentials / CSRF
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
    )
    limiter.init_app(app)

    from . import models  # noqa: F401  (ensure models are registered)

    from .routes.auth import bp as auth_bp
    from .routes.users import bp as users_bp
    from .routes.departments import bp as departments_bp
    from .routes.projects import bp as projects_bp
    from .routes.categories import bp as categories_bp
    from .routes.entries import bp as entries_bp
    from .routes.reports import bp as reports_bp
    from .routes.audit import bp as audit_bp
    from .routes.title_presets import bp as title_presets_bp
    from .routes.change_requests import bp as change_requests_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(entries_bp, url_prefix="/api/entries")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(audit_bp, url_prefix="/api/audit-logs")
    app.register_blueprint(title_presets_bp, url_prefix="/api/title-presets")
    app.register_blueprint(change_requests_bp, url_prefix="/api/change-requests")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify(error=str(err.description) if hasattr(err, "description") else "bad request"), 400

    @app.errorhandler(403)
    def forbidden(err):
        return jsonify(error="forbidden"), 403

    @app.errorhandler(404)
    def not_found(err):
        return jsonify(error="not found"), 404

    @jwt.unauthorized_loader
    def _unauth(reason):
        return jsonify(error=f"missing token: {reason}"), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify(error=f"invalid token: {reason}"), 401

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return jsonify(error="token expired"), 401

    @app.errorhandler(429)
    def rate_limited(err):
        desc = getattr(err, "description", "too many requests")
        return jsonify(error=f"rate limit exceeded: {desc}"), 429

    return app
