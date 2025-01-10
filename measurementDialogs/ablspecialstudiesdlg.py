"""
updated December 2024 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- signal/slot connections
- moved variable declarations into __init__
- updated reset value for Isotope_Marsh button from Honeyfield to Isotope_Marsh
- added some function explanation
- fixed any PEP8 issues
- added a main to test if works (commented out)
"""

from PyQt6.QtWidgets import *
from ui import ui_ABLSpecialStudiesDlg
from sys import argv


class ABLSpecialStudiesDlg(QDialog, ui_ABLSpecialStudiesDlg.Ui_ablspeciesstudiesDlg):
    def __init__(self,  parent=None):
        super(ABLSpecialStudiesDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        self.stomach = ''
        self.isotopeMarsh = ''
        self.isotopeAndrews = ''
        self.genetics = ''
        self.otolith = ''
        self.energetic = ''
        self.tsmri = ''
        self.sp_st = ''
        self.sp_ot = ''
        self.sp_ge = ''
        self.sp_isM = ''
        self.sp_isA = ''
        self.sp_en = ''
        self.sp_ts = ''
        self.result = ()

        # signal/slot connections
        self.otolithBtn.clicked.connect(self.getOtolith)
        self.stomachBtn.clicked.connect(self.getStomach)
        self.isotopeMarshBtn.clicked.connect(self.getIsotopeM)
        self.isotopeAndrewsBtn.clicked.connect(self.getIsotopeA)
        self.geneticsBtn.clicked.connect(self.getGenetics)
        self.energeticBtn.clicked.connect(self.getEnergetic)
        self.tsmriBtn.clicked.connect(self.getTSMRI)
        self.doneBtn.clicked.connect(self.Enter)
        self.clearBtn.clicked.connect(self.Clear)

    def setup(self, parent):
        """
        sets the text of all of the buttons and unchecks all of them
        :param parent: not used in this function
        :return: none
        """
        # set button texts
        self.stomachBtn.setText('Stomach')
        self.otolithBtn.setText('Otolith')
        self.geneticsBtn.setText('Genetics')
        self.isotopeMarshBtn.setText('Honeyfield')
        self.isotopeAndrewsBtn.setText('Isotope_Andrews')
        self.energeticBtn.setText('Energetics')
        self.tsmriBtn.setText('TSMRI')

        # uncheck all buttons
        self.stomachBtn.setChecked(False)
        self.otolithBtn.setChecked(False)
        self.geneticsBtn.setChecked(False)
        self.isotopeMarshBtn.setChecked(False)
        self.isotopeAndrewsBtn.setChecked(False)
        self.energeticBtn.setChecked(False)
        self.tsmriBtn.setChecked(False)

    def getStomach(self):
        """
        sets the self.stomach and self.sp_st variables and changes the text to 'Collected' for the stomach button
        :return: none
        """
        self.stomach = 'STOM'
        self.stomachBtn.setText('Collected')
        self.sp_st = ','

    def getIsotopeM(self):
        """
        sets the self.isotopeMarsh and self.sp_isM variables and changes the text to 'Collected' for the
        Isotope_Marsh button
        :return: none
        """
        self.isotopeMarsh = 'Honeyfield'
        self.isotopeMarshBtn.setText('Collected')
        self.sp_isM = ','

    def getIsotopeA(self):
        """
        sets the self.isotopeAndrews and self.sp_isA variables and changes the text to 'Collected' for the
        Isotope_Andrews button
        :return: none
        """
        self.isotopeAndrews = 'ISO_Andrews'
        self.isotopeAndrewsBtn.setText('Collected')
        self.sp_isA = ','

    def getOtolith(self):
        """
        sets the self.otolith and self.sp_ot variables and changes the text to 'Collected' for the otolith button
        :return: none
        """
        self.otolith = 'OTO'
        self.otolithBtn.setText('Collected')
        self.sp_ot = ','

    def getGenetics(self):
        """
        sets the self.genetics and self.sp_ge variables and changes the text to 'Collected' for the genetics button
        :return: none
        """
        self.genetics = 'GEN'
        self.geneticsBtn.setText('Collected')
        self.sp_ge = ','

    def getTSMRI(self):
        """
        sets the self.tsmri and self.sp_ts variables and changes the text to 'Collected' for the tsmri button
        :return: none
        """
        self.tsmri = 'TSMRI'
        self.tsmriBtn.setText('Collected')
        self.sp_ts = ','

    def getEnergetic(self):
        """
        sets the self.energetic and self.sp_en variables and changes the text to 'Collected' for the
        energetics button
        :return: none
        """
        self.energetic = 'ENRG'
        self.energeticBtn.setText('Collected')
        self.sp_en = ','

    def Clear(self):
        """
        'clears' all of the clicks by resetting the variables and the button texts and unchecks the buttons
        :return: none
        """
        # reset variables
        self.stomach = ''
        self.isotopeMarsh = ''
        self.isotopeAndrews = ''
        self.genetics = ''
        self.energetic = ''
        self.otolith = ''
        self.tsmri = ''
        self.sp_st = ''
        self.sp_ot = ''
        self.sp_ge = ''
        self.sp_isM = ''
        self.sp_isA = ''
        self.sp_en = ''
        self.sp_ts = ''

        # reset button text
        self.isotopeMarshBtn.setText('Isotope_Marsh')
        self.isotopeAndrewsBtn.setText('Isotope_Andrews')
        self.stomachBtn.setText('Stomach')
        self.otolithBtn.setText('Otolith')
        self.geneticsBtn.setText('Genetics')
        self.energeticBtn.setText('Energetics')
        self.tsmriBtn.setText('TSMRI')

        # uncheck buttons
        self.stomachBtn.setChecked(False)
        self.otolithBtn.setChecked(False)
        self.geneticsBtn.setChecked(False)
        self.energeticBtn.setChecked(False)
        self.isotopeMarshBtn.setChecked(False)
        self.isotopeAndrewsBtn.setChecked(False)
        self.tsmriBtn.setChecked(False)

    def Enter(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        self.result = (True, self.tsmri + self.sp_ts + self.stomach + self.sp_st + self.otolith + self.sp_ot +
                       self.genetics + self.sp_ge + self.energetic + self.sp_en + self.isotopeMarsh +
                       self.sp_isM + self.isotopeAndrews)

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
    form = ABLSpecialStudiesDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""