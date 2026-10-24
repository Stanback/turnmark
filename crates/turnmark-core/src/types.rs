use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum Course {
    SCY,
    SCM,
    LCM,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum Category {
    Women,
    Men,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum Stroke {
    Freestyle,
    Backstroke,
    Breaststroke,
    Butterfly,
    IndividualMedley,
}

macro_rules! record {
    ($name:ident { $($(#[$meta:meta])* $field:ident: $ty:ty),* $(,)? }) => {
        #[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
        #[serde(rename_all = "camelCase")]
        #[cfg_attr(feature = "native", derive(uniffi::Record))]
        pub struct $name { $($(#[$meta])* pub $field: $ty),* }
    };
}
record!(SwimEvent {
    distance: u32,
    stroke: Stroke,
    course: Course
});
record!(EventOption {
    event: SwimEvent,
    canonical_distance: u32
});
record!(Swim {
    time: String,
    event: SwimEvent
});
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[cfg_attr(feature = "native", derive(uniffi::Record))]
pub struct Provenance {
    pub id: String,
    pub title: String,
    pub url: String,
    pub revision: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sha256: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verified: Option<String>,
}
record!(ConversionRequest {
    swim: Swim,
    to: Course,
    table: Category
});
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum ConversionMethod {
    #[serde(rename = "ncaa-2025-27")]
    Ncaa,
    #[serde(rename = "colorado-teamunify-2026")]
    Colorado,
    #[serde(rename = "turnmark-empirical-2026")]
    Empirical,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum AltitudePolicy {
    #[serde(rename = "usa-swimming-altitude-2026")]
    UsaSwimming,
    #[serde(rename = "ncaa-altitude-2026-27-d1")]
    Ncaa,
}
record!(Elevation {
    value: f64,
    unit: ElevationUnit
});
record!(AltitudeRequest {
    swim: Swim,
    elevation: Elevation
});
record!(StandardsRequest {
    event: SwimEvent,
    table: Category,
    age: String
});
record!(PointsRequest {
    swim: Swim,
    table: Category
});

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum ElevationUnit {
    Feet,
    Meters,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum ConversionKind {
    Swum,
    Published,
    Derived,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum AltitudeKind {
    Swum,
    AltitudeAdjusted,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum CoverageReason {
    EventNotPublished,
    CourseNotSupported,
    AgeGroupNotPublished,
    FactorNotPublished,
    NoTimePublished,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum ValidationReason {
    InvalidInput,
    InvalidTime,
    InvalidCourse,
    InvalidStroke,
    InvalidDistance,
    InvalidCategory,
    InvalidAgeGroup,
    InvalidElevation,
    UnsupportedMethod,
    UnsupportedDataset,
    UnsafeResult,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum ConversionCaveat {
    ColoradoShortCourseDistance,
    /// The equivalence conversion rests on limited data: few swimmers in the training data swam
    /// this event in both courses, or its bootstrap interval at this time is wide.
    EmpiricalLowEvidence,
    /// The entered time lies outside the model's fitted range for this event and these courses;
    /// the conversion extrapolates beyond the available fit.
    EmpiricalOutOfRange,
}
record!(ConversionValue {
    time: String,
    seconds: f64,
    hundredths: u64,
    factor: f64,
    #[serde(default, skip_serializing_if = "is_zero")]
    offset_seconds: f64,
    kind: ConversionKind,
    event: SwimEvent,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    altitude: Option<AltitudeCalculation>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    caveat: Option<ConversionCaveat>
});
fn is_zero(value: &f64) -> bool {
    *value == 0.0
}
record!(AltitudeValue {
    raw_time: String,
    adjusted_time: String,
    raw_seconds: f64,
    adjusted_seconds: f64,
    adjustment_seconds: f64,
    elevation_feet: u32,
    kind: AltitudeKind
});
record!(AltitudeCalculation {
    value: AltitudeValue,
    provenance: Provenance
});
record!(YouthValue { event: SwimEvent, age: String, levels: Vec<String>, times: Vec<f64> });
record!(MastersValue {
    event: SwimEvent,
    age: String,
    time: String,
    seconds: f64,
    hundredths: u64
});
record!(Milestone {
    points: u64,
    time: String,
    seconds: f64,
    gap_seconds: f64
});
record!(PointsValue {
    points: u64,
    base_time: String,
    base_seconds: f64,
    validity: String,
    next_milestone: Milestone
});

pub(crate) enum Failure {
    Invalid {
        field: String,
        reason: ValidationReason,
    },
    Unavailable {
        reason: CoverageReason,
        provenance: Box<Provenance>,
    },
}
pub(crate) type Calculation<T> = Result<(T, Provenance), Failure>;
macro_rules! outcome {
    ($(#[$meta:meta])* $name:ident, $value:ident) => {
        #[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
        #[serde(tag = "status", rename_all = "lowercase")]
        #[cfg_attr(feature = "native", derive(uniffi::Enum))]
        $(#[$meta])*
        pub enum $name {
            Available {
                value: $value,
                provenance: Provenance,
            },
            Unavailable {
                reason: CoverageReason,
                provenance: Provenance,
            },
            Invalid {
                field: String,
                reason: ValidationReason,
            },
        }
        impl From<Calculation<$value>> for $name {
            fn from(result: Calculation<$value>) -> Self {
                match result {
                    Ok((value, provenance)) => Self::Available { value, provenance },
                    Err(Failure::Invalid { field, reason }) => Self::Invalid { field, reason },
                    Err(Failure::Unavailable { reason, provenance }) => Self::Unavailable {
                        reason,
                        provenance: *provenance,
                    },
                }
            }
        }
    };
}
// UniFFI outcomes carry concrete records. Preserve that generated API shape;
// the optional source-backed altitude context makes this variant 440 bytes.
outcome!(
    #[allow(clippy::large_enum_variant)]
    ConversionOutcome,
    ConversionValue
);
outcome!(AltitudeOutcome, AltitudeValue);
outcome!(YouthOutcome, YouthValue);
outcome!(MastersOutcome, MastersValue);
outcome!(PointsOutcome, PointsValue);

/// The benchmark dataset; a qualifying target is not entry eligibility.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
#[cfg_attr(feature = "native", derive(uniffi::Enum))]
pub enum StandardSystem {
    Youth,
    Masters,
    Futures,
    Juniors,
    Nisca,
}
record!(StandardProgram {
    system: StandardSystem, label: String, title: String, scope: String, ages: Vec<String>, note: String
});
record!(BenchmarkRequest {
    swim: Swim,
    table: Category,
    age: String,
    system: StandardSystem
});
record!(TimeTarget {
    label: String,
    time: String,
    seconds: f64,
    met: bool,
    gap_seconds: f64
});
record!(BenchmarkValue {
    event: SwimEvent, age: String, system: StandardSystem,
    entered_time: String, entered_seconds: f64,
    targets: Vec<TimeTarget>, achieved_level: Option<String>, next_target: Option<TimeTarget>
});
outcome!(BenchmarkOutcome, BenchmarkValue);
