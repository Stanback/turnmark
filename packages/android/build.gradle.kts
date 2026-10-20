plugins { id("com.android.library") }

android {
    testOptions.animationsDisabled = true
    testOptions.managedDevices.localDevices.create("turnmarkPhone") {
        device = "Pixel 2"
        sdkVersion = 37
        systemImageSource = "google"
        require64Bit = true
        pageAlignment = com.android.build.api.dsl.ManagedVirtualDevice.PageAlignment.FORCE_4KB_PAGES
    }
    namespace = "org.turnmark.sdk"
    compileSdk = 36
    ndkVersion = "30.0.16248370"
    defaultConfig {
        minSdk = 26
        ndk.abiFilters += listOf("arm64-v8a", "x86_64")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        consumerProguardFiles("consumer-rules.pro")
    }
    sourceSets {
        getByName("main") {
            kotlin.directories.add("../../bindings/generated/uniffi")
            jniLibs.directories.add("../../bindings/generated/android/jniLibs")
        }
        getByName("androidTest").assets.directories.add("../../fixtures")
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    api("net.java.dev.jna:jna:5.19.1@aar")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
}
