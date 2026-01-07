# coding=utf-8

#     National Oceanic and Atmospheric Administration (NOAA)
#     Alaskan Fisheries Science Center (AFSC)
#     Resource Assessment and Conservation Engineering (RACE)
#     Midwater Assessment and Conservation Engineering (MACE)

#  THIS SOFTWARE AND ITS DOCUMENTATION ARE CONSIDERED TO BE IN THE PUBLIC DOMAIN
#  AND THUS ARE AVAILABLE FOR UNRESTRICTED PUBLIC USE. THEY ARE FURNISHED "AS
#  IS."  THE AUTHORS, THE UNITED STATES GOVERNMENT, ITS INSTRUMENTALITIES,
#  OFFICERS, EMPLOYEES, AND AGENTS MAKE NO WARRANTY, EXPRESS OR IMPLIED,
#  AS TO THE USEFULNESS OF THE SOFTWARE AND DOCUMENTATION FOR ANY PURPOSE.
#  THEY ASSUME NO RESPONSIBILITY (1) FOR THE USE OF THE SOFTWARE AND
#  DOCUMENTATION; OR (2) TO PROVIDE TECHNICAL SUPPORT TO USERS.

"""
.. module:: SWFSCFinClipDNA

    :synopsis: Dialog which presents Yes/No buttons for collecting
               a DNA finclip. It also generates a finclip vial "number"
               in the form YYCCVVNNN where:

                YY is the 2 digit year (from current survey value)
                CC is the 2 digit cruise number (from current survey value)
                VV is the vessel code (from ships table)
                NNN is the zero padded finclip number

              example: 2506SH001

              It creates the "new" finclip vial number by doing a max
              'dna_finclip_number' + 1 for the current ship+survey. It will
              perform a uniqueness check prior to closing as a simple
              mechanism to ensure two simultaneous users don't insert the
              same number.


| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
|
"""

from PyQt6.QtWidgets import *
from ui import ui_SWFSCFinClipDNADlg


class SWFSCFinClipDNADlg(QDialog, ui_SWFSCFinClipDNADlg.Ui_SWFSCFinClipDNADlg):
    def __init__(self,  parent=None):
        super(SWFSCFinClipDNADlg, self).__init__(parent)
        self.setupUi(self)

        # variable declaration
        self.result = ()

        #  copy the bits we need
        self.db = parent.db
        self.schema = parent.schema
        self.survey=parent.survey
        self.ship=parent.ship
        self.numpad = parent.numpad
        self.message = parent.message
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds

        #  connect signals
        self.yesBtn.clicked.connect(self.getResponse)
        self.noBtn.clicked.connect(self.getResponse)
        self.vialNumberBtn.clicked.connect(self.editVialNum)


    def editVialNum(self):
        '''
        editVialNum is called when someone clicks on the vial number in the
        dialog. It will present the numpad and allow them to enter a new
        numeric value (the last element if the combined vial number.)

        A new combined vial number will be created using the number that
        is entered.
        '''

        self.numpad.msgLabel.setText("Edit vial number")
        if not self.numpad.exec():
            #  user cancelled action
            return

        try:
            thisNum = float(self.numpad.value)

            #  get the next full vial number using the new number just selected
            thisVialNumber = self.getVialNumber(thisNum)

            #  update the UI
            self.vialNumberBtn.setText(thisVialNumber)
        except:
            pass


    def getNextNumber(self):
        '''
        getNextNumber will get the next available vial number by querying the
        existing numbers and invrementing by one
        '''
        #  first, query the last vial number and generate the next one in the
        #  series.
        sql = ("SELECT measurement_value FROM " + self.schema + ".measurements WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND measurement_type='dna_finclip_number' " +
                "AND measurement_value <> 'None' ORDER BY measurement_value DESC")
        query = self.db.dbQuery(sql)
        lastVialNum, = query.first()

        #  wrap this in a try block to handle the first number (when lastVialNum == None)
        #  This will also catch malformed numbers and will return 1 in those cases too.
        try:
            lastVialNum = float(lastVialNum[-3:])
            thisNum = lastVialNum + 1
        except:
            thisNum = 1

        return thisNum


    def getVialNumber(self, thisNum):
        '''
        getVialNumber will get the next full vial number, including the survey
        and vessel code business.
        '''

        #  get the vessel code
        sql = ("SELECT vessel_code FROM " + self.schema + ".ships WHERE ship=" + self.ship)
        query = self.db.dbQuery(sql)
        vesselCode, = query.first()

        if vesselCode is None:
            vesselCode = ''

        #  finally build the new number in the form YYCCVVNNN where:
        #    YY is the 2 digit year (from current survey value)
        #    CC is the 2 digit cruise number (from current survey value)
        #    VV is the vessel code (from ships table)
        #    NNN is the zero padded finclip number
        if thisNum < 999:
            thisVialNumber = self.survey[-4:] + vesselCode + "%03i" % thisNum
        else:
            #  just in case, format numbers > 999
            thisVialNumber = self.survey[-4:] + vesselCode + "%04i" % thisNum

        return thisVialNumber


    def setup(self, parent):
        """
        For the SWFSCFinClipDNA, we need to get the next vial number

        """

        #  get the number for this vial
        thisNum = self.getNextNumber()

        #  get the next full vial number (includes the survey and vessel stuff)
        thisVialNumber = self.getVialNumber(thisNum)

        #  update the UI
        self.vialNumberBtn.setText(thisVialNumber)


    def setCaption(self, text):
        """
        sets the message label to the passed text
        :param text: text to set label to
        :return: none
        """
        self.msgLabel.setText(text)


    def checkUniqueVialNumber(self, vialNum):
        '''
        checkUniqueVialNumber checks if the provided vial number exists in the
        current ship+survey. Returns True if so, False if not.
        '''
        sql = ("SELECT measurement_value FROM measurements WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND measurement_type='dna_finclip_number' " +
                "AND measurement_value='" + vialNum + "'")
        query = self.db.dbQuery(sql)
        hasThisVial, = query.first()

        if hasThisVial is None:
            return True
        else:
            return False


    def getResponse(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """

        #  if the user is taking a fin clip, check to make sure our number is unique
        if self.sender().text().lower() == "yes":
            unique = self.checkUniqueVialNumber(self.vialNumberBtn.text())
            if not unique:
                #  it is not unique - let them know
                msgText = ("The current vial number is no longer unique. A new one will be generated. " +
                        "Please try again.")
                self.message.setMessage(self.errorIcons[2],self.errorSounds[2], msgText, 'info')
                self.message.exec()

                #  now try to generate a new, unique number
                self.setup(None)
                return

            result = self.vialNumberBtn.text()
        else:
            result = "None"

        #  return the result
        self.result = (True, result)
        self.accept()


    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, None)
        self.reject()



