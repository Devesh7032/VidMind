import React, { useState } from 'react';
import { ArrowUp, Link as LinkIcon, Sparkles } from 'lucide-react';

export default function Composer({
  onSubmit,
  isLoading,
  isDarkMode,
  suggestions = []
}) {
  const [sourceUrl, setSourceUrl] = useState('');
  const [promptText, setPromptText] = useState('');

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!sourceUrl.trim() || !promptText.trim() || isLoading) return;

    onSubmit({
      source_url: sourceUrl.trim(),
      user_prompt: promptText.trim()
    });

    setPromptText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const applySuggestion = (sugg) => {
    setPromptText(sugg);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-3 px-4 pb-4 pt-2">
      {/* Suggestions Row */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 justify-center">
          {suggestions.map((sugg, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applySuggestion(sugg)}
              className={`text-[11px] px-3 py-1.5 rounded-full border transition-all cursor-pointer ${
                isDarkMode
                  ? 'bg-gray-900/80 hover:bg-gray-800 border-gray-800 text-purple-300'
                  : 'bg-white hover:bg-gray-100 border-gray-200 text-purple-700 shadow-sm'
              }`}
            >
              ✨ "{sugg}"
            </button>
          ))}
        </div>
      )}

      {/* ChatGPT-Style Modern Composer Container */}
      <form
        onSubmit={handleSubmit}
        className={`rounded-2xl border shadow-xl transition-all ${
          isDarkMode
            ? 'bg-[#111726] border-gray-800/90 focus-within:border-purple-500/80 focus-within:ring-1 focus-within:ring-purple-500/50'
            : 'bg-white border-gray-200 shadow-gray-200/50 focus-within:border-purple-500 focus-within:ring-1 focus-within:ring-purple-500/40'
        }`}
      >
        {/* URL Input Bar */}
        <div className={`flex items-center space-x-2 px-4 py-2.5 border-b ${
          isDarkMode ? 'border-gray-800/60' : 'border-gray-100'
        }`}>
          <LinkIcon size={15} className="text-purple-400 shrink-0" />
          <input
            type="text"
            placeholder="Paste YouTube video or playlist URL (e.g. https://www.youtube.com/watch?v=...)..."
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            disabled={isLoading}
            className={`w-full text-xs bg-transparent outline-none ${
              isDarkMode ? 'text-gray-100 placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
            }`}
          />
        </div>

        {/* Natural Prompt Area & Send Button */}
        <div className="p-3.5 flex items-end space-x-3">
          <textarea
            rows={2}
            placeholder="Tell VidMind what to extract (e.g. 'Extract all React code and organize into files with explanations')..."
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className={`flex-1 bg-transparent text-xs outline-none resize-none leading-relaxed ${
              isDarkMode ? 'text-gray-100 placeholder-gray-500' : 'text-gray-900 placeholder-gray-400'
            }`}
          />

          <button
            type="submit"
            disabled={isLoading || !sourceUrl.trim() || !promptText.trim()}
            className={`h-8 w-8 rounded-xl flex items-center justify-center transition-all cursor-pointer ${
              sourceUrl.trim() && promptText.trim() && !isLoading
                ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30'
                : (isDarkMode ? 'bg-gray-800 text-gray-600' : 'bg-gray-200 text-gray-400')
            }`}
          >
            {isLoading ? (
              <span className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            ) : (
              <ArrowUp size={16} />
            )}
          </button>
        </div>
      </form>

      <p className="text-[10px] text-gray-500 text-center">
        VidMind extracts grounded knowledge artifacts, code files, and study packages using Gemini 2.5.
      </p>
    </div>
  );
}
