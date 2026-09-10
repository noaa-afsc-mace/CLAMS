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
    :module:: DietCheck

    :synopsis: DietCheck grabs the number of collected and called stomachs for the tow
                    and disables the button if the max has been hit

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


class DietCheck(QObject):

    def __init__(self, db, schema, activeSpcCode, parent=None):
        #  call the superclass init
        QObject.__init__(self, None)
        self.db = db
        self.schema = schema
        self.activeSpcCode = activeSpcCode
        self.settings = parent.settings

        self.cur_tow = None

        self.tot_collect = 0
        self.tot_called = 0
        self.collected = 0
        self.called = 0

    def evaluate(self, measurements, values, result):
        """
        checks to see if the diets are already collected
        :param measurements: available measurements for the specimen
        :param values: collected values for the specimen; not used in this conditional
        :param result: list of the measurement types and whether their buttons should be enabled
        :return: return the result list with any changes
        """
        # get current tow
        tow_sql = (f"SELECT parameter_value FROM {self.schema}.application_configuration "
                   f"WHERE parameter = 'ActiveEvent'")
        tow_query = self.db.dbQuery(tow_sql)
        self.cur_tow = tow_query.first()[0]

        # get the total collected allowed
        coll_allow_sql = (f"SELECT parameter_value FROM {self.schema}.application_configuration "
                          f"WHERE parameter = 'CollectedDietLimit'")
        coll_allow_query = self.db.dbQuery(coll_allow_sql)
        coll_val = coll_allow_query.first()[0]
        if coll_val:
            self.tot_collect = int(coll_val)
        else:
            self.tot_collect = 5

        # get the total called allowed
        call_allow_sql = (f"SELECT parameter_value FROM {self.schema}.application_configuration "
                          f"WHERE parameter = 'CalledDietLimit'")
        call_allow_query = self.db.dbQuery(call_allow_sql)
        call_val = call_allow_query.first()[0]
        if call_val:
            self.tot_called = int(call_val)
        else:
            self.tot_called = 0

        # get total already collected
        collection_sql = (f"SELECT COUNT(*) FROM {self.schema}.measurements WHERE event_id={self.cur_tow} "
                          f"AND measurement_type = 'stomach_collect' AND "
                          f"measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
        collection_query = self.db.dbQuery(collection_sql)
        self.collected = int(collection_query.first()[0])

        # get total already called
        if self.settings['DietCalledEnable'] in ['True', 'true', True]:
            called_sql = (f"SELECT COUNT(*) FROM {self.schema}.measurements WHERE event_id={self.cur_tow} "
                          f"AND measurement_type = 'stom_cont_1' "
                          f"AND measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
            called_query = (self.db.dbQuery(called_sql))
            self.called = int(called_query.first()[0])

        if self.collected >= self.tot_collect and self.called >= self.tot_called:
            result[measurements.index('diet_collection')] = [False, False]

        return result
