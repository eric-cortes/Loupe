const PALETTE = [
  "#7a2c22",
  "#2c4a3e",
  "#3a3a6b",
  "#6b4a2c",
  "#4a2c5e",
  "#2c4a5e",
  "#5e2c3a",
];

export function colorFor(id: number): string {
  return PALETTE[id % PALETTE.length];
}
