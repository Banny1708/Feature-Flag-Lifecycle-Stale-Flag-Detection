from flags import FEATURE_NEW_UI


def badge(user):
    if FEATURE_NEW_UI and user.premium:
        return "gold"
    return "basic"
