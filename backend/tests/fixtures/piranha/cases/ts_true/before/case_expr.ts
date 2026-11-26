import { FEATURE_NEW_UI } from "./flags";

export function badge(premium: boolean): string {
  if (FEATURE_NEW_UI && premium) {
    return "gold";
  }
  return "basic";
}
