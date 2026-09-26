class GapNotFoundError(Exception):
    """No CQI gap with the requested id in this organization."""
    pass


class GapNotWaivableError(Exception):
    """Only an OPEN or ADDRESSED gap can be waived."""
    pass
