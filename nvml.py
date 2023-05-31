"""
Periodically polls all the GPUs and writes usage info
for all running Python processes to disk in CSV format.
Usage: python src/nvml.py > /dev/null 2>&1 &
"""
import pynvml
import pathlib
import datetime
import schedule


def job(gpu_count, out_file):
    for gpu in range(gpu_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu)
        processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
        supported_throttle_reasons = pynvml.nvmlDeviceGetSupportedClocksThrottleReasons(
            handle
        )
        throttle_reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
        for p in processes:
            mem_MiB = p.usedGpuMemory / 1024 / 1024

            time_stamp = datetime.datetime.now()
            uuid = pynvml.nvmlDeviceGetUUID(handle).decode("UTF-8")
            pow_draw_watt = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            gpu_util_percentage = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu

            throtttle_reasons = {
                "sw_power_cap": pynvml.nvmlClocksThrottleReasonSwPowerCap,
                "hw_slowdown": pynvml.nvmlClocksThrottleReasonHwSlowdown,
            }
            throtttle_state = dict()
            for name, mask in throtttle_reasons.items():
                if mask & supported_throttle_reasons:
                    if mask & throttle_reasons:
                        throtttle_state[name] = "ON"  # Active
                    else:
                        throtttle_state[name] = "OFF"  # Not Active

            with out_file.open("a") as f:
                f.write(
                    f"{time_stamp},{uuid},{p.pid},{mem_MiB:.0f},{pow_draw_watt:.0f},{gpu_util_percentage},{throtttle_state['sw_power_cap']},{throtttle_state['hw_slowdown']}\n"
                )


# TODO (possibly) spawn a separate background process and run together with signac project
# see https://schedule.readthedocs.io/en/stable/background-execution.html


def main():
    """Main entry point."""
    pynvml.nvmlInit()
    gpu_count = pynvml.nvmlDeviceGetCount()

    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = pathlib.Path.cwd() / f"nvml_{now}.csv"

    # write CSV header
    with out_file.open("w") as f:
        f.write(
            "time_stamp,gpu_uuid,pid,used_gpu_memory_MiB,used_power_W,GPU_Util_%,sw_power_cap,hw_slowdown\n"
        )

    schedule.every().minute.do(job, gpu_count=gpu_count, out_file=out_file)

    while True:
        schedule.run_pending()

    pynvml.nvmlShutdown()


if __name__ == "__main__":
    main()
