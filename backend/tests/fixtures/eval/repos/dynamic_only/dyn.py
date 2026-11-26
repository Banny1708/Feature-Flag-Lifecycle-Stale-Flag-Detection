import ldclient

client = ldclient.get()


def dyn(user, name):
    if client.variation("prefix_" + name, user, False):
        return 1
    return 0


def env(user):
    import os
    if client.variation(os.getenv("SOME_ENV_FLAG", "x"), user, False):
        return 1
    return 0
