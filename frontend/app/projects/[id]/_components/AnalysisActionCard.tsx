"use client";

import type { AnalysisStatus } from "../_types/project-detail.types";

type AnalysisActionCardProps = {
  currentStatus: AnalysisStatus;
  progress: number;
  currentStep: string;
  isStartingAnalysis: boolean;
  analysisIsRunning: boolean;
  analysisMessage: string;
  publicAnalysisWarning: string;
  onStartAnalysis: () => void;
  copy: {
    running: string;
    launching: string;
    relaunch: string;
    launch: string;
  };
};

export default function AnalysisActionCard({
  currentStatus,
  progress,
  currentStep,
  isStartingAnalysis,
  analysisIsRunning,
  analysisMessage,
  publicAnalysisWarning,
  onStartAnalysis,
  copy,
}: AnalysisActionCardProps) {
  const showAnalysisMessage =
    Boolean(analysisMessage) && (analysisIsRunning || isStartingAnalysis);

  return (
    <div className="forge-card p-6">
      {showAnalysisMessage && (
        <p className="mb-5 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm font-semibold text-sky-700">
          {analysisMessage}
        </p>
      )}

      {publicAnalysisWarning && (
        <p className="mb-5 rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm font-semibold text-yellow-800">
          {publicAnalysisWarning}
        </p>
      )}

      <button
        type="button"
        className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
        onClick={onStartAnalysis}
        disabled={isStartingAnalysis || analysisIsRunning}
      >
        {analysisIsRunning
          ? `${copy.running} ${progress}%`
          : isStartingAnalysis
            ? copy.launching
            : currentStatus === "completed"
              ? copy.relaunch
              : copy.launch}
      </button>

      {analysisIsRunning && (
        <p className="mt-4 text-center text-sm font-semibold text-slate-500">
          {currentStep}
        </p>
      )}
    </div>
  );
}