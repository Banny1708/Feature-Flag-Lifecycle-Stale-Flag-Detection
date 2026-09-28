/**
 * API Client abstraction.
 * Currently serves data with simulated async delay for realistic UI loading states.
 * When backend REST API is available, swap fetch logic here without modifying UI components.
 */

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

const SIMULATED_DELAY_MS = 100;

export async function simulateFetch<T>(data: T, delayMs: number = SIMULATED_DELAY_MS): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(JSON.parse(JSON.stringify(data)));
    }, delayMs);
  });
}
