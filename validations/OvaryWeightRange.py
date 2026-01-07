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
.. module:: OvaryWeightRange

    :synopsis: OvaryWeightRange checks that the gonadosomatic index is
               less than the maximum percentage configured in CLAMS.
               The gonadosomatic index is gonadosomatic index is the
               calculation of the gonad mass as a proportion of the total
               body mass. It is represented by the formula:
               GSI = [gonad weight / total tissue weight] × 100

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

class OvaryWeightRange(QObject):

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

        #  Get the maxgsi parameter. Since this value applies to all species, we
        #  stuck it in the application_configuration table.
        sql = "SELECT parameter_value FROM " + schema + ".application_configuration WHERE lower(parameter)='maxgsi'"
        query = db.dbQuery(sql)

        #  extract returned results
        maxGSIVal, = query.first()
        self.maxGSI = maxGSIVal


    def validate(self, currentValue, measurements, values):
        '''
            The validate method is called when a measurement is made for a specific
            measurement type. Each measurement can have from 0-N validations. When
            a specific measurement is made, say "barcode", all validations
            assigned to the barcode measurement will have their validate methods
            called. Each one should verify that the currentValue is valid based
            on the logic of each particular validation.

                currentValue - the just measured value
                measurements - a list of the measurement types for this
                    protocol, in order.
                values - a list of the stored values of those measurements.
                    In order of the measurements.

            This validation checks if the gonad weight is less than the max
            weight computed as a percentage of the total specimen weight. It is
            a fairly crude check, but still valuable to ensure wildly inaccurate
            measurements.

            This is a fairly simple example, but the validation can be much
            more complex (but usually don't need to be.) Also, remember that
            these run each time a measurement configured for the validation
            runs so you don't want them to take too long to execute as it
            will slow data collection.

        '''

        #  ensure that the maxGSI value is numeric
        try:
            maxGSIVal = float(self.maxGSI)
        except:
            result = (False, "OvaryWeightRange Validation Error. Non-numeric 'maxGSI' specified " +
                    "in the application_configuration table. The validation cannot run.")
            return result

        #  ensure that our gonad weight is numeric
        try:
            gonadWt = float(currentValue)
        except:
            result = (False, "Non-numeric gonad weight recorded!?! You should re-weigh your gonad.")
            return result

        #  get the measured specimen weight and ensure it is numeric
        fishWt = values[measurements.index('organism_weight')]
        if fishWt is None:
            result = (False, "There's no specimen weight! OvaryWeightRange validation cannot run.")
            return result
        try:
            fishWt = float(fishWt)
        except:
            result = (False, "The specimen has a non-numeric weight. OvaryWeightRange validation cannot run.")
            return result

        #  finally, check that the gonad weight, as a percentage of the total specimen weight, is
        #  less than the max GSI value
        if (gonadWt / fishWt) > (maxGSIVal / 100.0):
            #  weight check failed - weight is outside valid range
            result = (False, "The GSI you've got here is " + str((gonadWt / fishWt) * 100) +
                    ", which is more than the configured maximum of " + str(maxGSIVal) +
                    ". Do you want to re-enter your gonad weight?")
        else:
            #  weight check succeeded - weight is o.k.
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
            currentValue = '.5'
            measureTypes = ['organism_weight']
            values = [5]

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
                self.validation = OvaryWeightRange(db, speciesCode, subcategory)

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


