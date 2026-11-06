"""Host-only regression for the two distinct missing-native-evidence cases."""
from run_trial_v25_diag_r3 import native_input_deadline_error


def main():
    sent = {'sent_monotonic': 10.0}
    assert native_input_deadline_error(sent, 16, {}, False, False, 22.0) is None
    absent = native_input_deadline_error(sent, 16, {}, False, False, 22.001)
    assert '未见原生按下接收' in absent and '不会自动重发' in absent
    no_up = native_input_deadline_error(sent, 16, {}, True, False, 22.001)
    assert '未见发键线程的抬起完成回执' in no_up
    incomplete = native_input_deadline_error(sent, 16, {16: (0, 0x30)}, True, False, 22.001)
    assert '原程序按下/抬起接收证据不完整' in incomplete
    assert native_input_deadline_error(sent, 16, {16: (0, 0x30)}, True, True, 22.001) is None
    print('input deadline classification: absent/down/up/complete and no resend PASS')


if __name__ == '__main__':
    main()
