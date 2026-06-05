class AttainmentConfigNotFound(Exception):
    pass


class AttainmentNotComputed(Exception):
    """No attainment results yet for this section offering."""
    pass


class NoPublishedResultError(Exception):
    """Tried to compute but result publication is not PUBLISHED."""
    pass
