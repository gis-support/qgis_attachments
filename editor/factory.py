# coding: utf-8

from qgis.PyQt.QtCore import QVariant
from qgis.gui import QgsEditorWidgetFactory
from qgis_attachments.editor.configWidget import AttachmentControlWidgetConfig
from qgis_attachments.editor.widget import AttachmentControlWidgetWrapper

class AttachmentControlWidget(QgsEditorWidgetFactory):
    """ Klasa do zarządzania kontrolkami dla załączników """

    def create(self, vl, fieldIdx, editor, parent):
        """ Kontrolka dla formularza """
        self.wrapper = AttachmentControlWidgetWrapper(vl, fieldIdx, editor, parent)
        return self.wrapper

    def configWidget(self, vl, fieldIdx, parent):
        """ Kontrolka ustawień """
        return AttachmentControlWidgetConfig(vl, fieldIdx, parent)
    
    def fieldScore(self, vl, fieldIdx):
        """ Wspierane są tylko pola tekstowe """
        field = vl.fields().field(fieldIdx)
        if vl.providerType() == 'postgres':
            return 5 if field.type()==QVariant.String and field.name()=='__attachments' else 0
        else:
            return 0