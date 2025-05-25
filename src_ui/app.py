import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src-py'))
from flask import Flask, render_template
from flask_cors import CORS
from database import update_database_schema
from api import register_apis

def create_app():
    app = Flask(__name__)
    CORS(app)
    update_database_schema()
    register_apis(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/overview')
    def overview():
        return render_template('overview.html')

    @app.route('/data')
    def data():
        return render_template('data.html')

    @app.route('/optimization')
    def optimization():
        return render_template('optimization.html')

    @app.route('/analysis')
    def analysis():
        return render_template('analysis.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) 