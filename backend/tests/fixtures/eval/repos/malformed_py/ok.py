import ldclient

client = ldclient.get()


def dynamic_only(user, name):
    # computed key only: must not be detected, must not crash the scan
    if client.variation("prefix_" + name, user, False):
        return 1
    return 0
