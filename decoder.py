import matplotlib.pyplot as plt
import numpy as np
import argparse
from pathlib import Path
from dataclasses import dataclass
from numpy.typing import NDArray
import re
import json

N_SAMPLES = 301
N_DIVISIONS_Y = 8
N_DIVISIONS_X = 12
ADC_MAX = 0xE4
ADC_MIN = 0x1C
ADC_RANGE = ADC_MAX - ADC_MIN
ADC_CENTER = (ADC_MAX + ADC_MIN) / 2.0
MINIMUM_FILE_SIZE = 2 * N_SAMPLES + 1
TIME_UNITS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
}

@dataclass
class WaveformData:
    ch01: NDArray[np.float32] | None | None
    ch02: NDArray[np.float32] | None
    time_values: NDArray[np.float32]
    voltage_lims: tuple[float, float]
    time_lims: tuple[float, float]
    metadata: bytes
    channels_on: tuple[bool, bool]
    sampling_rate: float = 0.0

def parse_time_scale(value: str) -> float:
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(s|ms|us|ns)", value.strip())

    if not match:
        raise argparse.ArgumentTypeError(f"Invalid time scale: '{value}'")

    magnitude = float(match.group(1))
    unit = match.group(2)

    return magnitude * TIME_UNITS[unit]

def decode_channel(channel_data: bytes, voltage_scale: float) -> np.ndarray:
    # Calculate voltage range and conversion factor based on the raw ADC values and the voltage scale
    voltage_range = N_DIVISIONS_Y * voltage_scale
    voltage_per_value = voltage_range / ADC_RANGE
    
    decoded_channel_data = (np.frombuffer(channel_data, dtype=np.uint8).astype(np.float32) - ADC_CENTER) * voltage_per_value
    
    return decoded_channel_data

def decode_metadata(metadata: bytes) -> tuple[bool, bool]:
    if not metadata:
        raise ValueError("Missing metadata")

    channels_on = metadata[0]
    
    ch01_on = (channels_on & 0x01) != 0
    ch02_on = (channels_on & 0x02) != 0
    
    return (ch01_on, ch02_on)

def read_waveform_file(filename: str, voltage_scale: float, time_scale: float) -> WaveformData:
    data = Path(filename).read_bytes()    
    if len(data) < MINIMUM_FILE_SIZE:
        raise ValueError("Invalid file size")

    # Extract channel data and metadata from the binary data
    ch01 = data[0:N_SAMPLES]
    ch02 = data[N_SAMPLES:2 * N_SAMPLES]
    metadata = data[2 * N_SAMPLES:]
    channels_on = decode_metadata(metadata)
    
    # Decode channel data if the channels are on, otherwise set to None
    ch01 = decode_channel(ch01, voltage_scale) if channels_on[0] else None
    ch02 = decode_channel(ch02, voltage_scale) if channels_on[1] else None
    
    # Calculate voltage and time limits based on the provided scales and divisions
    voltage_max = voltage_scale * N_DIVISIONS_Y / 2
    voltage_lims = (-voltage_max, voltage_max)
    time_lims = (0, time_scale * N_DIVISIONS_X)
    
    # Calculate time values for the x-axis and sampling rate
    total_time = time_scale * N_DIVISIONS_X
    sampling_rate = N_SAMPLES / (time_scale * N_DIVISIONS_X)
    time_values = np.linspace(0, total_time, N_SAMPLES, endpoint=False)
    
    waveform_data = WaveformData(
        ch01=ch01,
        ch02=ch02,
        time_values=time_values,
        voltage_lims=voltage_lims,
        time_lims=time_lims,
        metadata=metadata,
        channels_on=channels_on,
        sampling_rate=sampling_rate
    )
    
    return waveform_data

def plot_waveform(waveform_data: WaveformData):
    # Create plot
    plt.figure(figsize=(12, 4))
    
    # Plot channels
    if waveform_data.ch01 is not None:
        plt.plot(waveform_data.time_values, waveform_data.ch01, label="Channel 1", color='yellow')
    if waveform_data.ch02 is not None:
        plt.plot(waveform_data.time_values, waveform_data.ch02, label="Channel 2", color='blue')
    
    # Configure plot appearance
    plt.title("Waveform")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.ylim(waveform_data.voltage_lims)
    plt.xlim(waveform_data.time_lims)
    plt.minorticks_on()
    plt.grid(color='gray', linestyle='--', alpha=0.3)
    plt.grid(which="major", alpha=0.4)
    plt.grid(which="minor", alpha=0.15)
    plt.xticks(np.linspace(*waveform_data.time_lims, N_DIVISIONS_X + 1))
    plt.yticks(np.linspace(*waveform_data.voltage_lims, N_DIVISIONS_Y + 1))
    plt.tight_layout()
    plt.show()
    
def compute_fft(signal: NDArray[np.float32], sampling_rate: float):
    signal = signal - np.mean(signal)
    window = np.hanning(len(signal))
    
    fft_vals = np.fft.rfft(signal * window)
    freqs = np.fft.rfftfreq(len(signal), d=1 / sampling_rate)

    return freqs, np.abs(fft_vals)
    
def plot_spectrum(waveform_data: WaveformData):
    channels = [waveform_data.ch01, waveform_data.ch02]
    
    frequency_data = []
    for i, ch_on in enumerate(waveform_data.channels_on):
        if ch_on:
            freqs, magnitudes = compute_fft(channels[i], waveform_data.sampling_rate)
            frequency_data.append({
                "channel": i + 1,
                "frequencies": freqs,
                "magnitudes": magnitudes
            })

    fig, axs = plt.subplots(len(frequency_data), 1, figsize=(10, 4 * len(frequency_data)))
    if len(frequency_data) == 1:
        axs = [axs]  # Ensure axs is always a list for consistent indexing
        
    for i, freq_data in enumerate(frequency_data):
        axs[i].semilogy(freq_data["frequencies"], freq_data["magnitudes"])
        axs[i].set_xlabel("Frequency (Hz)")
        axs[i].set_ylabel("Magnitude")
        axs[i].set_title(f"Spectrum - Channel {freq_data['channel']}")
        axs[i].grid(True)
        
    plt.tight_layout()
    plt.show()
    
def analyze_waveform(waveform_data: WaveformData):
    channels = [waveform_data.ch01, waveform_data.ch02]
    
    print(f"Sampling Rate: {waveform_data.sampling_rate:.2f} Hz")
    for i, ch_on in enumerate(waveform_data.channels_on):
        print(f"Channel {i+1} is {'ON' if ch_on else 'OFF'}")
        
        if ch_on:
            print(f"  Min Voltage: {np.min(channels[i])} V")
            print(f"  Max Voltage: {np.max(channels[i])} V")
            print(f"  Mean Voltage: {np.mean(channels[i])} V")
            
            freqs_ch, magnitudes_ch = compute_fft(channels[i], waveform_data.sampling_rate)
            dominant_freq = freqs_ch[np.argmax(magnitudes_ch)]

            print(f"  Dominant Frequency: {dominant_freq:.2f} Hz")
            print(f"  RMS Voltage: {np.sqrt(np.mean(channels[i]**2))} V")
            print(f"  Peak-to-Peak Voltage: {np.ptp(channels[i])} V")
            print(f"  Standard Deviation: {np.std(channels[i])} V")
            
def export_waveform_data(waveform_data: WaveformData, output_filename: str):
    waveform_json = {
        "time_values": waveform_data.time_values.tolist(),
        "ch01": waveform_data.ch01.tolist() if waveform_data.ch01 is not None else None,
        "ch02": waveform_data.ch02.tolist() if waveform_data.ch02 is not None else None,
        "voltage_lims": waveform_data.voltage_lims,
        "time_lims": waveform_data.time_lims,
        "metadata": list(waveform_data.metadata),
        "channels_on": waveform_data.channels_on,
        "sampling_rate": waveform_data.sampling_rate
    }
    
    with open(output_filename, "w") as f:
        json.dump(waveform_json, f)

def main():
    parser = argparse.ArgumentParser(description="Plot waveform from binary file")
    parser.add_argument("filename", help="Path to the binary waveform file")
    parser.add_argument("-v", "--voltage_scale", type=float, help="Voltage scale in volts per division", default=1.0, required=False)
    parser.add_argument("-t", "--time_scale", type=parse_time_scale, help="Time scale in seconds per division (e.g. 10ms, 20us, 1s)", default="1ms", required=False)
    parser.add_argument("-a", "--analyze", action="store_true", help="Perform analysis of the waveform data")
    parser.add_argument("-s", "--spectrum", action="store_true", help="Plot the frequency spectrum of the waveform")
    parser.add_argument("-w", "--waveform", action="store_true", help="Plot the waveform data")
    parser.add_argument("-e", "--export", metavar="OUTPUT_FILE", help="Export waveform data to JSON file")
    args = parser.parse_args()    
    
    waveform_data = read_waveform_file(args.filename, args.voltage_scale, args.time_scale)
    
    if args.export:
        export_waveform_data(waveform_data, args.export)
    if args.analyze:
        analyze_waveform(waveform_data)
    if args.spectrum:
        plot_spectrum(waveform_data)
    if args.waveform:
        plot_waveform(waveform_data)
        
    if not (args.analyze or args.spectrum or args.waveform or args.export):
        plot_waveform(waveform_data)
    
if __name__ == "__main__":
    main()