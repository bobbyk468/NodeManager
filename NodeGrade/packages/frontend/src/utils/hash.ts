/** FNV-1a 64-bit hash — used for FERPA-safe answer fingerprinting (hex string, not reversible). */
export function fnv1a(text: string): string {
  let hash = BigInt('0xcbf29ce484222325');
  const prime = BigInt('0x00000100000001b3');
  const mask64 = (BigInt(1) << BigInt(64)) - BigInt(1);
  for (let i = 0; i < text.length; i++) {
    hash ^= BigInt(text.charCodeAt(i));
    hash = (hash * prime) & mask64;
  }
  return hash.toString(16).padStart(16, '0');
}
