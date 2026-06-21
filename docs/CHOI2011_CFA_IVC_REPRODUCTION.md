# Choi et al. 2011 CFA IVC Reproduction

Target paper:

> Chang-Hee Choi, Jung-Ho Choi, and Heung-Kyu Lee. "CFA pattern identification of digital cameras using intermediate value counting." Proceedings of the 13th ACM Multimedia and Security Workshop (MM&Sec '11), 21-26, 2011. DOI: 10.1145/2037252.2037258.

## Reproduction Scope

This implementation reproduces the CFA pattern identification stage as a CLI tool:

- compute intermediate value counts by RGB channel and 2x2 parity position;
- score the four Bayer candidates: `RGGB`, `BGGR`, `GBRG`, `GRBG`;
- report the estimated Bayer pattern and its `GXXG`/`XGGX` green-position group;
- optionally compare the estimate with EXIF camera lookup and RAW container metadata.

## Core Files

- `backend/app/core/cfa_ivc.py`: Bayer candidate scoring from IVC counts.
- `backend/app/core/hue.py`: RGB loading and IVC count primitive.
- `backend/app/core/raw_develop.py`: optional RAW development and RAW Bayer metadata extraction.
- `backend/scripts/identify_cfa_cli.py`: command-line entrypoint.
- `backend/tests/test_cfa_ivc.py`: synthetic CFA-pattern checks.

## CLI

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg
```

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg --json
```

## Verification

```powershell
cd backend
python -m pytest
```
