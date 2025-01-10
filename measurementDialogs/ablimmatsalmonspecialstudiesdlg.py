"""
updated December 2024 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- signal/slot connections
- moved variable declarations into __init__
- added some function explanation
- fixed any PEP8 issues
- added a main to test if works (commented out)
"""

from PyQt6.QtWidgets import *
from ui import ui_ABLImMatSalmonSpecialStudiesDlg
from sys import argv


class ABLImMatSalmonSpecialStudiesDlg(QDialog, ui_ABLImMatSalmonSpecialStudiesDlg.Ui_ablimmatsalmonspeciesstudiesDlg):
    def __init__(self,  parent=None):
        super(ABLImMatSalmonSpecialStudiesDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        self.stomach = ''
        self.isotope = ''
        self.thiamine = ''
        self.otolith = ''
        self.sp_st = ''
        self.sp_ot = ''
        self.sp_th = ''
        self.sp_is = ''
        self.result = ()

        # signal/slot connections
        self.otolithBtn.clicked.connect(self.getOtolith)
        self.stomachBtn.clicked.connect(self.getStomach)
        self.isotopeBtn.clicked.connect(self.getIsotope)
        self.thiamineBtn.clicked.connect(self.getNutrition)
        self.doneBtn.clicked.connect(self.Enter)
        self.clearBtn.clicked.connect(self.Clear)

    def setup(self, parent):
        """
        sets the text of all of the buttons and unchecks all of them
        :param parent: not used in this function
        :return: none
        """
        # set text on buttons
        self.stomachBtn.setText('Stomach')
        self.otolithBtn.setText('Otolith')
        self.thiamineBtn.setText('Nutrition')
        self.isotopeBtn.setText('Isotope')

        # uncheck all buttons
        self.stomachBtn.setChecked(False)
        self.otolithBtn.setChecked(False)
        self.thiamineBtn.setChecked(False)
        self.isotopeBtn.setChecked(False)

    def getStomach(self):
        """
        sets the self.stomach and self.sp_st variables and changes the text to 'Collected' for the stomach button
        :return: none
        """
        self.stomach = 'STOM'
        self.stomachBtn.setText('Collected')
        self.sp_st = ','

    def getIsotope(self):
        """
        sets the self.isotope and self.sp_is variables and changes the text to 'Collected' for the isotope button
        :return: none
        """
        self.isotope = 'ISO'
        self.isotopeBtn.setText('Collected')
        self.sp_is = ','

    def getNutrition(self):
        """
        sets the self.thiamine and self.sp_th variables and changes the text to 'Collected' for the thiamine button
        :return: none
        """
        self.thiamine = 'NUT'
        self.thiamineBtn.setText('Collected')
        self.sp_th = ','

    def getOtolith(self):
        """
        sets the self.otolith and self.sp_st variables and changes the text to 'Collected' for the otolith button
        :return: none
        """
        self.otolith = 'OTO'
        self.otolithBtn.setText('Collected')
        self.sp_ot = ','

    def Clear(self):
        """
        'clears' all of the clicks by resetting the variables and the button texts and unchecks the buttons
        :return: none
        """
        # reset the variables
        self.stomach = ''
        self.isotope = ''
        self.thiamine = ''
        self.otolith = ''
        self.sp_st = ''
        self.sp_ot = ''
        self.sp_is = ''
        self.sp_th = ''

        # reset the button text
        self.isotopeBtn.setText('Isotope')
        self.thiamineBtn.setText('Nutrition')
        self.stomachBtn.setText('Stomach')
        self.otolithBtn.setText('Otolith')

        # uncheck all buttons
        self.stomachBtn.setChecked(False)
        self.otolithBtn.setChecked(False)
        self.isotopeBtn.setChecked(False)
        self.thiamineBtn.setChecked(False)

    def Enter(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        self.result = (True, self.stomach + self.sp_st + self.otolith + self.sp_ot + self.thiamine +
                       self.sp_th + self.isotope)

        if self.result[-1] != '':
            if self.result[-1][-1] == ',':
                self.result = (True, self.result[-1][0:-1])
            self.accept()

    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = ABLImMatSalmonSpecialStudiesDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""