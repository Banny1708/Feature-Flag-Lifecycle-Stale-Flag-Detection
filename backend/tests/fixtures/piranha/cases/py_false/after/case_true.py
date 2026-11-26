from flags import FEATURE_NEW_UI


def render(user):
    if FEATURE_NEW_UI:
        return new_ui(user)
    else:
        return old_ui(user)
