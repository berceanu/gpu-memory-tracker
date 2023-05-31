"""Module containing various utility functions."""
import datetime
import logging
import subprocess
import time
import unicodedata
import re

import numpy as np

logger = logging.getLogger(__name__)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def normalize_to_interval(a, b, data):
    """Given the `data` array, normalize its values in the [a, b] interval."""
    d = np.atleast_1d(data.copy())
    norm_data = (b - a) * (d - d.min()) / (d.max() - d.min()) + a
    return norm_data


def first(s):
    """Return the first element from an ordered collection
    or an arbitrary element from an unordered collection.
    Raise StopIteration if the collection is empty.
    """
    return next(iter(s))


def corners(centers):
    """
    Given a 1d array of center positions, compute the positions of the edges
    between them.
    """
    lengths = np.diff(centers)
    inside_corners = centers[:-1] + lengths / 2
    leftmost_corner = centers[0] - lengths[0] / 2
    rightmost_corner = centers[-1] + lengths[-1] / 2
    c = np.insert(inside_corners, 0, leftmost_corner)
    corners = np.append(c, rightmost_corner)

    return corners


def latex_float(f):
    float_str = "{0:.2g}".format(f)
    if "e" in float_str:
        base, exponent = float_str.split("e")
        return r"{0} \times 10^{{{1}}}".format(base, int(exponent))
    else:
        return float_str


def modification_time(fname):
    return datetime.datetime.fromtimestamp(fname.stat().st_mtime)


def oldest_newest(paths):
    sorted_paths = sorted(list(paths), key=lambda p: modification_time(p))
    oldest = sorted_paths[-2]
    newest = sorted_paths[-1]
    return (oldest, modification_time(oldest)), (newest, modification_time(newest))


def all_equal(iterator):
    """Checks all np.ndarrays in iterator are equal."""
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(
        np.array_equal(np.atleast_1d(first), np.atleast_1d(rest)) for rest in iterator
    )


def round_to_nearest(x, base=50):
    return base * round(x / base)


def du(path):
    """Disk usage in human readable format (e.g. '2,1GB')"""
    return subprocess.check_output(["du", "-shx", path]).split()[0].decode("utf-8")


def seconds_to_hms(seconds):
    """
    Convert seconds to H:M:S format.
    Works for periods over 24H also.
    """
    return datetime.timedelta(seconds=seconds)


class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""


class Timer:
    def __init__(self):
        self._start_time = None

    def start(self):
        """Start a new timer"""
        if self._start_time is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it")

        self._start_time = time.perf_counter()

    def stop(self):
        """Stop the timer, and report the elapsed time"""
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        runtime = time.perf_counter() - self._start_time
        self._start_time = None

        return runtime


def nozzle_center_offset(distance):
    """
    Convert between distance from center of gas nozzle to distance from z = 0 point.
    """
    other_distance = np.subtract(3000.0e-6, distance)
    return other_distance


def ffmpeg_command(
    frame_rate: float = 10.0,  # CHANGEME
    input_files: str = "pic%04d.png",  # pic0001.png, pic0002.png, ...
    output_file: str = "test.mp4",
):
    """
    Build up the command string for running ``ffmpeg``.
    http://hamelot.io/visualization/using-ffmpeg-to-convert-a-set-of-images-into-a-video/

    :param frame_rate: desired video framerate, in fps
    :param input_files: shell-like wildcard pattern (globbing)
    :param output_file: name of video output
    :return: command to be executed in the shell for producing video from the input files
    """
    return (
        rf"ffmpeg -framerate {frame_rate} -pattern_type glob -i '{input_files}' "
        rf"-c:v libx264 -vf fps=25 -pix_fmt yuv420p {output_file}"
    )


def shell_run(*cmd, **kwargs):
    """
    Run the command ``cmd`` in the shell.

    :param cmd: the command to be run, with separate arguments
    :param kwargs: optional keyword arguments for ``Popen``, eg. shell=True
    :return: the shell STDOUT and STDERR
    """
    logger.info(cmd[0])
    stdout = (
        subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
        .communicate()[0]
        .decode("utf-8")
    )
    logger.info(stdout)
    return stdout


def main():
    """Main entry point."""
    print(ffmpeg_command())

    d = np.array([500, 750, 1000, 1250, 1500]) * 1e-6
    print(d)
    print(nozzle_center_offset(d))
    print(nozzle_center_offset(nozzle_center_offset(d)))

    t = Timer()
    t.start()

    time.sleep(5.0)

    runtime = t.stop()  # A few seconds later
    print(f"Elapsed time: {seconds_to_hms(runtime)}")

    print(f"Size of current working directory: {du('.')}")


if __name__ == "__main__":
    main()
