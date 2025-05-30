import pkgutil
import importlib
from flask import Flask, Blueprint

def register_apis(app: Flask):
    package = __package__ or 'api'
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{package}.{module_name}", __package__)
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, Blueprint):
                app.register_blueprint(obj) 