import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '@/shared/ui/Modal';
import { Button } from '@/shared/ui/Button';
import { TextAreaField } from '@/shared/ui/FormFields';
import type { KbDocumentView } from '../../../lib/contracts';

export function QaPairEditor({
  open,
  mode,
  initialValue,
  loading,
  onSubmit,
  onClose,
}: {
  open: boolean;
  mode: 'create' | 'edit';
  initialValue: KbDocumentView | null;
  loading: boolean;
  onSubmit: (data: { question: string; answer: string }) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation(['common', 'knowledgeBase']);
  const [question, setQuestion] = useState(initialValue?.qaQuestion ?? '');
  const [answer, setAnswer] = useState(initialValue?.qaAnswer ?? '');

  const handleClose = () => {
    setQuestion('');
    setAnswer('');
    onClose();
  };

  const handleSubmit = () => {
    if (!question.trim() || !answer.trim()) return;
    onSubmit({ question: question.trim(), answer: answer.trim() });
  };

  return (
    <Modal
      open={open}
      title={mode === 'create' ? t('knowledgeBase:qaEditor.titleCreate') : t('knowledgeBase:qaEditor.titleEdit')}
      onClose={handleClose}
      widthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            {t('common:actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !question.trim() || !answer.trim()}>
            {loading
              ? t('common:states.processing')
              : mode === 'create'
                ? t('common:actions.create')
                : t('common:actions.save')}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        <TextAreaField
          label={t('knowledgeBase:qaEditor.question')}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t('knowledgeBase:qaEditor.questionPlaceholder')}
        />
        <TextAreaField
          label={t('knowledgeBase:qaEditor.answer')}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder={t('knowledgeBase:qaEditor.answerPlaceholder')}
        />
      </div>
    </Modal>
  );
}
