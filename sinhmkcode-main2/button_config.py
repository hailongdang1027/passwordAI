# python 
from PyQt5.QtWidgets import QPushButton, QLineEdit, QTextEdit, QComboBox
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout  # for testing
from PyQt5.QtCore import QVariantAnimation, QAbstractAnimation
from PyQt5.QtGui import QColor, QFont

bg_color = "background-color:qlineargradient(spread:pad, x1:0, y1:0, x2:0.930852, y2:0.903409, stop:0 rgba(145, 232, 211, 255), stop:1 rgba(105, 160, 226, 255));"
button_color = "background-color: qlineargradient(spread:pad, x1:0.1133, y1:0.102273, x2:0.852217, y2:0.823864, stop:0 rgba(172, 238, 214, 255), stop:1 rgba(217, 236, 164, 255));"
button_config = "border-radius:21px;\n" + "border-style: solid;\n" + "color: black;\n"
style_sheet_button = button_color + button_config



def Template_init(Obj):
    class Button_Obj(Obj):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.color1 = QColor(169, 235, 224)
            self.color2 = QColor(234, 240, 191)
            font = QFont("Times New Roman", 30)
            self.setFont(font)

            self._animation = QVariantAnimation(self,
                                                valueChanged=self._animate,
                                                startValue=0.00001,
                                                endValue=0.9999,
                                                duration=300)

        def _animate(self, value):
            qss = """
                        font-weight: bold;
                        color: rgb(255, 255, 255);
                        border-style: solid;
                        border-radius:21px;
                    """
            grad = "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:{value} {color2}, stop: 1.0 {color1});".format(
                color1=self.color1.name(), color2=self.color2.name(), value=value
            )
            qss += grad
            self.setStyleSheet(qss + button_config)

        def enterEvent(self, event):
            self._animation.setDirection(QAbstractAnimation.Forward)
            self._animation.start()

        def leaveEvent(self, event):
            self._animation.setDirection(QAbstractAnimation.Backward)
            self._animation.start()
            super().leaveEvent(event)
    return Button_Obj


PushButton = Template_init(QPushButton)
LineEdit = Template_init(QLineEdit)
TextEdit = Template_init(QTextEdit)
ComboBox = Template_init(QComboBox)


if __name__ == '__main__':
    pass
