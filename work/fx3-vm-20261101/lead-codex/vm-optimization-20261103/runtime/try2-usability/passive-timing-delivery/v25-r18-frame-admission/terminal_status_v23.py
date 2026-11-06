"""Pure host terminal text from the immutable per-run receipt."""

def terminal_summary(receipt):
    if receipt['qemu_pid'] is None:
        status = '启动未完成：模拟器未启动；请核对失败回执。'
    elif not receipt['lifecycle_pass']:
        status = '试用已结束：收尾检查未全部通过；请核对进程、API16和双锁。'
    elif receipt['native_model_power_off_after_ready'] or receipt['native_shutdown_after_ready']:
        status = '试用已结束：观察到原生关机；本轮健康未通过，资源已回收。'
    elif receipt['health_pass']:
        status = '试用已结束：本轮健康检查通过，资源已回收。'
    else:
        status = '试用已结束：本轮健康检查未通过，资源已回收；请查阅回执。'
    return {'status': status, 'last_stop_cause': receipt['stop_cause'],
            'last_health_pass': bool(receipt['health_pass']),
            'last_lifecycle_pass': bool(receipt['lifecycle_pass']),
            'restart_requires_new_authorization': True}
