"""
Этапы пайплайна (сырой идентификатор + порядок для процента).

Согласовано с plan.md: этап 2.4 и далее.
"""

STAGE_FILE_UPLOAD = "file_upload"
STAGE_AUDIO_EXTRACTION = "audio_extraction"
STAGE_FRAME_ANALYSIS = "frame_analysis"
STAGE_TRANSCRIPTION = "transcription"
STAGE_TRANSCRIPT_CLEANING = "transcript_cleaning"
STAGE_MATERIAL_GENERATION = "material_generation"
STAGE_KB_PREPARATION = "kb_preparation"
STAGE_COMPLETED = "completed"

# Порядок: индекс 0..7 → оценка прогресса (8 сегментов)
ORDERED_STAGES: tuple[str, ...] = (
    STAGE_FILE_UPLOAD,
    STAGE_AUDIO_EXTRACTION,
    STAGE_FRAME_ANALYSIS,
    STAGE_TRANSCRIPTION,
    STAGE_TRANSCRIPT_CLEANING,
    STAGE_MATERIAL_GENERATION,
    STAGE_KB_PREPARATION,
    STAGE_COMPLETED,
)


def progress_for_stage_id(stage: str) -> int:
    """
    Процент 12..100 по индексу этапа (MVP, равные доли).
    """
    try:
        idx = ORDERED_STAGES.index(stage)
    except ValueError:
        return 0
    return int(round(100.0 * (idx + 1) / len(ORDERED_STAGES)))


def default_stage_for_uploaded() -> tuple[str, int]:
    """После загрузки файла — этап «загрузка» завершена, впереди остальное."""
    return (STAGE_FILE_UPLOAD, progress_for_stage_id(STAGE_FILE_UPLOAD))
