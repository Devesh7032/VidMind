import React, { useRef, useEffect, useState } from 'react';
import {
  Sparkles,
  Check,
  X as XIcon,
  Loader2,
  AlertTriangle,
  FileCode,
  FolderArchive,
  Download,
  Bookmark,
  Code,
  Bot,
  User,
  RotateCcw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import Composer from './Composer';

export default function ChatView({
  conversation,
  messages,
  activeJob,
  artifactsResult,
  isLoading,
  onSubmitPrompt,
  onSendFollowUp,
  onOpenCodeViewer,
  onOpenSaveModal,
  onRetryJob,
  isDarkMode,
  suggestions
}) {
  const messagesEndRef = useRef(null);
  const [showTechDetails, setShowTechDetails] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeJob, artifactsResult]);

  // If no conversation messages exist yet, show ChatGPT-style central empty state
  if (!messages || messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col justify-between overflow-y-auto">
        {/* Empty State Hero */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-xl mx-auto space-y-4">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-xl shadow-purple-600/30">
            <Sparkles size={28} />
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              What would you like me to extract?
            </h2>
            <p className="text-xs sm:text-sm text-gray-400 mt-2">
              Paste a YouTube video or playlist URL and describe what you need.
              VidMind creates offline Markdown notes, runnable code files, and study packs.
            </p>
          </div>
        </div>

        {/* Floating Composer Bar */}
        <Composer
          onSubmit={onSubmitPrompt}
          isLoading={isLoading}
          isDarkMode={isDarkMode}
          suggestions={suggestions}
        />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col justify-between overflow-hidden">
      {/* Messages Stream Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 max-w-3xl mx-auto w-full">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const isLastMessage = idx === messages.length - 1;
          const isJobFailed = activeJob && activeJob.status === 'FAILED';

          return (
            <div
              key={msg.message_id || idx}
              className={`flex items-start space-x-3 text-xs leading-relaxed ${
                isUser ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              {/* Avatar Icon */}
              <div
                className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-white shrink-0 shadow-md ${
                  isUser
                    ? 'bg-indigo-600'
                    : (isJobFailed && isLastMessage ? 'bg-red-600' : 'bg-gradient-to-tr from-purple-600 to-indigo-500 shadow-purple-600/20')
                }`}
              >
                {isUser ? <User size={16} /> : <Bot size={16} />}
              </div>

              {/* Message Bubble Container */}
              <div className={`flex-1 space-y-3 max-w-[85%] ${isUser ? 'text-right' : 'text-left'}`}>
                {/* User Prompt Message */}
                {isUser ? (
                  <div className="inline-block bg-purple-600 text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-md space-y-1.5 text-left">
                    {msg.source_url && (
                      <div className="text-[11px] bg-purple-700/70 text-purple-100 px-2.5 py-1 rounded-lg font-mono truncate max-w-xs border border-purple-500/40">
                        🔗 {msg.source_url}
                      </div>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ) : (
                  /* Assistant Response Message */
                  <div className={`rounded-2xl rounded-tl-none p-5 space-y-4 shadow-xl border ${
                    isDarkMode
                      ? 'bg-[#111726] border-gray-800 text-gray-100'
                      : 'bg-white border-gray-200 text-gray-900'
                  }`}>
                    {/* Assistant Natural Language Text */}
                    <div className="whitespace-pre-wrap leading-relaxed text-xs">
                      {msg.content}
                    </div>

                    {/* Live Processing Pipeline Checklist & Progress */}
                    {activeJob && isLastMessage && (
                      <div className={`rounded-xl p-4 space-y-3 border ${
                        isJobFailed
                          ? 'bg-[#180a0a] border-red-900/80 text-gray-200'
                          : 'bg-[#090d16] border-purple-900/60 text-gray-200'
                      }`}>
                        <div className="flex items-center justify-between">
                          <span className={`text-[11px] font-bold uppercase tracking-wider ${
                            isJobFailed ? 'text-red-400' : 'text-purple-400'
                          }`}>
                            {isJobFailed ? "⚠️ EXTRACTION STOPPED" : (activeJob.is_playlist ? "📚 Playlist Processing Pipeline" : "Processing Pipeline")}
                          </span>
                          {!isJobFailed && (
                            <span className="text-[10px] bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800 font-mono">
                              {activeJob.progress_percent || 0}%
                            </span>
                          )}
                        </div>

                        {/* Progress Bar (Only shown when job is active/running) */}
                        {!isJobFailed && (
                          <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden border border-gray-800">
                            <div
                              className="bg-gradient-to-r from-purple-500 to-indigo-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${activeJob.progress_percent || 0}%` }}
                            ></div>
                          </div>
                        )}

                        {/* Real Pipeline Stage Checklist */}
                        <div className="space-y-1.5 text-[11px]">
                          {/* Stage 1: Link & Metadata */}
                          <div className="flex items-center space-x-2 text-emerald-400 font-medium">
                            <Check size={14} />
                            <span>Link verified & metadata retrieved</span>
                          </div>

                          {/* Stage 2: Transcript */}
                          <div className={`flex items-center space-x-2 ${
                            !isJobFailed && (activeJob.progress_percent || 0) >= 30
                              ? 'text-emerald-400 font-medium'
                              : (isJobFailed ? 'text-emerald-400 font-medium' : 'text-purple-400')
                          }`}>
                            <Check size={14} />
                            <span>Transcript prepared</span>
                          </div>

                          {/* Stage 3: Visual Content Analysis */}
                          <div className={`flex items-center space-x-2 ${
                            !isJobFailed && (activeJob.progress_percent || 0) >= 50
                              ? 'text-emerald-400 font-medium'
                              : (isJobFailed ? 'text-emerald-400 font-medium' : 'text-gray-500')
                          }`}>
                            <Check size={14} />
                            <span>Visual content analyzed & code regions identified</span>
                          </div>

                          {/* Stage 4: File Reconstruction */}
                          <div className={`flex items-center space-x-2 ${
                            isJobFailed
                              ? 'text-red-400 font-bold'
                              : ((activeJob.progress_percent || 0) >= 85 ? 'text-emerald-400 font-medium' : ((activeJob.progress_percent || 0) >= 50 ? 'text-purple-400' : 'text-gray-500'))
                          }`}>
                            {isJobFailed ? (
                              <XIcon size={14} className="text-red-400 shrink-0" />
                            ) : ((activeJob.progress_percent || 0) >= 85 ? (
                              <Check size={14} />
                            ) : ((activeJob.progress_percent || 0) >= 50 ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <div className="h-3.5 w-3.5 rounded-full border border-gray-600" />
                            )))}
                            <span>Reconstructing progressive code files & validating syntax</span>
                          </div>
                        </div>

                        {/* Error Message & Retry Buttons on Failure */}
                        {isJobFailed && (
                          <div className="pt-2 border-t border-red-900/60 space-y-2.5">
                            <p className="text-xs text-red-200 leading-normal">
                              {activeJob.error_details?.message || activeJob.error_message || "I couldn't complete the extraction because the processing service encountered an error."}
                            </p>

                            {/* Expandable Technical Details */}
                            {activeJob.error_details?.technical_details && (
                              <div>
                                <button
                                  type="button"
                                  onClick={() => setShowTechDetails(!showTechDetails)}
                                  className="text-[10px] text-gray-400 hover:text-gray-300 flex items-center space-x-1 cursor-pointer font-mono"
                                >
                                  <span>Technical Details</span>
                                  {showTechDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                </button>
                                {showTechDetails && (
                                  <div className="mt-1 p-2 bg-[#0a0505] rounded border border-red-950 font-mono text-[10px] text-red-300 leading-relaxed">
                                    Code: {activeJob.error_details.code || 'ENCODING_ERROR'} | Stage: {activeJob.error_details.stage || 'RECONSTRUCTING'} | Detail: {activeJob.error_details.technical_details}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Action Buttons: Retry & View Completed Data */}
                            <div className="flex items-center space-x-2 pt-1">
                              <button
                                onClick={onRetryJob}
                                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl shadow-md flex items-center space-x-1.5 cursor-pointer"
                              >
                                <RotateCcw size={13} />
                                <span>Retry Extraction</span>
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Extracted Artifacts & Project Package Card */}
                    {artifactsResult && isLastMessage && (
                      <div className="bg-[#080e1a] border border-emerald-900/60 rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-gray-800/80 pb-2.5">
                          <div className="flex items-center space-x-2">
                            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span>
                            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                              ✨ Extracted Knowledge Package
                            </span>
                          </div>
                          <span className="text-[10px] text-gray-400 font-mono">
                            {artifactsResult.total_artifacts} files generated
                          </span>
                        </div>

                        {/* File Chips */}
                        <div className="flex flex-wrap gap-2">
                          {artifactsResult.artifacts.map((art) => (
                            <a
                              key={art.artifact_id}
                              href={art.download_url}
                              download
                              className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-gray-900 hover:bg-gray-800 text-gray-200 border border-gray-800 flex items-center space-x-1.5 transition-all"
                            >
                              {art.filename.endsWith('.zip') ? (
                                <FolderArchive size={13} className="text-amber-400" />
                              ) : (
                                <FileCode size={13} className="text-emerald-400" />
                              )}
                              <span>{art.filename}</span>
                            </a>
                          ))}
                        </div>

                        {/* Interactive Buttons */}
                        <div className="flex flex-wrap gap-2 pt-1">
                          <button
                            onClick={onOpenCodeViewer}
                            className="px-3.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-md flex items-center space-x-1.5 cursor-pointer"
                          >
                            <Code size={14} />
                            <span>Open Code Viewer</span>
                          </button>

                          <button
                            onClick={onOpenSaveModal}
                            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-md flex items-center space-x-1.5 cursor-pointer"
                          >
                            <Bookmark size={14} />
                            <span>Save to Library</span>
                          </button>

                          <a
                            href={artifactsResult.artifacts.find(a => a.filename.endsWith('.zip'))?.download_url || '#'}
                            download
                            className="px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 font-bold text-xs rounded-xl border border-gray-700 flex items-center space-x-1.5 transition-colors"
                          >
                            <Download size={14} />
                            <span>Download ZIP</span>
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Follow-up / Additional Input Composer */}
      <Composer
        onSubmit={onSendFollowUp}
        isLoading={isLoading}
        isDarkMode={isDarkMode}
        suggestions={[]}
      />
    </div>
  );
}
