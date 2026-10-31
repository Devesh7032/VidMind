import React from 'react';
import { X, Brain, CheckCircle, AlertTriangle, Lightbulb, Map, Target } from 'lucide-react';

export default function WorkspaceModal({
  isOpen,
  onClose,
  workspaceData,
  isLoading,
  isDarkMode
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className={`w-full max-w-4xl h-[85vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden ${
        isDarkMode ? 'bg-[#0e1422] border-gray-800 text-gray-100' : 'bg-white border-gray-200 text-gray-900'
      }`}>
        {/* Header Bar */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          isDarkMode ? 'border-gray-800 bg-[#090d16]' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center space-x-2.5">
            <Brain className="text-indigo-400" size={22} />
            <div>
              <h3 className="text-base font-bold text-white">Personal AI Knowledge Workspace</h3>
              <p className="text-xs text-gray-400">Concept Mastery, Knowledge Gaps, Learning Paths & Adaptive AI Tutor</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <X size={18} />
          </button>
        </div>

        {/* Workspace Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6 text-xs">
          {isLoading ? (
            <div className="py-20 text-center text-purple-400 text-xs animate-pulse">
              Analyzing knowledge graph, mastery levels, and gaps...
            </div>
          ) : workspaceData ? (
            <>
              {/* Mastery Counters */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-[#0b0f19] border border-gray-800 rounded-xl p-4 text-center">
                  <span className="text-3xl font-extrabold text-purple-400 block">{workspaceData.knowledge_profile.mastered_concepts_count}</span>
                  <span className="text-[11px] text-gray-400 uppercase font-semibold">Mastered Concepts</span>
                </div>
                <div className="bg-[#0b0f19] border border-gray-800 rounded-xl p-4 text-center">
                  <span className="text-3xl font-extrabold text-indigo-400 block">{workspaceData.knowledge_profile.practicing_concepts_count}</span>
                  <span className="text-[11px] text-gray-400 uppercase font-semibold">Practicing Concepts</span>
                </div>
                <div className="bg-[#0b0f19] border border-gray-800 rounded-xl p-4 text-center">
                  <span className="text-3xl font-extrabold text-emerald-400 block">{workspaceData.due_revisions_count}</span>
                  <span className="text-[11px] text-gray-400 uppercase font-semibold">Revisions Due Today</span>
                </div>
              </div>

              {/* Gaps & Recommendations */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="bg-[#0f1624] border border-purple-900/60 rounded-xl p-5 space-y-3">
                  <h4 className="font-bold text-purple-400 uppercase tracking-wider flex items-center space-x-1.5">
                    <AlertTriangle size={15} />
                    <span>Detected Knowledge Gaps</span>
                  </h4>
                  {workspaceData.recent_gaps.map((gap) => (
                    <div key={gap.gap_id} className="bg-[#0b101c] border border-gray-800 rounded-lg p-3 space-y-1">
                      <div className="flex items-center justify-between font-bold text-white">
                        <span>Missing: {gap.missing_concept}</span>
                        <span className="text-[9px] bg-red-950 text-red-300 px-2 py-0.5 rounded border border-red-800">{gap.gap_type}</span>
                      </div>
                      <p className="text-gray-300 leading-normal">{gap.reason}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-[#0f1624] border border-indigo-900/60 rounded-xl p-5 space-y-3">
                  <h4 className="font-bold text-indigo-400 uppercase tracking-wider flex items-center space-x-1.5">
                    <Lightbulb size={15} />
                    <span>Recommended Next Topics</span>
                  </h4>
                  {workspaceData.recommendations.map((rec) => (
                    <div key={rec.recommendation_id} className="bg-[#0b101c] border border-gray-800 rounded-lg p-3 space-y-1">
                      <div className="flex items-center justify-between font-bold text-white">
                        <span>{rec.title}</span>
                        <span className="text-[9px] bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800">{rec.type}</span>
                      </div>
                      <p className="text-gray-300 leading-normal">{rec.reason}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Learning Path */}
              {workspaceData.active_learning_path && (
                <div className="bg-[#0e1526] border border-gray-800 rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                    <h4 className="font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                      <Map size={15} className="text-purple-400" />
                      <span>Learning Path: {workspaceData.active_learning_path.target_goal}</span>
                    </h4>
                    <span className="text-gray-400 font-mono text-[10px]">Est: {workspaceData.active_learning_path.estimated_duration_minutes} mins</span>
                  </div>

                  <div className="space-y-2">
                    {workspaceData.active_learning_path.steps.map((step) => (
                      <div key={step.step_number} className="bg-[#070b14] border border-gray-800 rounded-lg p-3 flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className="h-5 w-5 rounded-full bg-purple-900 text-purple-200 flex items-center justify-center font-bold text-[10px]">
                            {step.step_number}
                          </span>
                          <div>
                            <h5 className="font-bold text-white">{step.topic_title}</h5>
                            <p className="text-gray-400 text-[11px] mt-0.5">{step.description}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                          step.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                          step.status === 'IN_PROGRESS' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                          'bg-gray-800 text-gray-400'
                        }`}>
                          {step.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
