# coding: utf-8

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QStyleOptionButton, QPushButton
from qgis.PyQt.QtCore import QRect, QEvent, QSize
from math import floor

class OptionButton:
    """ Przycisk dla pojedycznej akcji """

    def __init__(self, icon, callback):
        """ Przycisk definiuje ikona i akcja wywoływana po jej kliknięciu """
        self.icon = icon
        self.callback = callback

class OptionButtonsDelegate(QStyledItemDelegate):
    """ Domyślne wymiary obszaru opcji """
    HEIGHT = 30
    WIDTH = 30

    def __init__(self, buttons):
        super(OptionButtonsDelegate, self).__init__()
        self.buttons = buttons

    def paint(self, painter, option, index):
        """ Narysowanie przycisków opcji """
        r = option.rect
        for i, btn in enumerate(self.buttons):
            x, y = self.calcPosition(i, option)
            button = QStyleOptionButton()
            button.rect = QRect(x, y, self.WIDTH, self.HEIGHT)
            button.state = QStyle.State_Enabled
            button.icon = btn.icon
            button.iconSize = QSize(24, 24)
            button.features = QStyleOptionButton.Flat
            QApplication.style().drawControl( QStyle.CE_PushButton, button, painter)
    
    def editorEvent(self, event, model, option, index):
        """ Kliknięcie w przycisk """
        if event.type()==QEvent.MouseButtonRelease:
            #Na podstawie miejsca kliknięcia sprawdzamy, którą opcję klikną użytkownik
            x = event.x()
            column = floor(x/self.WIDTH)
            try:
                button = self.buttons[column]
            except IndexError:
                #Nie znaleziono opcji
                return False
            #Znaleziono opcję, wywołujemy jej akcję
            button.callback(index)
        return False

    def calcPosition(self, column, option):
        """ Oblicznie pozycji danej opcji w komórce tabeli """
        r = option.rect
        x = 0 + column*self.WIDTH
        y = r.top()+( (r.height()-self.HEIGHT)/2 )
        return x, y

    def columnWidth(self):
        """ Zwraca minimalną szerokość komórki na podstawie ilości opcji.
        Kolumna nie może być węższa niż 50px ze względu na nazwę kolumny """
        return max(self.WIDTH*len(self.buttons), 50)