export function helper(x: number): number {
  // UNRELATED_CODE must never change
  if (x > 0) {
    return x * 2;
  }
  return 0;
}
