# coding: utf-8

import inspect
from importlib import util
from pathlib import Path

class BackendsRegistry:
    """ Rejestr sterowników dla załączników """
    
    def __init__(self):
        self.backends_dir = Path(__file__).parent

        self.backends = {}
        for module_name in ['files', 'db']:
            main_module = self.backends_dir.joinpath(module_name).joinpath('main.py')
            #Załadowanie modułu
            spec = util.spec_from_file_location('main', main_module)
            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)
            #Lista obiektów w module
            clsmembers = inspect.getmembers(module, inspect.isclass)
            for (_, c) in clsmembers:
                # Odrzucamy inne klasy niż dziedziczące po klasie bazowej
                if hasattr(c, 'LABEL'):
                    #Aktywacja i rejestracja modułu
                    self.backends[c.LABEL] = c
    
    def getBackendInstance(self, name, parent):
        return self.backends[name]( parent )

#Rejestr jest singletonem, który jest importowany jako instancja klasy
backends_registry = BackendsRegistry()