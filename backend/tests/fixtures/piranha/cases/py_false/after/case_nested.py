from flags import FEATURE_NEW_UI


def nested(user):
    if FEATURE_NEW_UI:
        if user.premium:
            return "a"
        return "b"
    return "c"
