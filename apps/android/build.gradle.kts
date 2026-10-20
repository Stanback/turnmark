plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "net.stanback.turnmark"
    compileSdk = 37
    defaultConfig {
        applicationId = "net.stanback.turnmark"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"
        ndk.abiFilters += listOf("arm64-v8a", "x86_64")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    sourceSets.getByName("androidTest").assets.srcDir("../history")
    buildFeatures { compose = true }
    testOptions.animationsDisabled = true
    testOptions.managedDevices.localDevices.create("turnmarkPhone") {
        device = "Pixel 2"
        sdkVersion = 37
        systemImageSource = "google"
        require64Bit = true
        // API 37's software-rendered 16 KB image has allocator stalls. Keep
        // this fast UI lane on 4 KB; 16 KB runtime remains a release check.
        pageAlignment = com.android.build.api.dsl.ManagedVirtualDevice.PageAlignment.FORCE_4KB_PAGES
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(project(":sdk-android"))
    implementation("androidx.activity:activity-compose:1.13.0")
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material3.adaptive:adaptive:1.3.0")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    // Compose's transitive Espresso 3.5 uses reflection removed on Android 17.
    androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.window:window-testing:1.5.1")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
}
