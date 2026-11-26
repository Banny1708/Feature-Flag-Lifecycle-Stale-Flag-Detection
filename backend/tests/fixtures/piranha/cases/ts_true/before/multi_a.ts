import { FEATURE_NEW_UI } from "./flags";

export function partA(): number {
  if (FEATURE_NEW_UI) {
    return 1;
  }
  return 0;
}
