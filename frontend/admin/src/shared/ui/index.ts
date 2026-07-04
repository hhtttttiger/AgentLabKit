/**
 * Shared UI component library.
 *
 * Components are logically grouped by abstraction level (files stay at
 * ui/ root to preserve relative CSS / theme imports):
 *
 *   Primitives    — Button, Badge, Card, InlineMessage, Skeleton, ToolbarButton
 *   Composites    — DataTable, FilterToolbar, Modal, Drawer, FormModal, ConfirmDialog,
 *                    Pagination, RowActions, FormFields, JsonEditor, MetricStrip, EmptyState
 *   Layouts       — PageFrame, PageContent, SectionPageFrame,
 *                    ModuleLayoutShell, ManagementListFrame
 *   Overlays      — Toast, UserMenu, AccentPicker, LanguagePicker, ThemeToggle, ZoomSlider
 *   Charts        — SvgChart, AreaPath, LinePath, Bar, DonutSegment (./charts/)
 *
 * Import directly from the component file:
 *   import { Button } from '@/shared/ui/Button'
 *   import { DataTable } from '@/shared/ui/DataTable'
 */

// Primitives
export { Badge } from './Badge';
export { Button } from './Button';
export { Card } from './Card';
export { InlineMessage } from './InlineMessage';
export { Skeleton } from './Skeleton';
export { ToolbarButton } from './ToolbarButton';

// Composites
export { ConfirmDialog } from './ConfirmDialog';
export { DataTable } from './DataTable';
export { Drawer } from './Drawer';
export { EmptyState } from './EmptyState';
export { FilterToolbar } from './FilterToolbar';
export { FilterToolbarActions } from './FilterToolbarActions';
export { TextField, DateField, NumberField, SelectField, TextAreaField, ToggleField } from './FormFields';
export { FormModal } from './FormModal';
export { JsonEditor } from './JsonEditor';
export { MetricStrip } from './MetricStrip';
export { Modal } from './Modal';
export { Pagination } from './Pagination';
export { RowActions } from './RowActions';

// Layouts
export { ManagementListFrame } from './ManagementListFrame';
export { ModuleLayoutShell } from './ModuleLayoutShell';
export { PageContent } from './PageContent';
export { PageFrame } from './PageFrame';
export { SectionPageFrame } from './SectionPageFrame';

// Overlays
export { AccentPicker } from './AccentPicker';
export { LanguagePicker } from './LanguagePicker';
export { ThemeToggle } from './ThemeToggle';
export { ToastProvider, useToast, notify } from './Toast';
export { UserMenu } from './UserMenu';
export { ZoomSlider } from './ZoomSlider';
