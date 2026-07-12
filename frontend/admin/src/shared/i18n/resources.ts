/**
 * i18n resource bundle — assembled from per-module locale files.
 *
 * Each locale lives in ./locales/<lang>/ with one file per namespace:
 *   common.ts       — shared UI strings (nav, actions, toast, etc.)
 *   <module>.ts     — one file per feature module
 *
 * Namespaces are loaded on demand via i18next's ns mechanism.
 *
 * To add a new locale:
 *  1. Create ./locales/<lang>/ with the same file structure
 *  2. Add the entry below
 *  3. Register it in frontendLocales.ts
 */
import { common as zhCNCommon } from './locales/zh-CN/common';
import { aiChat as zhCNAiChat } from './locales/zh-CN/aiChat';
import { agentManagement as zhCNAm } from './locales/zh-CN/agentManagement';
import { modelManagement as zhCNMm } from './locales/zh-CN/modelManagement';
import { glossary as zhCNGlossary } from './locales/zh-CN/glossary';
import { knowledgeBase as zhCNKb } from './locales/zh-CN/knowledgeBase';
import { modelMonitoring as zhCNMon } from './locales/zh-CN/modelMonitoring';
import { costAnalysis as zhCNCost } from './locales/zh-CN/costAnalysis';
import { observability as zhCNObs } from './locales/zh-CN/observability';
import { memory as zhCNMem } from './locales/zh-CN/memory';
import { evaluation as zhCNEval } from './locales/zh-CN/evaluation';
import { userManagement as zhCNUser } from './locales/zh-CN/userManagement';

import { common as enUSCommon } from './locales/en-US/common';
import { aiChat as enUSAiChat } from './locales/en-US/aiChat';
import { agentManagement as enUSAm } from './locales/en-US/agentManagement';
import { modelManagement as enUSMm } from './locales/en-US/modelManagement';
import { glossary as enUSGlossary } from './locales/en-US/glossary';
import { knowledgeBase as enUSKb } from './locales/en-US/knowledgeBase';
import { modelMonitoring as enUSMon } from './locales/en-US/modelMonitoring';
import { costAnalysis as enUSCost } from './locales/en-US/costAnalysis';
import { observability as enUSObs } from './locales/en-US/observability';
import { memory as enUSMem } from './locales/en-US/memory';
import { evaluation as enUSEval } from './locales/en-US/evaluation';
import { userManagement as enUSUser } from './locales/en-US/userManagement';

export const ALL_NAMESPACES = [
  'common',
  'aiChat',
  'agentManagement',
  'modelManagement',
  'glossary',
  'knowledgeBase',
  'modelMonitoring',
  'costAnalysis',
  'observability',
  'memory',
  'evaluation',
  'userManagement',
] as const;

export type Namespace = (typeof ALL_NAMESPACES)[number];

export const adminI18nResources = {
  'zh-CN': {
    common: zhCNCommon,
    aiChat: zhCNAiChat,
    agentManagement: zhCNAm,
    modelManagement: zhCNMm,
    glossary: zhCNGlossary,
    knowledgeBase: zhCNKb,
    modelMonitoring: zhCNMon,
    costAnalysis: zhCNCost,
    observability: zhCNObs,
    memory: zhCNMem,
    evaluation: zhCNEval,
    userManagement: zhCNUser,
  },
  'en-US': {
    common: enUSCommon,
    aiChat: enUSAiChat,
    agentManagement: enUSAm,
    modelManagement: enUSMm,
    glossary: enUSGlossary,
    knowledgeBase: enUSKb,
    modelMonitoring: enUSMon,
    costAnalysis: enUSCost,
    observability: enUSObs,
    memory: enUSMem,
    evaluation: enUSEval,
    userManagement: enUSUser,
  },
} as const;
