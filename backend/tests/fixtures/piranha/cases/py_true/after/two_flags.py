from flags import FEATURE_NEW_UI, FEATURE_OLD_SEARCH


def both(user):
    a = "new"
    if FEATURE_OLD_SEARCH:
        b = "legacy"
    else:
        b = "modern"
    return a, b
