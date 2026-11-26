import { FEATURE_OLD_SEARCH } from "./flags";

export function search(query: string): string {
  if (FEATURE_OLD_SEARCH) {
    return legacySearch(query);
  } else {
    return newSearch(query);
  }
}
