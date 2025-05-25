def register_apis(app):
    from .data_api import data_bp
    from .analysis_api import analysis_bp
    from .optimize_api import optimize_bp
    from .log_api import log_bp
    app.register_blueprint(data_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(optimize_bp)
    app.register_blueprint(log_bp) 