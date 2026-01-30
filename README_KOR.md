# LocalImgPdfOCR

LightOnOCR-2-1B 모델을 사용하여 문서에서 텍스트와 이미지를 추출하는 CLI 및 GUI 인터페이스를 갖춘 OCR 애플리케이션입니다.

![Demo GIF](media/demo.gif)

텍스트 전용 모드
![Text Only Mode](media/textonly.png)

텍스트 + 이미지 모드
![Text + Images Mode](media/withimg.png)


## 특징

- **이중 인터페이스**: 자동화를 위한 CLI, 대화형 사용을 위한 GUI 제공
- **원클릭 설정**: 가상 환경 생성 및 의존성 설치 자동화
- **배치 작업**: 여러 파일 대기열 추가, 대량 실행 및 결과를 ZIP으로 다운로드 가능
- **이미지 추출**: 문서에서 포함된 이미지를 자동으로 추출 (텍스트+이미지 모드)
- **PDF 지원**: 페이지 선택 및 미리보기가 포함된 다중 페이지 PDF 변환
- **스마트 장치 감지**: GPU 자동 감지 및 UI에서 수동 CPU 전환 기능
- **자동 모델 다운로드**: 시작 시 HuggingFace에서 모델을 자동으로 가져옴
- **체계적인 출력**: 모든 결과는 타임스탬프가 찍힌 디렉토리에 저장됨
- **파이프라인 준비**: 더 큰 워크플로우에 통합할 수 있는 모듈식 설계

## 빠른 시작

### Windows

1. **애플리케이션 실행**:
   ```bash
   # ocr.bat 더블 클릭 (GUI 실행)
   # 또는 명령줄에서:
   ocr.bat
   
   첫 실행 시 자동으로 수행되는 작업:
   - Python 가상 환경 생성
   - 모든 의존성 설치
   - HuggingFace에서 LightOnOCR-2-1B 및 LightOnOCR-2-1B-bbox 모델 다운로드
   - GUI 실행
   ```

### Linux/Mac

1. 가상 환경 생성 및 의존성 설치:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. 애플리케이션 실행:
   ```bash
   # GUI
   python -m pipeline.gui_module
   
   # CLI
   python -m pipeline.cli_module process <files>
   ```

## 사용법

### GUI 모드

1. **실행**: `ocr.bat` 더블 클릭
2. **모드 선택**: "Text Only" 또는 "Text + Images" 선택
3. **파일 추가**: "Add Files" 또는 "Add Folder" 클릭
4. **처리**: "Process Files" 클릭
5. **결과**: `output/YYYYMMDD_HHMMSS/` 디렉토리에서 출력 확인

### CLI 모드

```bash
# 단일 이미지 처리 (텍스트 전용)
ocr.bat process image.png

# 텍스트 + 이미지 모드
ocr.bat process document.pdf --mode text-img

# 특정 PDF 페이지 처리
ocr.bat process document.pdf --pages "1-5,7,10-12"

# 여러 파일 일괄 처리
ocr.bat process *.pdf *.jpg

# CPU 모드 강제 사용
ocr.bat process image.png --device cpu

# 상세 출력
ocr.bat process image.png --verbose
```

## 지원 형식

**이미지**: PNG, JPG, JPEG, WEBP, BMP, TIFF, TIF, GIF  
**문서**: PDF

## 처리 모드

### 텍스트 전용 모드 (Text Only Mode)
- `LightOnOCR-2-1B` 모델 사용
- 일반 텍스트 추출
- 더 빠른 처리 속도
- 출력: 텍스트가 포함된 마크다운 파일

### 텍스트 + 이미지 모드 (Text + Images Mode)
- `LightOnOCR-2-1B-bbox` 모델 사용
- 텍스트 및 이미지 추출
- 이미지 바운딩 박스 감지
- 포함된 이미지 자르기 및 저장
- 출력: 텍스트 및 이미지 참조가 포함된 마크다운 파일

## 출력 구조

```
output/
└── 20260128_194500/          # 대기열 타임스탬프
    ├── document_page_1.md    # 추출된 텍스트
    ├── document_page_2.md
    ├── image_1.png            # 추출된 이미지 (텍스트+이미지 모드)
    ├── image_2.png
    └── metadata.json          # 처리 메타데이터
```

## 파이프라인 통합

더 큰 데이터 파이프라인에 통합하려면 모듈을 직접 가져오세요:

```python
from pipeline.ocr_module import load_model, extract_text_only, extract_text_with_images
from pipeline.job_module import create_batch_jobs, process_batch
from pipeline.preprocessing_module import pdf_to_images, parse_page_selection

# 모델 한 번만 로드
model, processor, device, dtype = load_model("text_only")

# 단일 이미지 처리
text = extract_text_only("image.png", model=model, processor=processor)

# 배치 처리
jobs, timestamp, output_dir = create_batch_jobs(
    file_paths=["file1.pdf", "file2.png"],
    model_type="text_img",
    model=model,
    processor=processor
)
completed, failed = process_batch(jobs)
```

자세한 API 문서는 `PIPELINE_INTEGRATION.md`를 참조하세요.

## 설정

`pipeline/config.py`를 수정하여 다음을 사용자 정의할 수 있습니다:
- 모델 경로
- 지원 파일 형식
- PDF 렌더링 DPI
- OCR 생성 매개변수
- 출력 디렉토리 구조

## 요구 사항

- Python 3.8+
- CUDA 지원 GPU (선택 사항, 사용할 수 없는 경우 CPU 사용)
- 모델 및 가상 환경을 위한 약 12GB 디스크 공간
- 최소 4GB RAM (대용량 PDF의 경우 더 필요)

### GPU 지원 설정

**NVIDIA GPU 사용자:**

기본 `pip install torch`는 CPU 전용 PyTorch를 설치합니다. GPU 가속을 위해:

1. 진단 실행: `python check_cuda.py`
2. CUDA가 감지되지 않으면, CUDA 버전 PyTorch로 재설치하세요:
   ```bash
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

## 문제 해결

**문제**: GPU가 감지되지 않음 (CUDA 대신 CPU 표시)  
**해결**: `python check_cuda.py`를 실행하여 진단하세요. CUDA 지원 PyTorch를 설치해야 할 수 있습니다.

**문제**: 가상 환경 설정 실패  
**해결**: Python이 설치되어 있고 PATH에 있는지 확인하세요. `python --version`을 실행하여 확인하세요.

**문제**: 모델을 찾을 수 없음 오류  
**해결**: 모델이 `models/LightOnOCR-2-1B/` 및 `models/LightOnOCR-2-1B-bbox/`에 있는지 확인하세요.

**문제**: GPU 메모리 부족  
**해결**: `--device cpu` 플래그를 사용하거나 배치 크기를 줄이세요.

**문제**: PDF 변환 실패  
**해결**: PDF가 손상되지 않았는지 확인하세요. 먼저 PDF 리더에서 열어보세요.

## 라이선스

모델 라이선스 참조:
- LightOnOCR-2-1B: Apache License 2.0
- LightOnOCR-2-1B-bbox: Apache License 2.0

## 크레딧

Models by LightOn AI: https://huggingface.co/lightonai
