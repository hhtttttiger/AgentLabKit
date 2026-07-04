import { useState } from 'react';
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
      title={mode === 'create' ? '创建 QA 对' : '编辑 QA 对'}
      onClose={handleClose}
      widthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !question.trim() || !answer.trim()}>
            {loading ? '处理中...' : mode === 'create' ? '创建' : '保存'}
          </Button>
        </div>
      }
    >
      <div className="space-y-5">
        <TextAreaField
          label="问题"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入问题内容"
        />
        <TextAreaField
          label="回答"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="输入回答内容"
        />
      </div>
    </Modal>
  );
}
