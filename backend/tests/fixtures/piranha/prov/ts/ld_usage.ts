import { init as initLD } from "launchdarkly-node-server-sdk";

const client = initLD("sdk-key");

export async function checkout(user: unknown): Promise<string> {
  if (await client.variation("LD_TS_CHECKOUT", user, false)) {
    return "new";
  }
  return "old";
}

export async function typed(user: unknown): Promise<string> {
  if (await client.boolVariation("LD_TS_BOOL", user, false)) {
    return "on";
  }
  return "off";
}

export async function strv(user: unknown): Promise<string> {
  return client.stringVariation("LD_TS_STR", user, "dflt");
}

export async function numv(user: unknown): Promise<number> {
  return client.numberVariation("LD_TS_NUM", user, 0);
}

export async function jsonv(user: unknown): Promise<unknown> {
  return client.jsonVariation("LD_TS_JSON", user, {});
}

export async function detail(user: unknown): Promise<unknown> {
  // VariationDetail returns an object: must NOT be cleaned
  const d = await client.variationDetail("LD_TS_DETAIL", user, false);
  return d.value;
}

export async function computed(user: unknown, name: string): Promise<number> {
  // computed key: must NOT be detected
  if (await client.variation("prefix_" + name, user, false)) {
    return 1;
  }
  return 0;
}
