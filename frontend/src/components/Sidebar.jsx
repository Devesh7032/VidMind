import React from 'react';
import {
  MessageSquare,
  Plus,
  Search,
  BookOpen,
  Brain,
  Bot,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Sparkles,
  FolderArchive
} from 'lucide-react';

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onOpenWorkspace,
  onOpenAgents,
  onOpenLibrary,
  isCollapsed,
  onToggleCollapse,
  isDarkMode,
  onToggleTheme,
  searchTerm,
  onSearchChange
}) {
  // Group conversations by date
  const filtered = conversations.filter(c =>
    (c.title || '').toLowerCase().includes((searchTerm || '').toLowerCase())
  );

  const groupConversations = () => {
    const today = [];
    const yesterday = [];
    const older = [];

    const now = new Date();
    filtered.forEach(item => {
      const created = new Date(item.created_at || Date.now());
      const diffDays = Math.floor((now - created) / (1000 * 60 * 60 * 24));
      if (diffDays === 0) today.push(item);
      else if (diffDays === 1) yesterday.push(item);
      else older.push(item);
    });

    return { today, yesterday, older };
  };

  const { today, yesterday, older } = groupConversations();

  if (isCollapsed) {
    return (
      <aside className={`w-16 border-r flex flex-col items-center py-4 justify-between transition-all duration-300 z-20 ${
        isDarkMode ? 'bg-[#090d16] border-gray-800 text-gray-300' : 'bg-gray-50 border-gray-200 text-gray-700'
      }`}>
        <div className="flex flex-col items-center space-y-4">
          <button
            onClick={onToggleCollapse}
            title="Expand sidebar"
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <ChevronRight size={18} />
          </button>
          
          <button
            onClick={onNewChat}
            title="New Chat"
            className="p-2.5 rounded-xl bg-purple-600 text-white shadow-md hover:bg-purple-500 transition-all cursor-pointer"
          >
            <Plus size={18} />
          </button>

          <div className="w-8 border-t border-gray-800 my-1"></div>

          <button
            onClick={onOpenLibrary}
            title="My Knowledge Library"
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <BookOpen size={18} />
          </button>

          <button
            onClick={onOpenWorkspace}
            title="AI Knowledge Workspace"
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <Brain size={18} />
          </button>

          <button
            onClick={onOpenAgents}
            title="Autonomous AI Agents"
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <Bot size={18} />
          </button>
        </div>

        <div className="flex flex-col items-center space-y-3">
          <button
            onClick={onToggleTheme}
            title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className={`p-2 rounded-xl transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shadow-md">
            VM
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`w-64 border-r flex flex-col justify-between transition-all duration-300 z-20 ${
      isDarkMode ? 'bg-[#090d16] border-gray-800/80 text-gray-200' : 'bg-gray-50 border-gray-200 text-gray-800'
    }`}>
      {/* Sidebar Header */}
      <div className="p-3.5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-600/20">
              <Sparkles size={16} />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1">
                VidMind <span className="text-[10px] bg-purple-900/80 text-purple-300 px-1.5 py-0.2 rounded border border-purple-700/50 font-mono">2.5</span>
              </h1>
              <p className="text-[10px] text-gray-400">AI Video Knowledge Assistant</p>
            </div>
          </div>
          <button
            onClick={onToggleCollapse}
            title="Collapse sidebar"
            className={`p-1.5 rounded-lg transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <ChevronLeft size={16} />
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onNewChat}
          className="w-full py-2.5 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs shadow-md shadow-purple-600/20 flex items-center justify-between transition-all cursor-pointer"
        >
          <span className="flex items-center space-x-2">
            <Plus size={16} />
            <span>New Chat</span>
          </span>
          <span className="text-[10px] bg-purple-700/60 px-1.5 py-0.5 rounded font-mono">⌘K</span>
        </button>

        {/* Search Input */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className={`w-full text-xs rounded-xl pl-8 pr-3 py-2 outline-none transition-all ${
              isDarkMode
                ? 'bg-gray-900/90 border border-gray-800 text-gray-200 placeholder-gray-500 focus:border-purple-500'
                : 'bg-white border border-gray-300 text-gray-900 placeholder-gray-400 focus:border-purple-500'
            }`}
          />
        </div>
      </div>

      {/* Navigation Tools Row */}
      <div className="px-3 py-1.5 space-y-1">
        <button
          onClick={onOpenLibrary}
          className={`w-full px-2.5 py-2 rounded-xl text-xs font-medium flex items-center space-x-2.5 transition-colors cursor-pointer ${
            isDarkMode ? 'hover:bg-gray-800/80 text-gray-300' : 'hover:bg-gray-200 text-gray-700'
          }`}
        >
          <BookOpen size={15} className="text-purple-400" />
          <span>My Knowledge Library</span>
        </button>
        <button
          onClick={onOpenWorkspace}
          className={`w-full px-2.5 py-2 rounded-xl text-xs font-medium flex items-center space-x-2.5 transition-colors cursor-pointer ${
            isDarkMode ? 'hover:bg-gray-800/80 text-gray-300' : 'hover:bg-gray-200 text-gray-700'
          }`}
        >
          <Brain size={15} className="text-indigo-400" />
          <span>AI Knowledge Workspace</span>
        </button>
        <button
          onClick={onOpenAgents}
          className={`w-full px-2.5 py-2 rounded-xl text-xs font-medium flex items-center space-x-2.5 transition-colors cursor-pointer ${
            isDarkMode ? 'hover:bg-gray-800/80 text-gray-300' : 'hover:bg-gray-200 text-gray-700'
          }`}
        >
          <Bot size={15} className="text-emerald-400" />
          <span>Autonomous AI Workflows</span>
        </button>
      </div>

      <div className="w-full border-t border-gray-800/60 my-1"></div>

      {/* Conversation History List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4 text-xs">
        {today.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider px-2 mb-1.5">Today</h4>
            <div className="space-y-1">
              {today.map(c => (
                <button
                  key={c.conversation_id}
                  onClick={() => onSelectConversation(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center space-x-2 truncate transition-colors ${
                    activeConversationId === c.conversation_id
                      ? (isDarkMode ? 'bg-purple-950/60 border border-purple-800/50 text-white font-medium' : 'bg-purple-100 border border-purple-300 text-purple-900 font-medium')
                      : (isDarkMode ? 'hover:bg-gray-800/60 text-gray-300' : 'hover:bg-gray-200 text-gray-700')
                  }`}
                >
                  <MessageSquare size={14} className="shrink-0 text-purple-400" />
                  <span className="truncate flex-1">{c.title || 'Untitled Conversation'}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {yesterday.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider px-2 mb-1.5">Yesterday</h4>
            <div className="space-y-1">
              {yesterday.map(c => (
                <button
                  key={c.conversation_id}
                  onClick={() => onSelectConversation(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center space-x-2 truncate transition-colors ${
                    activeConversationId === c.conversation_id
                      ? (isDarkMode ? 'bg-purple-950/60 border border-purple-800/50 text-white font-medium' : 'bg-purple-100 border border-purple-300 text-purple-900 font-medium')
                      : (isDarkMode ? 'hover:bg-gray-800/60 text-gray-300' : 'hover:bg-gray-200 text-gray-700')
                  }`}
                >
                  <MessageSquare size={14} className="shrink-0 text-purple-400" />
                  <span className="truncate flex-1">{c.title || 'Untitled Conversation'}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {older.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider px-2 mb-1.5">Previous</h4>
            <div className="space-y-1">
              {older.map(c => (
                <button
                  key={c.conversation_id}
                  onClick={() => onSelectConversation(c)}
                  className={`w-full text-left px-2.5 py-2 rounded-xl flex items-center space-x-2 truncate transition-colors ${
                    activeConversationId === c.conversation_id
                      ? (isDarkMode ? 'bg-purple-950/60 border border-purple-800/50 text-white font-medium' : 'bg-purple-100 border border-purple-300 text-purple-900 font-medium')
                      : (isDarkMode ? 'hover:bg-gray-800/60 text-gray-300' : 'hover:bg-gray-200 text-gray-700')
                  }`}
                >
                  <MessageSquare size={14} className="shrink-0 text-purple-400" />
                  <span className="truncate flex-1">{c.title || 'Untitled Conversation'}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {filtered.length === 0 && (
          <p className="text-[11px] text-gray-500 text-center py-4">No conversations found.</p>
        )}
      </div>

      {/* Sidebar Footer */}
      <div className={`p-3 border-t flex items-center justify-between ${
        isDarkMode ? 'border-gray-800/80 bg-gray-950/40' : 'border-gray-200 bg-gray-100/60'
      }`}>
        <div className="flex items-center space-x-2.5">
          <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white text-[11px] font-bold shadow-sm">
            VM
          </div>
          <div>
            <div className="text-xs font-semibold text-white leading-tight">VidMind Pro</div>
            <div className="text-[10px] text-gray-400">Offline & Cloud AI</div>
          </div>
        </div>

        <button
          onClick={onToggleTheme}
          title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          className={`p-1.5 rounded-lg transition-colors ${
            isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
          }`}
        >
          {isDarkMode ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </aside>
  );
}
