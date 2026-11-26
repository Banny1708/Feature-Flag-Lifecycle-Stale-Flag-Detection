from flags import FEATURE_NEW_UI, FEATURE_OLD_SEARCH


def both(user):
    if FEATURE_NEW_UI:
        a = "new"
    else:
        a = "old"
    if FEATURE_OLD_SEARCH:
        b = "legacy"
    else:
        b = "modern"
    return a, b
