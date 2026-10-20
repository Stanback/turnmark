package net.stanback.turnmark

/** A small local iteration suite; the default CI run still includes all tests. */
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class SmokeTest
