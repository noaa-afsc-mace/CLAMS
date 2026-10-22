"""
Organization constants and helper utilities for CLAMS.
"""

# Organization string constants
NWFSC = 'nwfsc'
SWFSC = 'swfsc'
AFSC = 'afsc'

def getOrganizationName(settings) -> str:
    """
    Extracts the lowercase organization name from:
    - An object with a .settings dict (e.g., passing `self` from any CLAMS window/dialog)
    - A direct settings dictionary: settings['OrganizationName']
    - A raw string: 'NWFSC'
    """
    return settings.get('OrganizationName', '').lower()


def hasOrganization(source, *target_orgs) -> bool:
    """
    Returns True if any of the target organization names are contained
    within the resolved organization name.
    """
    org_name = getOrganizationName(source)
    return any(target in org_name for target in target_orgs)
