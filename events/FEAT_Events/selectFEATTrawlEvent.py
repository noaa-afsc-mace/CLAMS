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
.. module:: selectFEATTrawlEvent

    :synopsis: selectFEATTrawlEvent presents the event selection dialog
               allowing the user to select the event (new or previous) and
               then sets the current trawl to that number. Used in the Wet Lab
               to bypass the need for the

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
"""
selectFEATTrawlEvent is a helper function used to launch the FEAT select trawl event.
This helper function was needed to implement the new event launcher system.
New event forms should be written such that they do not need a helper function.
"""

import FEATTrawlEvent


class SelectFEATTrawlEvent():

    def __init__(self, parent):

        self.parent = parent
        # create an instance of the trawl event dialog and display
        trawl_event = FEATTrawlEvent.FEATTrawlEvent(self.parent)
        trawl_event.exec_()
        if trawl_event.result() == 1:
            self.parent.activeEvent = trawl_event.activeEvent
