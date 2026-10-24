import metadata from "./generated/metadata.json" with { type: "json" };
import {
  conversionSource,
  altitudeSource,
  coloradoSource,
  empiricalSource,
  ncaaAltitudeSource,
} from "./data/conversions.js";
import type { Provenance } from "./contracts.js";
export {
  conversionSource,
  altitudeSource,
  coloradoSource,
  empiricalSource,
  ncaaAltitudeSource,
};

export const conversionMethod = "ncaa-2025-27";
export const coloradoMethod = "colorado-teamunify-2026";
export const empiricalMethod = "turnmark-empirical-2026";
export type ConversionMethod =
  | typeof conversionMethod
  | typeof coloradoMethod
  | typeof empiricalMethod;
export const conversionMethods = [
  { id: conversionMethod, label: "NCAA (default)", source: conversionSource },
  { id: coloradoMethod, label: "Colorado Timing", source: coloradoSource },
  {
    id: empiricalMethod,
    label: "Turnmark Equivalence",
    source: empiricalSource,
  },
] as const;
export const conversionProvenance: Readonly<Provenance> = Object.freeze({
  id: conversionMethod,
  ...conversionSource,
  sha256: metadata.sources.ncaa.sha256,
});
export const altitudeProvenance: Readonly<Provenance> = Object.freeze({
  id: "usa-swimming-altitude-2026",
  title: altitudeSource.title,
  url: altitudeSource.url,
  revision: altitudeSource.verified,
});
export const altitudePolicies = [
  {
    id: "usa-swimming-altitude-2026",
    label: "USA Swimming (default)",
    source: altitudeSource,
  },
  {
    id: "ncaa-altitude-2026-27-d1",
    label: "NCAA · 2026–27 Division I",
    source: ncaaAltitudeSource,
  },
] as const;
export type AltitudePolicy = (typeof altitudePolicies)[number]["id"];
