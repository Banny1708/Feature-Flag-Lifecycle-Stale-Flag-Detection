import { FEATURE_NEW_UI } from "./flags";

export function render(user: string): string {
  if (FEATURE_NEW_UI) {
    return newUi(user);
  } else {
    return oldUi(user);
  }
}
