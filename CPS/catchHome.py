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
.. module:: catchHome

    :synopsis: catchHome is a dialog that allows user to select between
                sorted and unsorted catch data entry.

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from ui import ui_CPSCatchHome
import CPS.unsortedCatch as unsortedCatch
import CPS.sortedCatch as sortedCatch

class catchHome(QDialog, ui_CPSCatchHome.Ui_CPSCatchHome):

    def __init__(self, parent=None):
        super(catchHome, self).__init__(parent)
        self.setupUi(self)

        self.db = parent.db
        self.sensorMonitor = parent.sensorMonitor
        self.workStation = parent.workStation
        self.activeHaul = parent.activeHaul
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.activePartition = parent.activePartition
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.scientist = parent.scientist
        self.deviceData = parent.deviceData
        self.schema = parent.schema

        #  set the event number
        self.haulNum.setText(self.activeHaul)

        #  set up some colors
        self.black = QPalette()
        self.black.setColor(QPalette.ColorRole.ButtonText,QColor(0, 0, 0))

        # set up button colors
        self.unsortedBtn.setPalette(self.black)
        self.sortedBtn.setPalette(self.black)
        self.unsortedBtn.setEnabled(True)
        self.sortedBtn.setEnabled(True)

        # set up signals and slots
        self.unsortedBtn.clicked.connect(self.getUnsorted)
        self.sortedBtn.clicked.connect(self.getSorted)
        self.doneBtn.clicked.connect(self.closeHome)

        # if haul is small and only sorted info has been entered
        # disabled unsorted button.
        sql = ("SELECT count(*) FROM " + self.schema + ".samples" + 
               " WHERE ship="+self.ship+
               " AND survey="+self.survey+
               " AND event_id="+self.activeHaul +
               " AND sample_type in ('SortingTable')")
        sortingPresent, = self.db.dbQuery(sql).first()

        sql = ("SELECT count(*) FROM " + self.schema + ".samples" + 
               " WHERE ship="+self.ship+
               " AND survey="+self.survey+
               " AND event_id="+self.activeHaul +
               " AND sample_type in ('WholeHaul')")
        wholeHaulPresent, = self.db.dbQuery(sql).first()

        if int(sortingPresent) == 1 and int(wholeHaulPresent) == 0:
            self.unsortedBtn.setEnabled(False)

    def getUnsorted(self):
        #  show the catch form
        self.close()
        unsorted = unsortedCatch.unsortedCatch(self)
        unsorted.exec()

    def getSorted(self):
        #  show the catch form
        self.close()
        catchWindow = sortedCatch.sortedCatch(self)
        catchWindow.exec()
    
    def closeHome(self):
        #  close the dialog
        self.reject()
