import { FEATURE_NEW_UI } from "./flags";

export function nested(premium: boolean): string {
  if (FEATURE_NEW_UI) {
    if (premium) {
      return "a";
    }
    return "b";
  }
  return "c";
}
