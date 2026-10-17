export {
  convertSwim,
  adjustAltitude,
  conversionMethod,
  type ConversionRequest,
  type ConversionValue,
  type AltitudeRequest,
  type AltitudeValue,
} from "./conversion.js";
export { parseTime, formatTime } from "./time.js";
export type {
  Course,
  Category,
  Stroke,
  Swim,
  SwimEvent,
  Result,
  Provenance,
  CoverageReason,
  ValidationReason,
} from "./contracts.js";
import { convertSwim, adjustAltitude } from "./conversion.js";

/** No I/O: the async boundary also permits a future explicitly loaded Wasm engine. */
export async function createEngine() {
  return Object.freeze({ convert: convertSwim, adjustAltitude });
}
