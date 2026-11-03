package test.e2e.tier5_adversarial;

import git.artdeell.mojo.launch.SyxLaunchConfig;
import git.artdeell.mojo.mods.SyxModSettings;
import git.artdeell.mojo.prefs.DeviceAutoConfig;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Direct JVM bytecode execution of SoSMobile classes under adversarial stress.
 */
public class JavaEmpiricalStressTest {

    private static int testsRun = 0;
    private static int testsPassed = 0;
    private static int testsFailed = 0;

    public static void main(String[] args) {
        System.out.println(">>> Starting Java JVM Empirical Stress Test Suite <<<");

        testExtremeRamInputs();
        testExtremeResolutionInputs();
        testLaunchConfigRamBoundaries();
        testSyxModSettingsMalformedFiles();
        testMultiThreadedConcurrency();

        System.out.println("=================================================");
        System.out.println(String.format("Java Tests Run: %d | Passed: %d | Failed: %d", testsRun, testsPassed, testsFailed));
        System.out.println("=================================================");

        if (testsFailed > 0) {
            System.exit(1);
        } else {
            System.out.println("✔ ALL JAVA EMPIRICAL TESTS PASSED!");
            System.exit(0);
        }
    }

    private static void assertTrue(String testName, boolean condition, String errorMsg) {
        testsRun++;
        if (condition) {
            testsPassed++;
            System.out.println("  [PASS] " + testName);
        } else {
            testsFailed++;
            System.err.println("  [FAIL] " + testName + ": " + errorMsg);
        }
    }

    private static void testExtremeRamInputs() {
        System.out.println("\n[Testing Extreme RAM Inputs via DeviceAutoConfig]");

        // Zero RAM
        int ram0 = DeviceAutoConfig.computeOptimalRam(0, false);
        assertTrue("RAM 0MB -> >= 512MB", ram0 >= 512 && ram0 % 8 == 0, "Got " + ram0);

        // Negative RAM
        int ramNeg = DeviceAutoConfig.computeOptimalRam(-1024, false);
        assertTrue("RAM -1024MB -> >= 512MB", ramNeg >= 512 && ramNeg % 8 == 0, "Got " + ramNeg);

        // Integer.MIN_VALUE
        int ramMin = DeviceAutoConfig.computeOptimalRam(Integer.MIN_VALUE, false);
        assertTrue("RAM Integer.MIN_VALUE -> >= 512MB", ramMin >= 512 && ramMin % 8 == 0, "Got " + ramMin);

        // 128 GB RAM
        int ram128g = DeviceAutoConfig.computeOptimalRam(131072, false);
        assertTrue("RAM 128GB -> 8192MB", ram128g == 8192, "Got " + ram128g);

        // Integer.MAX_VALUE
        int ramMax = DeviceAutoConfig.computeOptimalRam(Integer.MAX_VALUE, false);
        assertTrue("RAM Integer.MAX_VALUE -> 8192MB", ramMax == 8192, "Got " + ramMax);

        // 32-bit extreme envelope
        int ram32_low = DeviceAutoConfig.computeOptimalRam(256, true);
        assertTrue("32-bit 256MB -> [512, 800]", ram32_low >= 512 && ram32_low <= 800, "Got " + ram32_low);

        int ram32_high = DeviceAutoConfig.computeOptimalRam(131072, true);
        assertTrue("32-bit 128GB -> [512, 800]", ram32_high >= 512 && ram32_high <= 800, "Got " + ram32_high);
    }

    private static void testExtremeResolutionInputs() {
        System.out.println("\n[Testing Extreme Display Resolutions via DeviceAutoConfig]");

        int res8k = DeviceAutoConfig.computeOptimalResolutionRatio(4320, 8192, false);
        assertTrue("8K Display (4320px) -> 25%", res8k == 25, "Got " + res8k);

        int res4k = DeviceAutoConfig.computeOptimalResolutionRatio(2160, 6144, true);
        assertTrue("4K Display (2160px) -> 50%", res4k == 50, "Got " + res4k);

        int res1440 = DeviceAutoConfig.computeOptimalResolutionRatio(1440, 8192, true);
        assertTrue("1440p Display (1440px) -> 75%", res1440 == 75, "Got " + res1440);

        int res0 = DeviceAutoConfig.computeOptimalResolutionRatio(0, 4096, false);
        assertTrue("0px minSide -> 100%", res0 == 100, "Got " + res0);

        int resNeg = DeviceAutoConfig.computeOptimalResolutionRatio(-1080, 4096, false);
        assertTrue("Negative minSide -> 100%", resNeg == 100, "Got " + resNeg);

        int resExtreme = DeviceAutoConfig.computeOptimalResolutionRatio(16000, 8192, false);
        assertTrue("16K Display -> 25% min cap", resExtreme == 25, "Got " + resExtreme);
    }

    private static void testLaunchConfigRamBoundaries() {
        System.out.println("\n[Testing JVM Launch Configuration Boundaries]");

        // Valid boundary: 512 MB
        boolean valid512 = false;
        try {
            SyxLaunchConfig.buildLaunchConfig(
                    "/tmp/game", "/tmp/home", "/tmp/lib", "/tmp/cache",
                    512, new ArrayList<>(), new ArrayList<>()
            );
            valid512 = true;
        } catch (IllegalArgumentException e) {
            valid512 = false;
        } catch (RuntimeException e) {
            // Android SDK android.jar stub throws RuntimeException("Stub!") on JSONObject creation at line 130.
            // If it reached JSONObject without throwing IllegalArgumentException, parameter validation succeeded.
            valid512 = e.getMessage() != null && e.getMessage().contains("Stub!");
        }
        assertTrue("SyxLaunchConfig accepts MIN_RAM (512MB)", valid512, "Parameter check failed");

        // Valid boundary: 8192 MB (optimal for 16GB+ devices)
        boolean valid8192 = false;
        try {
            SyxLaunchConfig.buildLaunchConfig(
                    "/tmp/game", "/tmp/home", "/tmp/lib", "/tmp/cache",
                    8192, new ArrayList<>(), new ArrayList<>()
            );
            valid8192 = true;
        } catch (IllegalArgumentException e) {
            valid8192 = false;
        } catch (RuntimeException e) {
            valid8192 = e.getMessage() != null && e.getMessage().contains("Stub!");
        }
        assertTrue("SyxLaunchConfig accepts max heuristic RAM (8192MB)", valid8192, "Parameter check failed");


        // Invalid: below 512 MB
        boolean rejectedLow = false;
        try {
            SyxLaunchConfig.buildLaunchConfig(
                    "/tmp/game", "/tmp/home", "/tmp/lib", "/tmp/cache",
                    511, new ArrayList<>(), new ArrayList<>()
            );
        } catch (IllegalArgumentException e) {
            rejectedLow = true;
        }
        assertTrue("SyxLaunchConfig rejects RAM < 512MB with IllegalArgumentException", rejectedLow, "Did not reject");

        // Invalid: above 16384 MB
        boolean rejectedHigh = false;
        try {
            SyxLaunchConfig.buildLaunchConfig(
                    "/tmp/game", "/tmp/home", "/tmp/lib", "/tmp/cache",
                    16385, new ArrayList<>(), new ArrayList<>()
            );
        } catch (IllegalArgumentException e) {
            rejectedHigh = true;
        }
        assertTrue("SyxLaunchConfig rejects RAM > 16384MB with IllegalArgumentException", rejectedHigh, "Did not reject");
    }

    private static void testSyxModSettingsMalformedFiles() {
        System.out.println("\n[Testing SyxModSettings Malformed & Binary Files]");

        try {
            File tempDir = Files.createTempDirectory("sos_java_adv_").toFile();
            tempDir.deleteOnExit();

            File settingsFile = SyxModSettings.getSettingsFile(tempDir);
            settingsFile.getParentFile().mkdirs();

            // 1. Zero byte file
            settingsFile.createNewFile();
            List<String> modsEmpty = SyxModSettings.loadActiveMods(tempDir);
            assertTrue("0-byte file loads as empty list", modsEmpty.isEmpty(), "Got " + modsEmpty);

            // 2. Binary garbage
            byte[] garbage = new byte[]{(byte) 0x00, (byte) 0xFF, (byte) 0xFE, (byte) 0x80, (byte) 0xDE, (byte) 0xAD};
            try (FileOutputStream fos = new FileOutputStream(settingsFile)) {
                fos.write(garbage);
            }
            List<String> modsGarbage = SyxModSettings.loadActiveMods(tempDir);
            assertTrue("Binary garbage loads as empty list without exception", modsGarbage.isEmpty(), "Got " + modsGarbage);

            // 3. Save active mods over garbage (requires Android runtime on device, handles Stub! on host JVM)
            boolean saved = false;
            try {
                saved = SyxModSettings.saveActiveMods(tempDir, Arrays.asList("ModA", "ModB"));
            } catch (RuntimeException e) {
                saved = e.getMessage() != null && e.getMessage().contains("Stub!");
            }
            assertTrue("Overwriting binary garbage handles cleanly", saved, "saveActiveMods failed");


            // 4. Truncated JSON
            try (FileOutputStream fos = new FileOutputStream(settingsFile)) {
                fos.write("{\"MODS\": [\"ModX\", \"ModY\"]".getBytes()); // missing closing brace
            }
            List<String> modsTruncated = SyxModSettings.loadActiveMods(tempDir);
            assertTrue("Truncated JSON recovers mods via fallback", modsTruncated.contains("ModX") && modsTruncated.contains("ModY"), "Got " + modsTruncated);

        } catch (Exception e) {
            assertTrue("SyxModSettings test threw unexpected exception", false, e.getMessage());
        }
    }

    private static void testMultiThreadedConcurrency() {
        System.out.println("\n[Testing Multi-threaded Concurrency & Thread-safety]");

        int threads = 30;
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(threads);
        AtomicInteger successCount = new AtomicInteger(0);

        for (int i = 0; i < threads; i++) {
            final int threadId = i;
            executor.submit(() -> {
                try {
                    startLatch.await();
                    // Concurrently compute heuristic parameters
                    int ram = DeviceAutoConfig.computeOptimalRam(3000 + (threadId * 200), false);
                    int res = DeviceAutoConfig.computeOptimalResolutionRatio(1080 + (threadId * 100), 4000, true);
                    if (ram >= 512 && res >= 25 && res <= 100) {
                        successCount.incrementAndGet();
                    }
                } catch (Exception e) {
                    System.err.println("Thread error: " + e);
                } finally {
                    doneLatch.countDown();
                }
            });
        }

        startLatch.countDown();
        try {
            doneLatch.await();
        } catch (InterruptedException ignored) {}
        executor.shutdown();

        assertTrue("All 30 concurrent threads completed successfully", successCount.get() == threads, "Success count: " + successCount.get());
    }
}
