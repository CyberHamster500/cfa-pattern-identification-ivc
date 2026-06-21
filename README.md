# CFA Pattern Identification Using Intermediate Value Counting

Reference implementation for:

> Chang-Hee Choi, Jung-Ho Choi, and Heung-Kyu Lee. "CFA pattern identification of digital cameras using intermediate value counting." Proceedings of the 13th ACM Multimedia and Security Workshop (MM&Sec '11), 21-26, 2011. DOI: 10.1145/2037252.2037258.

## Overview

This repository provides a command-line implementation of CFA pattern identification for digital camera images using intermediate value counting (IVC).

The program estimates one of the four Bayer CFA patterns:

- `RGGB`
- `BGGR`
- `GBRG`
- `GRBG`

It also reports the corresponding green-position group:

- `XGGX` for `RGGB` and `BGGR`
- `GXXG` for `GBRG` and `GRBG`

## Method

For each RGB channel, the implementation counts non-intermediate pixels at each 2x2 parity position. A pixel is treated as non-intermediate when its value is outside the range of its four horizontal/vertical neighbors.

Each Bayer candidate is scored by summing the normalized IVC counts aligned with that candidate's R, G, and B positions:

```text
score(pattern) = sum normalized_count[channel_at_pattern_position, parity_position]
```

The candidate with the largest score is returned as the estimated CFA pattern. The reported confidence is the relative margin between the best and second-best candidate.

## Installation

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

From the repository root:

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg
```

RAW files are supported through `rawpy`/LibRaw:

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.NEF
```

Full JSON output:

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg --json
```

## Output

The CLI reports:

- input file type and size;
- EXIF camera lookup result when available;
- RAW container Bayer pattern when available;
- estimated Bayer CFA pattern;
- estimated green-position group;
- confidence score;
- conflict flags between EXIF/RAW metadata and the IVC estimate.

## Tests

```powershell
cd backend
python -m pytest
```

## Citation

```bibtex
@inproceedings{choi2011cfa,
  title = {CFA pattern identification of digital cameras using intermediate value counting},
  author = {Choi, Chang-Hee and Choi, Jung-Ho and Lee, Heung-Kyu},
  booktitle = {Proceedings of the thirteenth ACM multimedia workshop on Multimedia and security},
  pages = {21--26},
  year = {2011},
  publisher = {ACM},
  doi = {10.1145/2037252.2037258}
}
```
