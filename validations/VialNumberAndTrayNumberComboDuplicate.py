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
.. module:: VialNumberAndTrayNumberComboDuplicate

    :synopsis: VialNumberAndTrayNumberComboDuplicate determines whether the combo of vial number and tray number has already been used
               given survey number tray number and vial number. If a combo usage already
               exists, return false with an informational string otherwise
               return true.

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
"""

from PyQt6.QtCore import *

class VialNumberAndTrayNumberComboDuplicate(QObject):

    def __init__(self, db, schema, speciesCode,  subcategory='None'):
        '''
            The init methods of CLAMS validations are run whenever a new protocol
            or species is selected in the specimen module. Any setup that the
            validation requires should be done here. The three input arguments are:

                db - a reference to the active dbConnection class object
                speciesCode - the species code of the current specimen
                subcategory - the subcategory of the current specimen

            If you need to pass additional data to a validation, you should
            add this data to the species_data table and query it out here in
            the init method (see LengthRange.py for example.)

        '''

        #  call the superclass init
        QObject.__init__(self, None)

        #  store a reference to our db object
        self.db = db
        self.schema = schema

        #  get the active survey ID
        sql = "SELECT parameter_value FROM " + schema + ".application_configuration WHERE parameter = 'ActiveSurvey'"
        query = self.db.dbQuery(sql)
        self.survey, = query.first()


    def validate(self,  currentValue,  measurements,  values):
        '''
            The validate method is called when a measurement is made for a specific
            measurement type. Each measurement can have from 0-N validations. When
            a specific measurement is made, say "barcode", all validations
            assigned to the barcode measurement will have their validate methods
            called. Each one should verify that the currentValue is valid based
            on the logic of each particular validation.

                currentValue - vial number
                measurements - a list of the measurement types for this
                    protocol, in order.
                values - a list of the stored values of those measurements.
                    In order of the measurements.

            This validation checks the current vial number against the vial
            numbers in the database FOR THE ACTIVE SURVEY.

            This is a fairly simple example, but the validation can be much
            more complex (but usually don't need to be.) Also, remember that
            these run each time a measurement configured for the validation
            runs so you don't want them to take too long to execute as it
            will slow data collection.

        '''
        index = measurements.index('dna_tray_number')
        trayNumber = values[index]

        sql = ("SELECT s.specimen_id, dna_tray_number.measurement_value as dna_tray_number, dna_vial_number.measurement_value as dna_vial_number, dna_vial_number.survey as survey" +
        " from (select distinct specimen_id from " + self.schema + ".measurements) s" +
        " left outer join " + self.schema + ".measurements dna_tray_number on s.specimen_id = dna_tray_number.specimen_id AND dna_tray_number.measurement_type = 'dna_tray_number'" +
        " left outer join " + self.schema + ".measurements dna_vial_number on s.specimen_id = dna_vial_number.specimen_id AND dna_vial_number.measurement_type = 'dna_vial_number'" +
        " where dna_vial_number.survey ='" + self.survey +
        "' and dna_tray_number.measurement_value = '" + trayNumber +
        "' and dna_vial_number.measurement_value = '" + currentValue + "'")

        query = self.db.dbQuery(sql)
        val = query.first()
        if val[0] is not None:
            #  Vial and Tray number combo already exists
            result = ('invalid', "This tray number and vial number combo already exists in the database for " +
                    "this survey.  Entering a duplicate of the combo is not allowed")
        else:
            # New vial number entered, success
            result = (True, '')

        return result


'''
The validationTest class enables testing of validations by creating a database
connection, creating an instance of the validation object, and then executing its
validate method.

This class will need to be customized a bit for each individual validation.
'''
class validationTest(QObject):
        def __init__(self):
            super(validationTest, self).__init__(None)

            #  we use a timer here to add runTest to the event processing queue and
            #  then exit the init. Execution will return to main, where the
            #  application event loop will be started by the call to app.exec() which
            #  will then start processing events on the queue which will then execute
            #  runTest with the event loop running.
            startTimer = QTimer(self)
            startTimer.timeout.connect(self.runTest)
            startTimer.setSingleShot(True)
            startTimer.start(0)


        def runTest(self):
            '''runTest attempts to create a database connection by presenting a dialog
            requesting credentials. If successful, it instantiates the validation and
            runs the validate method of said validation. You should set up any
            specific parameters required for this validation's test here.
            '''

            #  set up the required parameters for this test
            speciesCode = 21740
            subcategory = 'None'
            currentValue = '1'
            measureTypes = ['dna_tray_number']
            values = [1]

            #  create a connection dialog to get connection params - by default
            #  this will create a dbConnection object and store it in the "db"
            #  attribute.
            conenctionDialog = connectdlg.ConnectDlg(None, None, None)
            ok = conenctionDialog.exec()

            #  if we've connected to the database, create and run the validation
            if ok:
                db = conenctionDialog.db

                #  create the validation using the db connection and specified species
                #  and subcategory.
                self.validation = VialNumberAndTrayNumberComboDuplicate(db, speciesCode, subcategory)

                #  execute the validation
                ok = self.validation.validate(currentValue, measureTypes, values)

                #  print the results
                print(ok)

            else:
                print("Unable to connect to the database")

            #  exit the application
            QApplication.instance().quit()


if __name__ == '__main__':
    #  import test specific libraries
    import sys
    from pathlib import Path
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtWidgets import *

    file = Path(__file__).resolve()
    sys.path.append(str(file.parents[1]))
    import connectdlg

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  instantiate the test
    form = validationTest()

    #  and start the application event loop
    app.exec()


