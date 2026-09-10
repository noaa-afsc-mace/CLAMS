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
    :module:: DNABoundaries

    :synopsis: DNABoundaries is a conditional that counts the number of DNA
    samples (measurement_type = dna_barcode) taken within the same geographic
    area as the current specimen. Geographic zones are defined by boundary
    latitudes stored in species_data. When the count in a zone reaches 50 the
    dna_barcode measurement button is disabled.

    The latitude of the current haul is read from the event_data table
    (event_parameter = 'LatitudeHB'). Boundary parameters whose names begin
    with 'Boundary_' are read from species_data, sorted by value, and used to
    derive the zone that contains the haul latitude.

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Southwest Fisheries Science Center (SWFSC)
| Fisheries Resources Division (FRD)
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
"""
import unittest
from unittest.mock import Mock
from PyQt6.QtCore import *


class DNABoundaries(QObject):

    def __init__(self, db, schema, speciesCode, parent=None):
        '''
        The init methods of CLAMS conditionals are run whenever a new protocol
        or species is selected in the specimen module. Any setup that the
        conditional requires should be done here. The three input arguments are:

            db - a reference to the active dbConnection class object
            schema - the database schema name
            speciesCode - the species code of the current specimen
            parent - a reference to the parent CLAMSspecimen object

        Geographic boundary latitudes are loaded from the species_data table
        (species_parameter values beginning with 'Boundary_'). The haul-back
        latitude for the current event is read from event_data
        (event_parameter = 'LatitudeHB') and used to determine which zone the
        specimen belongs to.
        '''

        #  call the superclass init
        QObject.__init__(self, None)
        self.db = db
        self.schema = schema
        self.ship = parent.ship
        self.survey = parent.survey
        self.activeHaul = parent.activeHaul

        #  Initialize zone bounds to None; set below if a zone can be determined
        self.lowerBound = None
        self.upperBound = None

        #  Query all boundary parameters for this species, sorted by latitude
        sql = ("SELECT species_parameter, parameter_value FROM " + schema +
               ".species_data WHERE species_code=" + speciesCode +
               " AND lower(species_parameter) LIKE 'boundary_%'" +
               " ORDER BY cast(parameter_value AS float)")
        query = db.dbQuery(sql)

        #  Build a sorted list of boundary latitude values
        boundaries = []
        for _param, value in query:
            if value is not None:
                boundaries.append(float(value))

        #  Look up the haul-back latitude of the current event
        sql = ("SELECT parameter_value FROM " + schema + ".event_data WHERE ship=" +
               self.ship + " AND survey=" + self.survey + " AND event_id=" +
               self.activeHaul + " AND event_parameter='LatitudeHB'")
        query = db.dbQuery(sql)
        latitude, = query.first()

        #  Determine which zone the current haul latitude falls in
        if latitude is not None and len(boundaries) >= 2:
            latitude = float(latitude)
            for i in range(len(boundaries) - 1):
                if boundaries[i] <= latitude < boundaries[i + 1]:
                    self.lowerBound = boundaries[i]
                    self.upperBound = boundaries[i + 1]
                    break


    def evaluate(self, measurements, values, result):
        '''
        The evaluate method is called when a measurement is taken to determine
        what changes in the protocol. Each measurement can have from 0-N
        conditionals.

            measurements - a list of the measurement types for this
                protocol, in order.
            values - a list of the stored values of those measurements,
                in order.
            result - a 2-d array (e.g. [[True, False], [False, True], ...]),
                the first item represents whether a measurement is enabled
                (True) or disabled (False) and the second item represents
                whether a measurement is mandatory (True) or optional (False).

        When the count of dna_barcode measurements taken in events whose
        haul-back latitude falls within the same geographic zone as the current
        event reaches 50, the dna_barcode button is disabled.
        '''

        if self.lowerBound is None or self.upperBound is None:
            return result

        #  Count DNA samples taken in events within the same geographic zone
        sql = ("SELECT count(*) FROM " + self.schema +
               ".measurements WHERE measurement_type='dna_barcode'" +
               " AND event_id IN" +
               " (SELECT event_id FROM " + self.schema + ".event_data" +
               " WHERE ship=" + self.ship +
               " AND survey=" + self.survey +
               " AND event_parameter='LatitudeHB'" +
               " AND cast(parameter_value AS float) >= " + str(self.lowerBound) +
               " AND cast(parameter_value AS float) < " + str(self.upperBound) + ")")
        query = self.db.dbQuery(sql)
        dnaCount, = query.first()

        if values[measurements.index('dna_barcode')] is None and dnaCount is not None and int(dnaCount) >= 50:
            try:
                result[measurements.index('dna_barcode')] = [False, False]
            except (ValueError, IndexError):
                pass

        return result


'''
The conditionalTest class enables testing of conditionals by creating a
mock database, creating an instance of the conditional object, and then
executing its evaluate method.
'''

class conditionalTest(unittest.TestCase):
    schema = 'clams2swfsc'
    speciesCode = '20610'

    parent = Mock()
    parent.activeSample = '1'
    parent.activeHaul = '100'
    parent.ship = '1'
    parent.survey = '123'

    anchovyMeasurements = ['standard_length_mm', 'weight_g', 'dna_barcode', 'alpha_barcode']

    #  Boundary values from species_data, sorted by latitude
    boundaryRows = [
        ['Boundary_Mexico', '32.0'],
        ['Boundary_PtConception', '34.5'],
        ['Boundary_SanFrancisco', '37.75'],
        ['Boundary_CapeMendocino', '40.383'],
        ['Boundary_ColumbiaRiver', '46.233'],
        ['Boundary_Canada', '49.0'],
    ]

    def _make_db(self, latitude, dnaCount):
        '''Helper to create a mock db returning the given haul latitude and
        DNA barcode count.'''
        boundaryQuery = Mock()
        boundaryQuery.__iter__ = Mock(return_value=iter(self.boundaryRows))

        latQuery = Mock()
        latQuery.first.return_value = [latitude]

        countQuery = Mock()
        countQuery.first.return_value = [str(dnaCount)]

        db = Mock()
        db.dbQuery.side_effect = [boundaryQuery, latQuery, countQuery]
        return db

    def testDNACountAt50DisablesButton(self):
        '''When exactly 50 DNA samples have been taken in the zone,
        the dna_barcode button must be disabled.'''
        db = self._make_db('33.0', 50)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        values = ['120', '14', 'asdf', 'asdf']
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [False, False], [True, False]], ok)

    def testDNACountBelow50LeavesButtonEnabled(self):
        '''When fewer than 50 DNA samples have been taken in the zone,
        the dna_barcode button must remain enabled.'''
        db = self._make_db('33.0', 49)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        values = ['120', '14', None, 'asdf']
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [True, False], [True, False]], ok)

    def testDNACountAbove50DisablesButton(self):
        '''When more than 50 DNA samples have been taken in the zone,
        the dna_barcode button must be disabled.'''
        db = self._make_db('40.5', 51)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        values = ['100', '10', None, None]
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [False, False], [True, False]], ok)

    def testLatitudeAtLowerBoundaryIncludedInZone(self):
        '''A latitude exactly on a lower boundary must be included in that zone
        (>= lower, < upper).'''
        db = self._make_db('34.5', 50)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        self.assertEqual(conditional.lowerBound, 34.5)
        self.assertEqual(conditional.upperBound, 37.75)

        values = ['130', '18', None, None]
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [False, False], [True, False]], ok)

    def testLatitudeOutsideBoundariesNeverDisables(self):
        '''A latitude outside all defined boundaries must not disable any button.'''
        db = self._make_db('25.0', 50)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        self.assertIsNone(conditional.lowerBound)
        self.assertIsNone(conditional.upperBound)

        values = ['100', '10', None, None]
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [True, False], [True, False]], ok)

    def testNoLatitudeAvailableNeverDisables(self):
        '''When no latitude is stored for the event, no button must be disabled.'''
        db = self._make_db(None, 50)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        self.assertIsNone(conditional.lowerBound)
        self.assertIsNone(conditional.upperBound)

        values = ['100', '10', None, None]
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [True, False], [True, False]], ok)

    def testDifferentZonesAreIndependent(self):
        '''A haul in a different zone (ColumbiaRiver–Canada) with 50 samples
        must disable the button only for that zone.  The _make_db helper
        creates a fresh mock for each call so zone boundaries are resolved
        independently.'''
        db = self._make_db('47.0', 50)
        conditional = DNABoundaries(db, self.schema, self.speciesCode, self.parent)

        self.assertEqual(conditional.lowerBound, 46.233)
        self.assertEqual(conditional.upperBound, 49.0)

        values = ['110', '15', None, None]
        results = [[True, False], [True, False], [True, False], [True, False]]
        ok = conditional.evaluate(self.anchovyMeasurements, values, results)

        self.assertEqual([[True, False], [True, False], [False, False], [True, False]], ok)


if __name__ == '__main__':
    unittest.main()
