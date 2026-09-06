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
    :module:: sbeSetLocation

    :synopsis: "This dialog is presented when the user clicks the ""Download""
                button in CLAMSsbeDownloader. This dialog asks the user where
                the SBE was located on the net so that info can be stored in the
                event_data table. Atfter establishing where the SBE was located,
                 the data will then be downloaded from the SBE and inserted into
                 the haul_stream_data table."

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6.QtWidgets import QDialog, QApplication
from ui import ui_sbeSetLocation

class sbeSetLocation(QDialog, ui_sbeSetLocation.Ui_sbeSetLocation):

    def __init__(self, parent=None):
        #  initialize the parents
        super(sbeSetLocation, self).__init__(parent)
        self.setupUi(self)
        self.settings = parent.settings

        #  self.location stores the mounting location
        self.location = None

        #  since there is not a good way to identify specific SBE mounting
        #  location event_parameters, we will hard-code them here. Note that
        #  the values here are used for the combo-box item names and we will
        #  append "SBE" to them to use as the event_parameter value. For example,
        #  'Headrope' will be inserted in event_data as "HeadropeSBE"
        #  If you need to add a new location, it must first be added to the
        #  event_parameters table
        if self.settings['OrganizationName'] == 'NWFSC':
            self.locations = ['Headrope', 'Footrope', 'Camera', 'Other']
        else:
            self.locations = ['Headrope', 'Footrope', 'Camtrawl', 'DropTS', 'Dropcam', 'Other']

        self.cbLocation.addItems(self.locations)

        #  set the combobox initial value - WE WANT IT TO DEFAULT TO HEADROPE
        self.cbLocation.setCurrentIndex(0)

        #  set up signals
        self.pbOK.clicked.connect(self.okClicked)
        self.pbCancel.clicked.connect(self.cancelClicked)


    def okClicked(self):

        self.location = str(self.cbLocation.currentText ()) + 'SBE'
        self.accept()


    def cancelClicked(self):
        self.location = None
        self.accept()


if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)
    form = sbeSetLocation()
    form.show()
    app.exec()
