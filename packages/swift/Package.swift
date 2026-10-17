// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "TurnmarkCore",
    platforms: [.iOS(.v17)],
    products: [.library(name: "TurnmarkCore", targets: ["TurnmarkCore"])],
    targets: [
        .binaryTarget(name: "turnmark_coreFFI", path: "Artifacts/TurnmarkCoreFFI.xcframework"),
        .target(name: "TurnmarkCore", dependencies: ["turnmark_coreFFI"]),
        .testTarget(name: "TurnmarkCoreTests", dependencies: ["TurnmarkCore"], resources: [.copy("Fixtures")]),
    ]
)
