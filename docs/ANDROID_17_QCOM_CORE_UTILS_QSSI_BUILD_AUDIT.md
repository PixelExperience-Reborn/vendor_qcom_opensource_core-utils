# Stage 194 — Qualcomm core-utils / QSSI14 vs independent AOSP 17 build system

**Date:** 2026-11-08. **Project:** independent PixelExperience-Reborn, official Google AOSP android-17.0.0_r1. **Immediate task:** qualify platform repositories and build graph. No device trees, no SM8475 adaptation, no optional features in this stage.

## Historical source, prior developers and exact scope

- Historical repository: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_core-utils
- PE seventeen HEAD **9bd656462a3637798f4392a98e51d2a2c56f4748**, dated **2023-11-07**, tree **17e0e21650bc0b0c1d3279ab92bdfdc93ec67e71**. Final commit removed a historical HIDL Performance HAL from the Qualcomm FCM because **AIDL Perf2** was intended.
- Contains **50 archived tracked source files** in the recursive Git tree; Qualcomm QSSI-specific build orchestration, Soong config, legacy VINTF framework extension, DLKM make rules, metadata and device-tree image tools, and host image generator.
- The old files represent real Qualcomm engineering history. Do not call these tools useless merely because they are old. Conversely, neither their 2023 provenance nor the newer-sounding "QSSI" label establishes compatibility with a Google AOSP17 platform.

## Source-level findings and decisions

| Archived component | Original mechanism observed | AOSP17 platform decision |
| --- | --- | --- |
| build/build.sh v12 | QSSI-only / target-only / merge-only modes, qssi/qssi_64 mapping, merged target_files and OTA outputs | Retain as historical reference; do not replace independent Google build/make, Soong or release pipeline |
| Android.bp | Custom qssi_vs_vendor_cc_base Soong config defaults keyed by qssi_or_vendor | Do not inject QSSI-specific build variables into AOSP17 until an actual tracked consumer requires them |
| vendor_framework_compatibility_matrix.xml | Unversioned Qualcomm **framework** compatibility matrix with many optional vendor-specific HIDL + AIDL HALs; **vendor.qti.hardware.perf2** IPerf/default is AIDL V1, optional | Do not install as AOSP17 system FCM, do not grant implied vendor capability. Select vendor/product/system_ext FCMs via an independently reviewed manifest and VINTF schema only |
| build/AndroidBoardCommon.mk | QSSI board rules, vendor firmware mount points/symlinks, target kernel path, DTBO and checker hooks | Exclude from platform base; board-specific needs are a later separate device-tree problem |
| dlkm/AndroidKernelModule.mk | Kernel module building via old device/qcom/kernelscripts fallback, TARGET_PREBUILT_INT_KERNEL and CROSS_COMPILE | Do not import into Android17 platform build; reconcile with current kernel build/module packaging only when actual kernel integration begins |
| build/sdllvm-lto-defs.mk | Old SDCLANG_PATH and link/archiver flags, including legacy gold linker handling | Prefer official LLVM/Clang/LLD supplied by pinned AOSP17. No broad compiler override |
| vndk/Android.mk | Conditional generated VNDK-SP copies using historical BOARD_VNDK_VERSION / PLATFORM_VNDK_VERSION | Do not backport historical VNDK-SP packaging into Android17 |
| image_generation_tool/Android.bp + image_generation_tool.py, meta_image, dtbTool, packkernelimg | Separate vendor bundle/image/boot/vbmeta host helpers | Independently validate Google system/tools/mkbootimg, build/make releasetools and AVB before adopting any Qualcomm-specific image command |
| build/qcom.key | An archived key-like file is tracked in Git | **Never read, execute, package, sign with, or distribute it as a new PE-Reborn signing key**. Audit CI intentionally excludes its working-tree checkout |

The archive's XML is a Qualcomm framework-extension source, not the **official Android17 framework compatibility matrix**. AOSP17 uses the framework / device / system_ext / product FCM matching and VINTF lifecycle rules maintained by Android. An AIDL Perf2 declaration is not a working Performance HAL service: the service provider and proper partition/manifest ownership must be established independently. Do not import historical FM radio declarations or packages.

## AOSP17 official source ownership (immutable reference)

The independently pinned Android17 project graph already includes:
- **build/make** → platform/build
- **build/soong** → platform/build/soong
- **build/release** → platform/build/release
- **hardware/interfaces** → platform/hardware/interfaces
- **system/libvintf** → platform/system/libvintf
- **system/tools/mkbootimg** → platform/system/tools/mkbootimg
- **prebuilts/clang/host/linux-x86** → platform/prebuilts/clang/host/linux-x86

These are baseline platform build/VINTF/boot/toolchain owners; Qualcomm source may be considered when an identifiable **actual Android17 build dependency** has no approved equivalent. Choosing latest Qualcomm technology must be backed by exact source SHA, licence, module/API/ABI contract, Soong compatibility, and tests — not date or product name.

For context, Qualcomm's 2026 open `qualcomm-linux/qcom-build-utils` belongs to **Qualcomm Linux / Linux infrastructure**, not a verified direct replacement for Android/QSSI core-utils. Its workflows/Yocto packaging cannot be safely added to AOSP17 without a distinct port and need. No import from that repository is made here.

References:
- https://source.android.com/docs/core/architecture/vintf/comp-matrices
- https://source.android.com/docs/core/architecture/vintf/fcm
- https://github.com/qualcomm-linux/qcom-build-utils
- https://android.googlesource.com/platform/build/
- https://android.googlesource.com/platform/system/tools/mkbootimg/

## Actual changes in the stage 194 audit branch

1. Preserve original seventeen Git history and all archived original Git subtree/object IDs. Do not change Qualcomm sources, Makefiles, HIDL/AIDL, FCM, or tracked signing material.
2. Add host-only Python tests for original snapshot, QSSI script purpose, custom Soong variables, XML FCM AIDL Perf2 and old HIDL coexistence, board/DLKM/SDLLVM/VNDK/image-generation boundaries, no archived key checkout and canonical AOSP17 build graph. Source-only tests use an exact pinned AOSP17 manifest commit.
3. GitHub Actions uses **sparse-checkout-cone-mode: false** and explicit source file paths to deliberately *exclude* build/qcom.key from the working tree; legacy tools are NOT executed.
4. Companion manifest Draft PR #2 blocks only this exact archive's path and known aliases in all active and experimental profiles; two negative tests; strict 135-path matrix stage 194 row. Default.xml and historic seventeen unchanged.

## Remaining gates — platform, not hardware

- Verify all selected 25 source stages and candidates with real repo manifest resolution and targeted sync. Do not claim it is an entire checked-out Android17 tree.
- Build host-tools/Soong/bootstrap, test module collision and real exported QSSI dependencies, fix actual compile failures in own platform repos.
- Validate platform image packaging, current VINTF format, signing provenance, security and reliable reproducible builds with real Android17 tools. Decide separately whether any Qualcomm-specific tool/definition is required in PE-Reborn.
- Only once independent AOSP17 platform source is compiled and qualified, plan a **separate** SM8475 device bring-up. LF52406/LineageOS device trees stay read-only references and are **not** CI inputs.

**No full AOSP17 platform build or ROM image was produced. CI PASS = source, metadata and manifest tests only.**
