import React, { useState } from 'react';
import { X, Bot, Rocket, CheckCircle, Clock, ShieldCheck } from 'lucide-react';

export default function AgentModal({
  isOpen,
  onClose,
  isDarkMode,
  onExecuteWorkflow,
  isExecuting,
  activeWorkflow
}) {
  const [goalInput, setGoalInput] = useState('');
  const [autonomyLevel, setAutonomyLevel] = useState('ASSISTED');

  const suggestions = [
    "Prepare me for a DSA interview using my saved knowledge.",
    "Analyze my knowledge gaps and build a personalized study roadmap.",
    "Turn everything I know into an interview cheat sheet package."
  ];

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!goalInput.trim() || isExecuting) return;
    onExecuteWorkflow(goalInput.trim(), autonomyLevel);
  };

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
            <Bot className="text-emerald-400" size={22} />
            <div>
              <h3 className="text-base font-bold text-white">Autonomous AI Agent Workflows</h3>
              <p className="text-xs text-gray-400">Task Planning, Multi-Agent Orchestration & Explainable Workflows</p>
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

        {/* Modal Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6 text-xs">
          {/* Goal Submission Form */}
          <div className="bg-[#111726] border border-purple-900/60 rounded-2xl p-5 space-y-4 shadow-xl">
            <label className="block text-xs font-bold text-purple-400 uppercase tracking-wider">
              Describe the high-level goal for the AI Agents to execute:
            </label>

            <form onSubmit={handleSubmit} className="flex items-center space-x-2">
              <input
                type="text"
                placeholder="e.g. 'Prepare me for a DSA interview'..."
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                disabled={isExecuting}
                className="flex-1 bg-[#0b0f19] border border-gray-800 focus:border-purple-500 rounded-xl px-4 py-3 text-xs text-white outline-none"
              />
              <select
                value={autonomyLevel}
                onChange={(e) => setAutonomyLevel(e.target.value)}
                className="bg-[#0b0f19] border border-gray-800 text-gray-300 text-xs rounded-xl px-3 py-3 outline-none font-mono"
              >
                <option value="ASSISTED">Assisted</option>
                <option value="AUTOMATIC">Automatic</option>
                <option value="MANUAL">Manual</option>
              </select>
              <button
                type="submit"
                disabled={isExecuting || !goalInput.trim()}
                className="px-5 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white font-bold text-xs rounded-xl shadow-lg cursor-pointer disabled:opacity-50 flex items-center space-x-1.5"
              >
                {isExecuting ? (
                  <>
                    <span className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    <span>Running...</span>
                  </>
                ) : (
                  <>
                    <Rocket size={14} />
                    <span>Run Goal</span>
                  </>
                )}
              </button>
            </form>

            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((sugg, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setGoalInput(sugg);
                    onExecuteWorkflow(sugg, autonomyLevel);
                  }}
                  className="text-[11px] bg-gray-900 hover:bg-gray-800 text-purple-300 border border-gray-800 rounded-lg px-2.5 py-1 transition-colors cursor-pointer"
                >
                  💡 "{sugg}"
                </button>
              ))}
            </div>
          </div>

          {/* Execution Output Result */}
          {activeWorkflow && (
            <div className="bg-[#0e1626] border border-emerald-900/60 rounded-2xl p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-gray-800 pb-2.5">
                <div>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">Task Execution Complete</span>
                  <h4 className="text-sm font-bold text-white mt-0.5">{activeWorkflow.high_level_goal}</h4>
                </div>
                <span className="text-[10px] bg-emerald-950 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-800 font-mono">
                  {activeWorkflow.overall_status}
                </span>
              </div>

              <p className="text-xs text-gray-300 bg-[#060a12] p-3.5 rounded-xl border border-gray-800 leading-relaxed">
                {activeWorkflow.final_output_summary}
              </p>

              {/* Execution Steps */}
              <div className="space-y-2">
                <h5 className="font-bold text-purple-400 uppercase tracking-wider text-[10px]">Multi-Agent Execution Log</h5>
                {activeWorkflow.execution_history.map((step, idx) => (
                  <div key={step.task_id} className="bg-[#0b101c] border border-gray-800 rounded-xl p-3 space-y-1 text-xs">
                    <div className="flex items-center justify-between font-bold text-white">
                      <span>{idx + 1}. {step.objective}</span>
                      <span className="text-[9px] bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800 font-mono">{step.agent_role}</span>
                    </div>
                    <p className="text-gray-400 italic text-[11px]">Why: "{step.explanation}"</p>
                    <div className="bg-[#050810] p-2 rounded border border-gray-800 text-gray-300 text-[11px]">
                      {step.output_summary}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
