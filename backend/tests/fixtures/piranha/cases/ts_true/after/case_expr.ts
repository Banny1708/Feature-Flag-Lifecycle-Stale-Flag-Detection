

export function badge(premium: boolean): string {
  if (premium) {
    return "gold";
  }
  return "basic";
}
