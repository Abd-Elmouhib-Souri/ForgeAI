import fs from "node:fs";
import path from "node:path";


const root = process.cwd();

const detailPath = path.join(
  root,
  "app",
  "projects",
  "[id]",
  "_components",
  "ProjectDetailClient.tsx"
);

const typesPath = path.join(
  root,
  "app",
  "projects",
  "[id]",
  "_types",
  "project-detail.types.ts"
);


// Line endings normalized: on Windows (git core.autocrlf) the sources are
// checked out with CRLF and the "\n\n" markers below would never match.
const detail = fs.readFileSync(
  detailPath,
  "utf8"
).replace(/\r\n/g, "\n");

const types = fs.readFileSync(
  typesPath,
  "utf8"
).replace(/\r\n/g, "\n");


const panelStart = detail.indexOf(
  "function ContextClarificationPanel"
);

const panelEnd = detail.indexOf(
  "\nexport default function ProjectDetailClient",
  panelStart
);

if (
  panelStart < 0 ||
  panelEnd < 0
) {
  throw new Error(
    "ContextClarificationPanel source not found"
  );
}

const panel = detail.slice(
  panelStart,
  panelEnd
);


const saveStart = detail.indexOf(
  "async function handleSaveClarifications"
);

const saveEnd = detail.indexOf(
  "\n\n  const needsClarification",
  saveStart
);

if (
  saveStart < 0 ||
  saveEnd < 0
) {
  throw new Error(
    "handleSaveClarifications source not found"
  );
}

const saveHandler = detail.slice(
  saveStart,
  saveEnd
);


const oldFrenchManualHint =
  "Modifiez la description avec les r\u00e9ponses ci-dessous, puis relancez l\u2019analyse.";

const oldEnglishManualHint =
  "Update the project description with the answers below, then relaunch the analysis.";


const checks = {
  directAnswerControl:
    panel.includes("<textarea"),

  structuredClarificationItemType:
    types.includes(
      "interface ClarificationItem"
    ) &&
    types.includes(
      'kind: ClarificationKind'
    ),

  readinessExposesClarificationItems:
    types.includes(
      "clarification_items?: ClarificationItem[]"
    ),

  durableClarificationContextType:
    types.includes(
      "interface ClarificationContextData"
    ) &&
    (
      types.split(
        "clarification_context?: ClarificationContextData | null"
      ).length - 1
    ) >= 2,

  readinessConsumesBackendItems:
    detail.includes(
      "readiness?.clarification_items"
    ),

  canonicalFieldIdentity:
    panel.includes(
      "answers[item.field]"
    ) &&
    panel.includes(
      "onAnswerChange("
    ) &&
    panel.includes(
      "item.field"
    ) &&
    !panel.includes(
      "onAnswerChange(item.question"
    ),

  boundedAnswerControl:
    panel.includes(
      "maxLength={4000}"
    ),

  dedicatedClarificationRoute:
    saveHandler.includes(
      "/clarifications"
    ),

  dedicatedPatchMutation:
    saveHandler.includes(
      "api.patch<ProjectAnalysisResponse>"
    ),

  canonicalPayload:
    saveHandler.includes(
      "{ answers }"
    ),

  consumesServerRevalidation:
    saveHandler.includes(
      "setAnalysis(res.data)"
    ) &&
    saveHandler.includes(
      "await fetchProject()"
    ),

  durableAnswerPrefill:
    detail.includes(
      "clarificationAnswersFromContext"
    ) &&
    detail.includes(
      "clarification_context"
    ),

  derivedDraftWithoutStateSyncEffect:
    detail.includes(
      "persistedClarificationAnswers"
    ) &&
    detail.includes(
      "clarificationDraft.projectId === id"
    ) &&
    detail.includes(
      "...persistedClarificationAnswers"
    ) &&
    detail.includes(
      "...clarificationDraft.answers"
    ) &&
    !detail.includes(
      "clarificationDraftDirty"
    ) &&
    !detail.includes(
      "setClarificationAnswers({});"
    ),

  clarificationSaveDoesNotLaunchAgents:
    !saveHandler.includes(
      "/analyze/start"
    ) &&
    !panel.includes(
      "/analyze/start"
    ) &&
    !panel.includes(
      "onStartAnalysis"
    ),

  normalAnalysisLaunchStillExists:
    detail.includes(
      "/analyze/start"
    ) &&
    detail.includes(
      "onStartAnalysis={handleStartAnalysis}"
    ),

  oldManualDescriptionInstructionRemoved:
    !detail.includes(
      oldFrenchManualHint
    ) &&
    !detail.includes(
      oldEnglishManualHint
    ),
};


let green = true;


for (const [name, ok] of Object.entries(checks)) {
  console.log(
    `${name.toUpperCase()} = ${ok}`
  );

  if (!ok) {
    green = false;
  }
}


if (!green) {
  console.error(
    "FRONTEND_CLARIFICATION_AUTHORITY_RED"
  );

  process.exit(1);
}


console.log(
  "FRONTEND_CLARIFICATION_AUTHORITY_GREEN"
);
