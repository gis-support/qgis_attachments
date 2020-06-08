from qgis.core import QgsFieldFormatter, NULL
from qgis_attachments.backends.layers.sqlite_driver import SQLiteDriver
from qgis_attachments.translator import translate
from qgis_attachments.backends.registry import backends_registry

translate_ = lambda msg: translate('FieldFormatter', msg)

class AttachmentsFieldFormatter(QgsFieldFormatter):

    def id(self):
        #ID field formattera musi być takie samo jak nazwa rejestrowana w editorWidgetRegistry
        return 'QGIS Attachments'

    def representValue(self, layer, fieldIndex, config, cache, value):
        if value == NULL:
            return translate_('Brak załączników')

        #Aktualny backend
        backend = backends_registry.backends.get(config['backend'])
        if not backend:
            return value
        #Zwrócenie wartości dla danego backendu
        return backend.representValue(self, layer, fieldIndex, config, cache, value)
