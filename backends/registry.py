# coding: utf-8

import inspect
from importlib import util
from pathlib import Path

class BackendsRegistry:
    """ Rejestr sterowników dla załączników """
    
    def __init__(self):
        self.backends_dir = Path(__file__).parent

        self.backends = {}
        self.supported = {}
        self.labels = {}
        for module_name in ['files', 'layers']:
            main_module = self.backends_dir.joinpath(module_name).joinpath('main.py')
            #Załadowanie modułu
            spec = util.spec_from_file_location('main', main_module)
            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)
            #Lista obiektów w module
            clsmembers = inspect.getmembers(module, inspect.isclass)
            for (_, c) in clsmembers:
                # Odrzucamy inne klasy niż dziedziczące po klasie bazowej
                label = None
                if hasattr(c, 'LABEL'):
                    label = c.LABEL
                if hasattr(c, 'NAME'):
                    if not label:
                        label = c.NAME
                    self.labels[c.NAME] = label
                    #Aktywacja i rejestracja modułu
                    self.backends[c.NAME] = c
                    if hasattr(c, 'isSupported'):
                        self.supported[c.NAME] = c.isSupported

    def getBackendInstance(self, name, parent):
        return self.backends[name]( parent )

    def getBackendNameFromLabel(self, value):
        for name, label in self.labels.items():
            if value == label:
                return name

#Rejestr jest singletonem, który jest importowany jako instancja klasy
backends_registry = BackendsRegistry()