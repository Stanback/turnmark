import { callCore, compatibility } from "./core.js";

export function parseTime(input: unknown): number | null {
  return typeof input === "string" ? callCore("parse", input) : null;
}
export function truncateTime(seconds: number): number {
  return Number.isFinite(seconds)
    ? compatibility("truncateTime", [seconds])
    : seconds;
}
export function formatTime(seconds: number | null, round = false): string {
  return compatibility("formatTime", [seconds, round]);
}
