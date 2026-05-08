# FNIRSI 2C53T Waveform Decoder

A Python utility for decoding and analyzing `.bin` waveform files exported by the FNIRSI 2C53T portable oscilloscope.

## Features

- Decode CH1 and CH2 waveform data
- Voltage conversion
- Timebase reconstruction
- Matplotlib waveform visualization
- Waveform statistics
- FFT spectrum analysis
- JSON export support

## Installation

Clone the repository:

```bash
git clone https://github.com/RafaelDiasCampos/FNIRSI-2C53T-Decoder.git
cd FNIRSI-2C53T-Decoder
```

Install dependencies:

```bash
pip install numpy matplotlib
```

## Usage

Basic waveform plotting (defaults to 1V and 1ms per division):

```bash
python decoder.py capture.bin
```

Specify voltage and time scales:

```bash
python decoder.py capture.bin -v 0.5 -t 20us
```

## Command Line Options

| Option                  | Description                            |
| ----------------------- | -------------------------------------- |
| `-v`, `--voltage_scale` | Voltage scale in volts/division        |
| `-t`, `--time_scale`    | Time scale (e.g. `10ms`, `20us`, `1s`) |
| `-w`, `--waveform`      | Plot waveform                          |
| `-s`, `--spectrum`      | Plot FFT spectrum                      |
| `-a`, `--analyze`       | Print waveform analysis                |
| `-e`, `--export FILE`   | Export waveform data to JSON           |


## Examples

Plot waveform:

```bash
python decoder.py capture.bin -v 500mV -t 100us -w
```

Analyze signal:

```bash
python decoder.py capture.bin -v 1.0 -t 1ms -a
```

Plot FFT spectrum:

```bash
python decoder.py capture.bin -v 1.0 -t 100us -s
```

Export decoded data:

```bash
python decoder.py capture.bin -e waveform.json
```

## Binary File Format

Manual analysis on the binary format used by the FNIRSI 2C53T indicates the following fields:

| Offset  | Length  | Description                     |
| ------- | ------- | ------------------------------- |
| `0x000` | `0x12D` | Channel 1 samples (301 samples) |
| `0x12D` | `0x12D` | Channel 2 samples (301 samples) |
| `0x25A` | `0x01`  | Channels turned on (Bit 1 -> Channel 1, Bit 2 -> Channel 2)|
| `0x25B` | `0x04`  | Unknown purpose (0x0000012D)                          |

Each channel sample is represented by a single unsigned byte, with a value between `0x1C` and `0xE4`.