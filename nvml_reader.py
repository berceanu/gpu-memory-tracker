"""
Reads GPU usage info from CSV file and plots it.
Saves the figure(s) as PNG file(s).
Usage: python nvml_reader.py filename.csv
"""
import collections.abc
import pathlib
from dataclasses import dataclass, field
from typing import Tuple

import numpy as np
import pandas as pd
import pynvml

from horizontal_bars_figure import FigureHorizontalBars, Tick


def get_gpus_in_csv(path_to_csv, gpus_on_machine):
    df = pd.read_csv(path_to_csv)
    csv_uuids = tuple(df["gpu_uuid"].unique())

    gpus_in_csv = list()

    for gpu in gpus_on_machine:
        if gpu.uuid in csv_uuids:
            gpus_in_csv.append(gpu)

    return GpuList(tuple(gpus_in_csv))


def min_len_unique_uuid(uuids):
    """Determine the minimum string length required for a UUID to be unique."""

    def length_of_longest_string(list_of_strings):
        return len(max(list_of_strings, key=len))

    uuid_length = length_of_longest_string(uuids)
    tmp = set()
    for i in range(uuid_length):
        tmp.clear()
        for _id in uuids:
            if _id[:i] in tmp:
                break
            else:
                tmp.add(_id[:i])
        else:
            break
    return i


def get_gpus_on_machine():
    """Populates the list of available GPUs on the machine."""
    pynvml.nvmlInit()
    gpu_count = pynvml.nvmlDeviceGetCount()

    gpus_on_machine = list()
    for gpu in range(gpu_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu)
        uuid = pynvml.nvmlDeviceGetUUID(handle).decode("UTF-8")
        mem_total = pynvml.nvmlDeviceGetMemoryInfo(handle).total / 1024 ** 2
        enforced_power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000
        device = GpuDevice(
            uuid=uuid,
            total_memory=int(mem_total),
            power_limit=int(enforced_power_limit),
        )
        gpus_on_machine.append(device)
    pynvml.nvmlShutdown()
    return GpuList(tuple(gpus_on_machine))


@dataclass
class GpuDevice:
    """Stores GPU properties, per device."""

    uuid: str  # eg, "GPU-1dfe3b5c-79a0-0422-f0d0-b22c6ded0af0"
    total_memory: int  # MiB (Mebibyte)
    power_limit: int  # Watt


@dataclass
class GpuList(collections.abc.Sequence):
    gpus: Tuple[GpuDevice]
    short_uuid_len: int = field(init=False)

    def __post_init__(self):
        self.short_uuid_len = min_len_unique_uuid(list(gpu.uuid for gpu in self))

    def __getitem__(self, key):
        return self.gpus.__getitem__(key)

    def __len__(self):
        return self.gpus.__len__()


def uuid_series(df, uuid, column):
    mask = df["gpu_uuid"].values == uuid
    return df.loc[mask, column]


def resampled_time_index(df, freq="5T", rounding="30T"):
    start_time = df.index[0].round(rounding)
    end_time = df.index[-1].round(rounding)
    return pd.date_range(start=start_time, end=end_time, freq=freq)


def reindex_time_series(series, new_index):
    resampled = series.resample(new_index.freq).mean()
    return resampled.reindex(new_index)


def generate_time_ticks(time_index, num_ticks=5):
    tick_positions = np.linspace(0.0, 1.0, num_ticks)
    start_time = time_index[0]
    end_time = time_index[-1]
    tick_labels = pd.date_range(start=start_time, end=end_time, periods=num_ticks)
    ticks = list()
    for position, label in zip(tick_positions, tick_labels):
        ticks.append(Tick(position, label.strftime("%H:%M")))
    return tuple(ticks)


def generate_y_labels(gpus_in_csv):
    s_uuid = list()
    for gpu in gpus_in_csv:
        s_uuid.append(gpu.uuid[: gpus_in_csv.short_uuid_len])
    return tuple(s_uuid)


def Y_matrix(gpus_in_csv, df, time_index, quantity):
    normalized_by = {
        "used_gpu_memory_MiB": "total_memory",
        "used_power_W": "power_limit",
    }[quantity]

    Y = np.zeros(shape=(len(gpus_in_csv), time_index.size))

    for count, gpu in enumerate(gpus_in_csv):
        s = uuid_series(df, gpu.uuid, quantity)
        r = reindex_time_series(s, time_index)
        Y[count] = r / getattr(gpu, normalized_by)

    return Y


def main():
    """Main entry point."""
    path_to_csv = pathlib.Path.cwd() / "nvml_20210228-165008.csv"

    gpus_on_machine = get_gpus_on_machine()
    gpus_in_csv = get_gpus_in_csv(path_to_csv, gpus_on_machine)

    # ----------------------------------------------------------------------------------

    df = pd.read_csv(path_to_csv)

    df["time_stamp"] = pd.to_datetime(df["time_stamp"])
    df.set_index("time_stamp", inplace=True)

    df["gpu_uuid"] = df["gpu_uuid"].astype("string")
    df["hw_slowdown"] = df["hw_slowdown"].astype("category")
    df["sw_power_cap"] = df["sw_power_cap"].astype("category")

    # ----------------------------------------------------------------------------------

    grouped = df.groupby(["gpu_uuid"])
    print(grouped[["used_power_W", "used_gpu_memory_MiB"]].agg(["max", "mean", "std"]))

    # ----------------------------------------------------------------------------------

    print(
        f"{path_to_csv.name} was recorded over the time interval from {df.index[0]} to {df.index[-1]}."
    )
    df = df.loc["2021-02-28 17:30":"2021-02-28 22:30"]

    # ----------------------------------------------------------------------------------

    Y_labels = generate_y_labels(gpus_in_csv)

    dti = resampled_time_index(df)
    X_ticks = generate_time_ticks(dti)

    # ----------------------------------------------------------------------------------

    def save_figure(quantity):
        suffix = {"used_gpu_memory_MiB": "mem", "used_power_W": "pow"}[quantity]

        Y = Y_matrix(gpus_in_csv=gpus_in_csv, df=df, time_index=dti, quantity=quantity)

        f = FigureHorizontalBars(
            X=np.linspace(start=0, stop=1, num=dti.size, endpoint=True),
            Y=Y,
            x_ticks=X_ticks,
            y_labels=Y_labels,
        )
        f.render()
        f.save(fname=path_to_csv.with_suffix(f".{suffix}.png"))

    # ----------------------------------------------------------------------------------

    save_figure("used_gpu_memory_MiB")
    save_figure("used_power_W")


if __name__ == "__main__":
    main()
