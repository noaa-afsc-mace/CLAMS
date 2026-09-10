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
    :module:: SexCheck

    :synopsis: SexChecks checks to see if a sex has been entered

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
| Created by:
|       Alicia Billings <alicia.billings@noaa.gov>
"""

from PyQt6.QtCore import *

class SexCheck(QObject):
    def __init__(self, db, schema, activeSpcCode, parent=None):
        #  call the superclass init
        QObject.__init__(self, None)
        self.db = db
        self.schema = schema
        self.activeSpcCode = activeSpcCode

    def evaluate(self, measurements, values, result):
        """
        checks to see if there is a sex entered, and if not, disable the gonad and liver buttons
        :param measurements: available measurements for the specimen
        :param values: collected values for the specimen
        :param result: list of the measurement types and whether their buttons should be enabled
        :return: return the result list with any changes
        """
        # get the current sex
        try:
            cur_sex = values[measurements.index('sex')]
        except:
            cur_sex = None
        try:
            cur_barcode = values[measurements.index('barcode')]
        except:
            cur_barcode = None

        columns_to_disable = ['gonad_collection', 'luck_meas']

        is_female_with_barcode = bool(
            cur_sex and
            cur_sex.lower() == 'female' and
            cur_barcode is not None
        )
        target_state = [is_female_with_barcode, False]

        for col in columns_to_disable:
            try:
                idx = measurements.index(col)
                result[idx] = target_state
            except ValueError:
                pass

        return result
