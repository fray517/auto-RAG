/**
 * Идентификаторы этапов (как в backend `pipeline_stages.ORDERED_STAGES`).
 * Порядок совпадает с plan.md, шаг 2.4.
 */
export const STAGE_ORDER = [
  'file_upload',
  'audio_extraction',
  'frame_analysis',
  'transcription',
  'transcript_cleaning',
  'material_generation',
  'kb_preparation',
  'completed',
] as const

export type StageId = (typeof STAGE_ORDER)[number]

export const STAGE_LABELS_RU: Record<StageId, string> = {
  file_upload: 'Загрузка файла',
  audio_extraction: 'Извлечение аудио',
  frame_analysis: 'Слайды выбираются вручную',
  transcription: 'Транскрибация',
  transcript_cleaning: 'Очистка транскрипции',
  material_generation: 'Генерация материалов',
  kb_preparation: 'Подготовка к добавлению в базу',
  completed: 'Завершено',
}

export function indexOfStage(stage: string): number {
  const i = STAGE_ORDER.indexOf(stage as StageId)
  return i === -1 ? 0 : i
}
