from flags import FEATURE_NEW_UI, FEATURE_OLD_SEARCH


def both(user):
    if FEATURE_NEW_UI:
        a = "new"
    else:
        a = "old"
    b = "modern"
    return a, b
