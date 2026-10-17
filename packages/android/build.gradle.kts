plugins { id("com.android.library") }

android {
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
