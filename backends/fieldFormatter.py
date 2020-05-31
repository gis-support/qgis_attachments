from qgis.core import QgsFieldFormatter, NULL
from qgis_attachments.backends.layers.sqlite_driver import SQLiteDriver

class AttachmentsFieldFormatter(QgsFieldFormatter):

    def id(self):
        #ID field formattera musi być takie samo jak nazwa rejestrowana w editorWidgetRegistry
        return 'QGIS Attachments'

    def representValue(self, layer, fieldIndex, config, cache, values):
        if values == NULL:
            return 'Brak załączników'

        if config['backend'] == 'layers':
            layer_path = layer.dataProvider().dataSourceUri().split('|')[0]
            separator = config['valuesSeparator']
            filenames = SQLiteDriver.fetchAttachments(layer_path, values.split(separator), with_ids=False)
            return separator.join(filenames)

        elif config['backend'] == 'files':
            return values
