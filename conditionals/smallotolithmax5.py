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
    :module:: SmallOtolithMax5

    :synopsis: SmallOtolithMax5 a conditional that checks if a fish is smaller than 
    a threshold then counts the number of small otoliths taken, after 5, otolith protocol stops

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Southwest Fisheries Science Center (SWFSC)
| Fisheries Resources Division (FRD)
|
| Author:
        Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Kelsey James <kelsey.james@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""
import unittest
from unittest.mock import Mock
from PyQt6.QtCore import *


class SmallOtolithMax5(QObject):

    def __init__(self, db, schema, speciesCode, parent=None):
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
        self.activeSample = parent.activeSample
        self.schema = schema
        self.db = db

        #  Get the large length for this species from the species_data table
        sql = ("SELECT parameter_value FROM " + schema + ".species_data WHERE species_code=" + speciesCode +
               " AND lower(species_parameter)='small_length'")
        query = db.dbQuery(sql)
        smallLength, = query.first()
        #  extract returned results
        self.smallLength=smallLength


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

        '''
        lengthIndex = [i for i, s in enumerate(measurements) if "length" in s]
        lengthFieldName = measurements[lengthIndex[0]]
        length = values[lengthIndex[0]]

        # Counts the number of otoliths taken from a small specimen
        smallOtoCount = None
        if self.activeSample and self.smallLength:
            sql = ("SELECT count(*) FROM " + self.schema + ".measurements WHERE measurement_type='alpha_barcode' " +
                "AND specimen_id in (SELECT specimen_id FROM " + self.schema + ".measurements WHERE " +
                "measurement_type='" + lengthFieldName + "' AND cast(measurement_value as float) < " + 
                self.smallLength + " AND sample_id=" + self.activeSample + ")")
            query = self.db.dbQuery(sql)
            smallOtoCount, = query.first()

        if self.smallLength and smallOtoCount and length:
            self.smallLength = float(self.smallLength)
            smallOtoCount = int(smallOtoCount)
            length = float(length)

            # check if the length is larger than the species 'largeLength', if yes, Otolith barcode is mandatory
            if length < self.smallLength and smallOtoCount >= 5:
                try:
                    result[measurements.index('alpha_barcode')]=[False, False]
                except:
                    pass

        return result
       
'''
The conditionalTest class enables testing of conditionals by creating a database
connection, creating an instance of the conditional object, and then executing its
evaluate method.

This class will need to be customized a bit for each individual validation.
'''

class conditionalTest(unittest.TestCase):
    schema = 'clams2swfsc'
    speciesCode = 'anch'

    parent = Mock()
    parent.activeSample = '1'

    anchovyMeasurements = ['standard_length_mm', 'weight_g', 'dna_barcode', 'alpha_barcode']
    mackerelMeasurements = ['fork_length_mm', 'weight_g', 'alpha_barcode']

    def testSmallAnchovyGreaterThan5(self):
        query = Mock()
        query.first.side_effect = [['60'], ['6']]
        db = Mock()
        db.dbQuery.return_value = query

        smallOtolith = SmallOtolithMax5(db, self.schema, self.speciesCode, self.parent)

        values = ['2', '14', 'asdf', 'asdf']
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = smallOtolith.evaluate(self.anchovyMeasurements, values, results)
        
        self.assertEqual([[True, False], [True, False], [True, False], [False, False]], ok)
    
    def testSmallAnchovyLessThan5(self):
        query = Mock()
        query.first.side_effect = [['60'], ['4']]
        db = Mock()
        db.dbQuery.return_value = query

        smallOtolith = SmallOtolithMax5(db, self.schema, self.speciesCode, self.parent)

        values = ['2', '14', 'asdf', 'asdf']
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = smallOtolith.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [True, False], [True, False]], ok)
    
    def testSmallMackerelGreaterThan5(self):
        query = Mock()
        query.first.side_effect = [['150'], ['5']]
        db = Mock()
        db.dbQuery.return_value = query

        smallOtolith = SmallOtolithMax5(db, self.schema, self.speciesCode, self.parent)

        values = ['100', '20', 'asdf']
        results = [[True, False], [True, False], [True, False]]
        ok = smallOtolith.evaluate(self.mackerelMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [False, False]], ok)

    def testLargeMackerelLessThan5(self):
            query = Mock()
            query.first.side_effect = [['150'], ['1']]

            db = Mock()
            db.dbQuery.return_value = query

            smallOtolith = SmallOtolithMax5(db, self.schema, self.speciesCode, self.parent)

            values = ['200', '20', 'asdf']
            results = [[True, False], [True, False], [True, False]]
            ok = smallOtolith.evaluate(self.mackerelMeasurements, values, results)

            self.assertEqual([[True, False], [True, False], [True, False]], ok)

    def testSmallMackerelLessThan5(self):
            query = Mock()
            query.first.side_effect = [['150'], ['1']]

            db = Mock()
            db.dbQuery.return_value = query

            smallOtolith = SmallOtolithMax5(db, self.schema, self.speciesCode, self.parent)

            values = ['50', '20', 'asdf']
            results = [[True, False], [True, False], [True, False]]
            ok = smallOtolith.evaluate(self.mackerelMeasurements, values, results)

            self.assertEqual([[True, False], [True, False], [True, False]], ok)

if __name__ == '__main__':
    unittest.main()

