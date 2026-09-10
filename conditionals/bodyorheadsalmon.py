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
    :module:: BodyOrHeadSalmon

    :synopsis: BodyOrHeadSalmon is a conditional that checks if a body or head should be frozen

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

from PyQt6.QtCore import *

class BodyOrHeadSalmon(QObject):

    def __init__(self, db, schema, speciesCode, parent=None):
        '''
            The init methods of CLAMS conditionals are run whenever a new protocol
            or species is selected in the specimen module. Any setup that the
            conditional requires should be done here. The three input arguments are:

                db - a reference to the active dbConnection class object

            If you need to pass additional data to a validation, you should
            add this data to the species_data table and query it out here in
            the init method (see LengthRange.py for example.)

        '''
        #  call the superclass init
        QObject.__init__(self, None)
        self.cnt = 0;           # initialize the counter


    def evaluate(self,   measurements,  values,  result):
        '''
            The evaluate method is called when a measurement is taken to determine
            what changes in the protocol. Each measurement can have from 0-N validations. When
            a specific measurement is made, say "barcode", all validations
            assigned to the barcode measurement will have their validate methods
            called. Each one should verify that the currentValue is valid based
            on the logic of each particular validation.

                measurements - a list of the measurement types for this
                    protocol, in order.
                values - a list of the stored values of those measurements.
                    In order of the measurements.
                result - a 2-d array (e.g. [[True, False], [False, True], ...]), the
                    first item represents whether a measurement is enabled (True) or disabled (False) and
                    the second item represents whether a measurement is mandatory (True) or optional (False)

            For example, this conditional is for the body count measurement and when
            a count value is logged, it will check to see if that value is greater than 50.

            This is a fairly simple example, but the conditional can be
            more complex (but usually don't need to be.) Also, remember that
            these run each time a measurement configured for the conditional
            runs so you don't want them to take too long to execute as it
            will slow data collection.

        '''
        
        if values[0] is not None:                                 # first reading must be mandatory and completed
            if values.count(None) == len(values)-1:   # all other readings must be None
                self.cnt = self.cnt+1                          # increment the counter
        
		
        if self.cnt < 21:
            try:
                result[measurements.index('fish_head')] = [False]
            except:
                pass
        elif self.cnt > 20 & self.cnt < 51:
            try:
                result[measurements.index('whole_fish')] = [False]
            except:
                pass
        elif self.cnt > 51:
            try:
                result[measurements.index('whole_fish')] = [False]
                result[measurements.index('fish_head')] = [False]
            except:
                pass
                
        return result

'''
The conditionalTest class enables testing of conditionals by creating a database
connection, creating an instance of the conditional object, and then executing its
evaluate method.

This class will need to be customized a bit for each individual validation.
'''
class conditionalTest(QObject):
        def __init__(self):
            super(conditionalTest, self).__init__(None)

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
            measurements = ['whole_fish', 'fish_head']
            values = [1, None, None]
            results = [3, 4]
            db = None
            schema = None
            speciesCode = None
            ok = None

            #  create the validation using an empty db connection
            self.evaluate = BodyOrHeadSalmon(db, schema, speciesCode)

            #  execute the validation 11 times
            for x in range(30):
                ok = self.evaluate.evaluate(measurements, values, results)

            # print the results
            # expected: [False, False]
            print(ok)

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
    form = conditionalTest()

    #  and start the application event loop
    app.exec()



