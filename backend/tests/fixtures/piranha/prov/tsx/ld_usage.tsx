import { init as initLD } from "launchdarkly-node-server-sdk";

const client = initLD("sdk-key");

export async function checkout(user: string): Promise<string> {
  if (await client.variation("TSX_CHECKOUT", user, false)) {
    return "new";
  }
  return "old";
}

export async function detail(user: string): Promise<unknown> {
  const d = await client.variationDetail("TSX_DETAIL", user, false);
  return d.value;
}
