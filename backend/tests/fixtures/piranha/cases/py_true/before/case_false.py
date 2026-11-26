from flags import FEATURE_OLD_SEARCH


def search(query):
    if FEATURE_OLD_SEARCH:
        return legacy_search(query)
    else:
        return new_search(query)
