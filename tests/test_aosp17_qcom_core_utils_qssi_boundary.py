#!/usr/bin/env python3
"""PE-Reborn stage 194: isolate historical Qualcomm QSSI core-utils from AOSP17.

SOURCE-ONLY. This deliberately does not import LineageOS device trees,
execute legacy signing tools, build kernel modules, or read archived key data.
"""
from pathlib import Path
import os
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "9bd656462a3637798f4392a98e51d2a2c56f4748"
ARCHIVE_TREE = "17e0e21650bc0b0c1d3279ab92bdfdc93ec67e71"
LEGACY_PATH = "vendor/qcom/opensource/core-utils"
LEGACY_NAME = "vendor_qcom_opensource_core-utils"
GOOGLE_SOURCES = {
    "build/make": "platform/build",
    "build/release": "platform/build/release",
    "build/soong": "platform/build/soong",
    "hardware/interfaces": "platform/hardware/interfaces",
    "system/libvintf": "platform/system/libvintf",
    "system/tools/mkbootimg": "platform/system/tools/mkbootimg",
    "prebuilts/clang/host/linux-x86": "platform/prebuilts/clang/host/linux-x86",
}


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def entry(tree, path):
    data = git("ls-tree", tree, "--", path)
    if not data:
        raise AssertionError("Git entry missing: " + path)
    fields, named = data.split("\t", 1)
    if named != path:
        raise AssertionError("Git path mismatch " + named)
    mode, kind, oid = fields.split()
    return mode, kind, oid


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def reference(env):
    path = os.environ.get(env)
    if not path or not Path(path).is_file():
        raise AssertionError("required pinned source: " + env)
    return Path(path).read_text(encoding="utf-8")


class QssiCoreUtilsAosp17Boundary(unittest.TestCase):
    def test_historic_qualcomm_snapshot_is_preserved(self):
        ret = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"], capture_output=True, text=True,
        )
        self.assertEqual(ret.returncode, 0, ret.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_original_qssi_source_trees_are_unmodified(self):
        originals = {
            "Android.bp": ("100644", "blob", "0aff4678adcc86218b875766ad5a21dbbc893e23"),
            "Android.mk": ("100644", "blob", "65711611ccc6a3dd7f3a0a08e1438e148ef2d5ce"),
            "build": ("040000", "tree", "e464b9e76aabac4eab25d15f6a0aadf1c84fa261"),
            "dlkm": ("040000", "tree", "cf0ec8f8fb750b8354665f138a1dc8ff6a62b125"),
            "dtbtool": ("040000", "tree", "9b863288f3c50f2cd4b9a52717263bda9706a2c5"),
            "hidl": ("040000", "tree", "b3c527f9b42cdaf5fc7af23423802e0ee25390e2"),
            "image_generation_tool": ("040000", "tree", "e0c055b28dd77b38a6c4dd3bf78fc6952f2c8d0d"),
            "meta_image": ("040000", "tree", "24b9a5033b0e01f5497d77fdd203d7c4bdc0f8a1"),
            "packkernelimg": ("040000", "tree", "86ca4d9da36726da01ea845c6644a59ed7520ab5"),
            "vendor_framework_compatibility_matrix.xml": (
                "100644", "blob", "b7f6b292ed758adaeb29d45d62ef468db075cdc8"),
            "vndk": ("040000", "tree", "f4e8b1baecc8825a1d4bf078ca1664c93e367f04"),
        }
        for path, expected in originals.items():
            with self.subTest(path=path):
                self.assertEqual(entry("HEAD", path), expected)
                self.assertEqual(entry("HEAD", path), entry(ARCHIVE_COMMIT, path))

    def test_qssi_build_script_is_vendor_multiphase_not_standard_aosp(self):
        src = read("build/build.sh")
        self.assertIn("This script is mainly to compile QSSI targets", src)
        self.assertIn("QSSI_ONLY=", src)
        self.assertIn("TARGET_ONLY=", src)
        self.assertIn("TARGET_PRODUCT_MAPPING_QSSI=", src)
        self.assertIn("TARGET_MATCHING_QSSI", src)
        self.assertIn("BUILD_SH_VERSION=12", src)
        self.assertIn("qssi_64", src)
        self.assertIn("merged-", src)
        self.assertIn("vendor/qcom/opensource/core-utils/build/build.sh", read("build/build_image_standalone.py"))

    def test_qualcomm_qssi_soong_config_is_not_aosp_base_requirement(self):
        src = read("Android.bp")
        self.assertIn('name: "qssi_vs_vendor_cc_base"', src)
        self.assertIn('config_namespace: "qssi_vs_vendor"', src)
        self.assertIn('variables: ["qssi_or_vendor"]', src)
        self.assertIn('"qssi"', src)
        self.assertIn('"vendor"', src)
        self.assertIn("vendor/qcom/opensource/core-utils/Android.bp", src)

    def test_legacy_matrix_is_qualcomm_framework_extension_not_official_fcm(self):
        root = ET.fromstring(read("vendor_framework_compatibility_matrix.xml"))
        self.assertEqual(root.tag, "compatibility-matrix")
        self.assertEqual(root.attrib.get("type"), "framework")
        self.assertEqual(root.attrib.get("version"), "1.0")
        # This is a vendor-owned extension matrix without a shipping
        # AOSP17 platform FCM level. Never replace official platform matrices.
        self.assertNotIn("level", root.attrib)
        hals = root.findall("hal")
        self.assertGreater(len(hals), 40)
        self.assertTrue(any(h.get("format") == "hidl" for h in hals))
        self.assertTrue(any(h.get("format") == "aidl" for h in hals))

    def test_2023_perf2_aidl_is_interface_evolution_not_wholesale_import(self):
        root = ET.fromstring(read("vendor_framework_compatibility_matrix.xml"))
        entries = [h for h in root.findall("hal")
                   if h.findtext("name") == "vendor.qti.hardware.perf2"]
        self.assertEqual(len(entries), 1)
        perf = entries[0]
        self.assertEqual(perf.attrib.get("format"), "aidl")
        self.assertEqual(perf.attrib.get("optional"), "true")
        self.assertEqual(perf.findtext("version"), "1")
        self.assertIn("IPerf", [n.text for n in perf.findall("interface/name")])
        # No perf2 binary or service implementation is defined by this FCM.

    def test_legacy_vendor_board_rules_cannot_override_modern_platform(self):
        board = read("build/AndroidBoardCommon.mk")
        self.assertIn("BOARD_PREBUILT_DTBOIMAGE", board)
        self.assertIn("TARGET_OUT_VENDOR", board)
        self.assertIn("TARGET_MOUNT_POINTS_SYMLINKS", board)
        self.assertIn("device/qcom/$(TARGET_PRODUCT)/enforcement_override.mk", board)
        script = read("vendorsetup.sh")
        self.assertIn('export QTI_BUILDTOOLS_DIR="vendor/qcom/opensource/core-utils"', script)
        # QSSI board paths, properties and symlinks are not portable
        # platform-wide AOSP17 defaults.

    def test_old_sdllvm_lto_and_vndk_packaging_not_reenabled(self):
        sdllvm = read("build/sdllvm-lto-defs.mk")
        vndk = read("vndk/Android.mk")
        self.assertIn("SDCLANG_PATH", sdllvm)
        self.assertIn("llvm-ar", sdllvm)
        self.assertIn("-fuse-ld=gold", sdllvm)
        self.assertIn("BOARD_VNDK_VERSION", vndk)
        self.assertIn("vndk-sp-gen", vndk)

    def test_archived_dlkm_uses_vendor_legacy_kbuild_paths(self):
        src = read("dlkm/AndroidKernelModule.mk")
        self.assertIn("device/qcom/kernelscripts/kernel_definitions.mk", src)
        self.assertIn("$(TARGET_KERNEL_SOURCE)/AndroidKernel.mk", src)
        self.assertIn("$(TARGET_PREBUILT_INT_KERNEL)", src)
        self.assertIn("$(KERNEL_CROSS_COMPILE)", src)
        self.assertNotIn("vendor_boot", src)
        # No Linux kernel compilation is performed by this audit.

    def test_old_host_image_tools_do_not_replace_aosp_toolchain(self):
        img = read("image_generation_tool/Android.bp")
        dtb = read("dtbtool/Android.bp")
        meta = read("meta_image/Android.bp")
        self.assertIn("python_binary_host", img)
        self.assertIn('name: "image_generation_tool"', img)
        self.assertIn('name: "dtbTool"', dtb)
        self.assertIn('name: "meta_image"', meta)
        self.assertIn("packkernelimg", read("packkernelimg/Android.mk"))

    def test_historical_key_material_is_never_checked_out_or_used(self):
        # Metadata-only check for archived key-like object.
        # Do not open, copy, print or run old signing material.
        mode, kind, _ = entry("HEAD", "build/qcom.key")
        self.assertEqual((mode, kind), ("100644", "blob"))
        self.assertFalse((ROOT / "build/qcom.key").exists(),
                         "CI MUST exclude historical key-like archive material")
        # All AOSP17 release/dev signing needs independently controlled keys.

    def test_official_aosp17_owns_platform_build_vintf_boot_tools(self):
        root = ET.fromstring(reference("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = {node.get("path"): node.get("name")
                    for node in root.iter("project")}
        for path, name in GOOGLE_SOURCES.items():
            with self.subTest(path=path):
                self.assertEqual(projects[path], name)
        self.assertNotIn(LEGACY_PATH, projects)
        self.assertNotIn(LEGACY_NAME, projects.values())

    def test_selected_aosp17_manifest_entrypoint_is_unchanged(self):
        root = ET.fromstring(reference("PE_AOSP17_DEFAULT"))
        self.assertEqual([n.get("name") for n in root.findall("include")],
                         ["aosp17_pe_p2_kernel_configs.xml"])
        self.assertFalse(any(p.get("path") == LEGACY_PATH
                             or p.get("name") == LEGACY_NAME
                             for p in root.iter("project")))

    def test_no_device_tree_or_feature_work_is_imported(self):
        for path in ("device.mk", "BoardConfig.mk", "AndroidProducts.mk",
                     "device/xiaomi", "init.mondrian.rc"):
            self.assertFalse((ROOT / path).exists())
        # Present-stage CI never downloads any LF52406/LineageOS tree.

if __name__ == "__main__":
    unittest.main(verbosity=2)
