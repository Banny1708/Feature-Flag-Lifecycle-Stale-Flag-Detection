

export function nested(premium: boolean): string {
  {
    if (premium) {
      return "a";
    }
    return "b";
  }
  return "c";
}
