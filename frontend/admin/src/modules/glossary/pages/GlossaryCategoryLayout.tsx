import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useGlossaryCategory } from '../resources/category/hooks';
import { ModuleLayoutShell } from '@/shared/ui/ModuleLayoutShell';

export function GlossaryCategoryLayout() {
  const { t } = useTranslation(['common', 'glossary']);
  const { categoryId } = useParams<{ categoryId: string }>();
  const navigate = useNavigate();
  const categoryQuery = useGlossaryCategory(categoryId);

  if (!categoryId) return <Navigate to="/glossary" replace />;

  const categoryName = categoryQuery.data?.name ?? t('glossary:category.fallbackTitle');

  const tabs = [
    { key: 'terms', label: t('glossary:category.sections.terms'), path: `/glossary/${categoryId}` },
  ];

  return (
    <ModuleLayoutShell
      eyebrow={t('glossary:category.eyebrow')}
      title={categoryName}
      sections={tabs}
      leading={
        <button
          onClick={() => navigate('/glossary')}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition hover:bg-state-hover hover:text-text"
          title={t('glossary:category.backToList')}
        >
          <ArrowLeft size={18} />
        </button>
      }
    />
  );
}
