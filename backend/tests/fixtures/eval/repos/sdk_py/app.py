import ldclient

client = ldclient.get()

def checkout(user):
    if client.variation("LD_PY_CHECKOUT", user, False):
        return new_ui(user)
    return old_ui(user)

def flag_detail(user):
    # variation_detail returns an object, not a value: must NOT be cleaned
    d = client.variation_detail("LD_PY_DETAIL", user, False)
    return d.value

def computed(user, name):
    # computed key: must NOT be detected as a static flag
    if client.variation("prefix_" + name, user, False):
        return 1
    return 0

def envkey(user):
    import os
    # environment-derived key: must NOT be detected as a static flag
    if client.variation(os.getenv("LD_ENV_KEY", "fallback"), user, False):
        return 1
    return 0
