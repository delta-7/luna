def closest_divisor(freq_base, freq_target, max_ppm=None):
    divisor = round(freq_base / freq_target)

    if divisor <= 0:
        raise ValueError("Output frequency is too high")

    ppm = 1000000 * ((freq_base / divisor) - freq_target) / freq_target
    if max_ppm is not None and ppm > max_ppm:
        raise ValueError("Output frequency deviation is too high ({} ppm)".format(ppm))

    return divisor
