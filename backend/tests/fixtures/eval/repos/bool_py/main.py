from flags import FEATURE_BOOL_EVAL


def render(user):
    if FEATURE_BOOL_EVAL:
        return new_ui(user)
    else:
        return old_ui(user)
