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
.. module:: startMACETrawlEvent

    :synopsis: startMACETrawlEvent presents the event selection dialog
               allowing the user to select the event (new or previous) and
               then opens the trawl event form for that event. It used
               to also present the simple protected spp. check dialog but
               that was disabled starting with the FY22 field season since
               the PS observation protocol changed and the observation
               start and stop actions were integrated into our trawl events.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
"""

import eventseldlg


class startFEATTrawlEvent:
    def __init__(self, parent):
        #  create an instance of the event selection dialog
        hlDialog = eventseldlg.EventSelDlg(parent)

        #  display the event select dialog
        if hlDialog.exec():
            #  check if a event number was selected - exit if not
            if not hlDialog.activeEvent:
                return

            #  set the active event
            parent.activeEvent = hlDialog.activeEvent
            parent.reloaded = hlDialog.reloaded
