"""Clean-room unit tests for macOS 26+ IOUSBHost Transport Guard, Senser v1/v2 & Jiritsu Auditor."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fx3_recovery.macos_usb_transport_guard import (
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    FX3_MODEL_ID,
    FX3_MSC_VID_PID,
    JIRITSU_BLOCK,
    JIRITSU_CODE_DEBUG,
    JIRITSU_CODE_FIRMUP,
    JIRITSU_CODE_FORMAT,
    JIRITSU_CODE_GET_FILE,
    JIRITSU_CODE_GET_FILE2,
    JIRITSU_CODE_MOUNT,
    JIRITSU_CODE_SET_FILE,
    JIRITSU_CODE_SET_FILE2,
    JIRITSU_CODE_SET_FILE_PATH,
    JIRITSU_PFUNC,
    K_IORETURN_EXCLUSIVE_ACCESS,
    K_IORETURN_SUCCESS,
    SONY_SERVICE_VID_PID,
    VENDOR_CONTROL_B_REQUEST,
    VENDOR_CONTROL_BM_REQUEST_TYPE,
    VENDOR_CONTROL_W_INDEX,
    VENDOR_CONTROL_W_VALUE,
    JiritsuCommand,
    MacOSUSBTransportSession,
    SenserChallenge,
    TransportState,
    audit_jiritsu_command,
    audit_jiritsu_sequence,
    classify_senser_challenge,
    compute_exclusive_access_backoff_ms,
)


class MacOSUSBTransportGuardTests(unittest.TestCase):
    def test_hard_locked_jiritsu_safety_flags(self) -> None:
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)

    def test_compute_exclusive_access_backoff_ms_schedule_and_cap(self) -> None:
        delays = [compute_exclusive_access_backoff_ms(i) for i in range(6)]
        self.assertEqual(delays, [50, 100, 200, 400, 800, 800])
        with self.assertRaises(ValueError):
            compute_exclusive_access_backoff_ms(-1)

    def test_session_happy_path_fx3_macos26_iousbhost_fallback_and_senser_v1(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        self.assertEqual(sess.attach_msc(vid_pid=FX3_MSC_VID_PID), TransportState.MSC_DETECTED)

        ok_q, status_q = sess.wait_for_msc_quiescence(waited_ms=400, driver_quiescent=True)
        self.assertTrue(ok_q)
        self.assertEqual(status_q, "MSC_QUIESCENT_READY")

        claim = sess.claim_interface([K_IORETURN_EXCLUSIVE_ACCESS, K_IORETURN_SUCCESS])
        self.assertTrue(claim.success)
        self.assertEqual(claim.active_backend, "IOUSBHost")
        self.assertEqual(claim.exclusive_access_retries, 1)
        self.assertEqual(claim.backoff_schedule_ms, [50])

        vctrl = sess.send_vendor_control()
        self.assertTrue(vctrl.success)
        self.assertEqual(vctrl.bm_request_type, VENDOR_CONTROL_BM_REQUEST_TYPE)
        self.assertEqual(vctrl.b_request, VENDOR_CONTROL_B_REQUEST)
        self.assertEqual(vctrl.w_value, VENDOR_CONTROL_W_VALUE)
        self.assertEqual(vctrl.w_index, VENDOR_CONTROL_W_INDEX)
        self.assertEqual(vctrl.retransmit_count, 0)

        auth = sess.authenticate_senser(SenserChallenge(senser_version=1, challenge_rounds=7))
        self.assertTrue(auth.supported)
        self.assertEqual(auth.service_vid_pid, SONY_SERVICE_VID_PID)
        self.assertEqual(sess.state, TransportState.SERVICE_MODE_ACTIVE)

        audit = sess.audit_jiritsu_flow(
            [
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_MOUNT),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE2),
            ]
        )
        self.assertTrue(audit.allowed)
        self.assertEqual(audit.status, "PERMITTED_READONLY_JIRITSU_FLOW")

    def test_session_rejects_unsupported_usb_vid_pid(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        with self.assertRaises(ValueError):
            sess.attach_msc(vid_pid="1234:5678")

    def test_session_blocks_claim_before_msc_quiescence_on_macos26(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc(vid_pid=FX3_MSC_VID_PID)
        claim = sess.claim_interface([K_IORETURN_SUCCESS])
        self.assertFalse(claim.success)
        self.assertEqual(claim.status, "BLOCKED_QUIESCENCE_REQUIRED")

    def test_session_blocks_insufficient_quiescence_wait_or_active_driver(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        ok1, msg1 = sess.wait_for_msc_quiescence(waited_ms=400, driver_quiescent=False)
        self.assertFalse(ok1)
        self.assertTrue(msg1.startswith("BLOCKED_MSC_DRIVER_ACTIVE"))

        ok2, msg2 = sess.wait_for_msc_quiescence(waited_ms=100, driver_quiescent=True)
        self.assertFalse(ok2)
        self.assertTrue(msg2.startswith("BLOCKED_MSC_DRIVER_ACTIVE"))

    def test_session_macos26_exclusive_access_backoff_exhaustion_fails_closed(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        claim = sess.claim_interface([K_IORETURN_EXCLUSIVE_ACCESS] * 4)
        self.assertFalse(claim.success)
        self.assertEqual(claim.status, "FAILED_CLOSED_EXCLUSIVE_ACCESS")
        self.assertEqual(claim.backoff_schedule_ms, [50, 100, 200, 400])
        self.assertEqual(sess.state, TransportState.FAILED_CLOSED_EXCLUSIVE_ACCESS)

    def test_session_unexpected_ioreturn_error_fails_closed(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        claim = sess.claim_interface([0xE00002C0])
        self.assertFalse(claim.success)
        self.assertEqual(claim.status, "BLOCKED_USB_CLAIM_ERROR")

    def test_vendor_control_requires_claimed_interface_and_exact_tuple(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        unclaimed = sess.send_vendor_control()
        self.assertFalse(unclaimed.success)
        self.assertEqual(unclaimed.status, "BLOCKED_UNCLAIMED_INTERFACE")

        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        sess.claim_interface([K_IORETURN_SUCCESS])
        bad_tuple = sess.send_vendor_control(w_value=0x1234)
        self.assertFalse(bad_tuple.success)
        self.assertEqual(bad_tuple.status, "BLOCKED_INVALID_VENDOR_CONTROL")

    def test_vendor_control_usb_stall_suppresses_retransmission(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        sess.claim_interface([K_IORETURN_SUCCESS])

        stalled = sess.send_vendor_control(usb_stall=True)
        self.assertFalse(stalled.success)
        self.assertTrue(stalled.usb_stall_detected)
        self.assertEqual(stalled.retransmit_count, 0)
        self.assertEqual(stalled.status, "STALL_ABORTED_NO_RETRANSMIT")
        self.assertEqual(sess.state, TransportState.STALL_ABORTED_NO_RETRANSMIT)

    def test_cannot_authenticate_senser_after_usb_stall(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        sess.claim_interface([K_IORETURN_SUCCESS])
        sess.send_vendor_control(usb_stall=True)

        auth = sess.authenticate_senser(SenserChallenge(senser_version=1, challenge_rounds=7))
        self.assertFalse(auth.supported)
        self.assertTrue(auth.fail_closed)
        self.assertEqual(auth.status, "BLOCKED_INVALID_TRANSPORT_STATE")

    def test_classify_senser_v1_supported_rounds_3_to_7(self) -> None:
        for rounds in (3, 5, 7):
            res = classify_senser_challenge(
                SenserChallenge(senser_version=1, challenge_rounds=rounds, model_name="ILME-FX3", model_id=FX3_MODEL_ID)
            )
            self.assertTrue(res.supported)
            self.assertFalse(res.fail_closed)
            self.assertEqual(res.service_vid_pid, SONY_SERVICE_VID_PID)

        for bad_rounds in (2, 8):
            bad = classify_senser_challenge(SenserChallenge(senser_version=1, challenge_rounds=bad_rounds))
            self.assertFalse(bad.supported)
            self.assertTrue(bad.fail_closed)
            self.assertEqual(bad.status, "BLOCKED_INVALID_SENSER_V1_ROUNDS")

    def test_classify_senser_v2_rsa_ilce7m5_fails_closed(self) -> None:
        res = classify_senser_challenge(
            SenserChallenge(
                senser_version=2,
                auth_scheme="rsa_signature",
                challenge_rounds=1,
                model_name="ILCE-7M5",
                rsa_modulus_bits=2048,
            )
        )
        self.assertFalse(res.supported)
        self.assertTrue(res.fail_closed)
        self.assertEqual(res.status, "BLOCKED_SENSER_V2_RSA_UNSUPPORTED")
        self.assertEqual(res.service_vid_pid, "NONE_FAIL_CLOSED")

    def test_session_senser_v2_blocks_subsequent_jiritsu_flow(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc(vid_pid="054C:0DA1", model_name="ILCE-7M5", model_id=0x99999999)
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        sess.claim_interface([K_IORETURN_SUCCESS])
        sess.send_vendor_control()

        auth = sess.authenticate_senser(
            SenserChallenge(senser_version=2, auth_scheme="rsa_signature", model_name="ILCE-7M5", rsa_modulus_bits=2048)
        )
        self.assertFalse(auth.supported)
        self.assertEqual(sess.state, TransportState.FAILED_CLOSED_SENSER_V2)

        flow = sess.audit_jiritsu_flow([JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE)])
        self.assertFalse(flow.allowed)
        self.assertEqual(flow.status, "BLOCKED_SERVICE_MODE_NOT_ACTIVE")

    def test_jiritsu_blocks_0x4003_format_and_0x4006_firmup(self) -> None:
        fmt = audit_jiritsu_command(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_FORMAT)
        self.assertFalse(fmt.allowed)
        self.assertEqual(fmt.status, "BLOCKED_DESTRUCTIVE_JIRITSU_FORMAT")

        firmup = audit_jiritsu_command(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_FIRMUP)
        self.assertFalse(firmup.allowed)
        self.assertEqual(firmup.status, "BLOCKED_DESTRUCTIVE_JIRITSU_FIRMUP")

    def test_jiritsu_blocks_debug_and_set_file_writes(self) -> None:
        dbg = audit_jiritsu_command(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_DEBUG)
        self.assertFalse(dbg.allowed)
        self.assertEqual(dbg.status, "BLOCKED_JIRITSU_CODE_EXECUTION")

        for write_code in (JIRITSU_CODE_SET_FILE, JIRITSU_CODE_SET_FILE2):
            res = audit_jiritsu_command(JIRITSU_PFUNC, JIRITSU_BLOCK, write_code)
            self.assertFalse(res.allowed)
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_JIRITSU_WRITE")

    def test_jiritsu_blocks_set_file_path_traversal_and_ld_so_preload(self) -> None:
        for bad_path in (
            "/tmp/jiritsu/../../etc/ld.so.preload",
            "/etc/ld.so.preload",
            "/setting/updater/mode",
            "relative/path",
            "/",
            "/tmp/jiritsu/" + ("a" * 510),
        ):
            res = audit_jiritsu_command(
                JIRITSU_PFUNC,
                JIRITSU_BLOCK,
                JIRITSU_CODE_SET_FILE_PATH,
                file_path=bad_path,
            )
            self.assertFalse(res.allowed, msg=f"Expected block for {bad_path!r}")

    def test_jiritsu_permits_readonly_tier0_capture_flow(self) -> None:
        audit = audit_jiritsu_sequence(
            [
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_MOUNT),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_SET_FILE_PATH, "/tmp/jiritsu/tier0_read.bin"),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE2),
            ]
        )
        self.assertTrue(audit.allowed)
        self.assertEqual(audit.status, "PERMITTED_READONLY_JIRITSU_FLOW")
        self.assertEqual(len(audit.permitted_codes), 4)
        self.assertEqual(audit.blocked_codes, [])

    def test_jiritsu_rejects_wrong_pfunc_or_block(self) -> None:
        bad_pfunc = audit_jiritsu_command(0x41, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE)
        self.assertFalse(bad_pfunc.allowed)
        self.assertEqual(bad_pfunc.status, "BLOCKED_INVALID_JIRITSU_TARGET")

        bad_block = audit_jiritsu_command(JIRITSU_PFUNC, 0x1002, JIRITSU_CODE_GET_FILE)
        self.assertFalse(bad_block.allowed)
        self.assertEqual(bad_block.status, "BLOCKED_INVALID_JIRITSU_TARGET")

    def test_jiritsu_hard_locks_allow_persistent_writes_false(self) -> None:
        audit = audit_jiritsu_sequence(
            [
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE),
                JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_FORMAT),
            ],
            allow_persistent_writes=True,
        )
        self.assertFalse(audit.allowed)
        self.assertFalse(audit.allow_persistent_writes)
        self.assertTrue(any("hard-locks it to False" in w for w in audit.warnings))

    def test_jiritsu_rejects_unknown_command_code_fail_closed(self) -> None:
        res = audit_jiritsu_command(JIRITSU_PFUNC, JIRITSU_BLOCK, 0x4099)
        self.assertFalse(res.allowed)
        self.assertEqual(res.status, "BLOCKED_UNKNOWN_JIRITSU_COMMAND")

    def test_session_state_history_audit_trail(self) -> None:
        sess = MacOSUSBTransportSession(macos_major=26)
        sess.attach_msc()
        sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
        sess.claim_interface([K_IORETURN_EXCLUSIVE_ACCESS, K_IORETURN_SUCCESS])
        sess.send_vendor_control()
        sess.authenticate_senser(SenserChallenge(senser_version=1, challenge_rounds=7))
        self.assertEqual(
            sess.history,
            [
                "DISCONNECTED",
                "MSC_DETECTED",
                "WAITING_MSC_QUIESCENCE",
                "CLAIM_BACKOFF",
                "IOUSBHOST_CLAIMED",
                "VENDOR_CONTROL_SENT",
                "SERVICE_MODE_ACTIVE",
            ],
        )


if __name__ == "__main__":
    unittest.main()
