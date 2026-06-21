# CFA Pattern Identification Using Intermediate Value Counting

[English README](README.md)

다음 논문의 재현 코드입니다.

> Chang-Hee Choi, Jung-Ho Choi, and Heung-Kyu Lee. "CFA pattern identification of digital cameras using intermediate value counting." Proceedings of the 13th ACM Multimedia and Security Workshop (MM&Sec '11), 21-26, 2011. DOI: 10.1145/2037252.2037258.

## 개요

이 저장소는 intermediate value counting(IVC)을 이용해 디지털 카메라 이미지의 CFA pattern을 식별하는 CLI 구현입니다.

추정 대상 Bayer CFA pattern:

- `RGGB`
- `BGGR`
- `GBRG`
- `GRBG`

함께 보고하는 green-position group:

- `RGGB`, `BGGR` -> `XGGX`
- `GBRG`, `GRBG` -> `GXXG`

## 방법

각 RGB 채널에 대해 2x2 parity 위치별 non-intermediate pixel 수를 계산합니다. 한 pixel 값이 상하좌우 네 이웃의 값 범위 밖에 있으면 non-intermediate로 계산합니다.

각 Bayer 후보는 해당 후보의 R, G, B 위치와 정규화된 IVC count가 얼마나 잘 맞는지로 점수를 계산합니다.

```text
score(pattern) = sum normalized_count[channel_at_pattern_position, parity_position]
```

가장 높은 점수의 후보를 추정 CFA pattern으로 반환합니다. confidence는 1위와 2위 후보 점수 차이를 1위 점수로 나눈 상대 margin입니다.

## 설치

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 사용

저장소 root에서 실행합니다.

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg
```

RAW 파일은 `rawpy`/LibRaw를 통해 지원합니다.

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.NEF
```

전체 JSON 출력:

```powershell
$env:PYTHONPATH="$PWD\backend"
python backend\scripts\identify_cfa_cli.py path\to\image.jpg --json
```

## 출력

CLI 출력 항목:

- 입력 파일 종류와 크기
- 가능한 경우 EXIF camera lookup 결과
- 가능한 경우 RAW container Bayer pattern
- 추정 Bayer CFA pattern
- 추정 green-position group
- confidence score
- EXIF/RAW metadata와 IVC 추정값 사이의 conflict flag

## 테스트

```powershell
cd backend
python -m pytest
```

## 인용

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

## License

MIT. [LICENSE](LICENSE)를 참고하세요.
