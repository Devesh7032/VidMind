import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import CodeViewerModal from './components/CodeViewerModal';
import SaveToLibraryModal from './components/SaveToLibraryModal';
import WorkspaceModal from './components/WorkspaceModal';
import AgentModal from './components/AgentModal';

export default function App() {
  // Theme & Layout State
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [sidebarSearchTerm, setSidebarSearchTerm] = useState('');

  // Conversation & Message State
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Active Extraction Job & Artifacts State
  const [activeProject, setActiveProject] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [artifactsResult, setArtifactsResult] = useState(null);

  // Collections & Save Modal State
  const [collections, setCollections] = useState([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState('');
  const [saveStatusMsg, setSaveStatusMsg] = useState('');
  const [showSaveModal, setShowSaveModal] = useState(false);

  // Workspace & Autonomous Agents Modal State
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [workspaceData, setWorkspaceData] = useState(null);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);

  const [showAgentModal, setShowAgentModal] = useState(false);
  const [activeAgentWorkflow, setActiveAgentWorkflow] = useState(null);
  const [isExecutingAgentWorkflow, setIsExecutingAgentWorkflow] = useState(false);

  // Code Viewer Modal State
  const [showCodeViewerModal, setShowCodeViewerModal] = useState(false);

  const exampleSuggestions = [
    "Extract all the React code and organize into component files",
    "Extract all formulas and mathematical equations into a cheat sheet",
    "Generate a complete technical interview preparation Q&A pack",
    "Extract all code implementations in C++ and Java with complexity analysis"
  ];

  // Helper error parser
  const parseSafeErrorMessage = async (res, defaultMsg) => {
    try {
      const text = await res.text();
      try {
        const json = JSON.parse(text);
        return json.detail || json.message || defaultMsg;
      } catch {
        return `Server Error (${res.status}): ${defaultMsg}`;
      }
    } catch {
      return defaultMsg;
    }
  };

  // Fetch past conversations
  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    }
  };

  // Fetch collections
  const fetchCollections = async () => {
    try {
      const res = await fetch('/api/collections');
      if (res.ok) {
        const data = await res.json();
        setCollections(data);
        if (data.length > 0 && !selectedCollectionId) {
          setSelectedCollectionId(data[0].collection_id);
        }
      }
    } catch (err) {
      console.error('Error fetching collections:', err);
    }
  };

  // Fetch artifacts for a project
  const fetchArtifactsSummary = async (projectId) => {
    try {
      const res = await fetch(`/api/projects/${projectId}/artifacts`);
      if (res.ok) {
        const data = await res.json();
        setArtifactsResult(data);
      }
    } catch (err) {
      console.error('Error fetching artifacts summary:', err);
    }
  };

  // Fetch Workspace Dashboard data
  const fetchWorkspaceData = async () => {
    setIsLoadingWorkspace(true);
    try {
      const res = await fetch('/api/intelligence/workspace');
      if (res.ok) {
        const data = await res.json();
        setWorkspaceData(data);
      }
    } catch (err) {
      console.error('Error fetching workspace dashboard:', err);
    } finally {
      setIsLoadingWorkspace(false);
    }
  };

  useEffect(() => {
    fetchConversations();
    fetchCollections();
  }, []);

  // Handle New Chat creation
  const handleNewChat = () => {
    setActiveConversation(null);
    setMessages([]);
    setActiveProject(null);
    setActiveJob(null);
    setArtifactsResult(null);
  };

  // Select an existing conversation from sidebar
  const handleSelectConversation = async (conv) => {
    setActiveConversation(conv);
    setActiveJob(null);
    setArtifactsResult(null);

    try {
      const msgsRes = await fetch(`/api/conversations/${conv.conversation_id}/messages`);
      if (msgsRes.ok) {
        const msgsData = await msgsRes.json();
        setMessages(msgsData);
      }
    } catch (err) {
      console.error('Error loading conversation messages:', err);
    }
  };

  // Handle submitting initial URL + Prompt to trigger extraction pipeline
  const handleSubmitPrompt = async ({ source_url, user_prompt }) => {
    setIsLoading(true);
    setActiveJob(null);
    setArtifactsResult(null);

    // 1. Create or ensure active conversation
    let currentConv = activeConversation;
    if (!currentConv) {
      try {
        const convRes = await fetch('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: `Extract: ${user_prompt.slice(0, 30)}...` })
        });
        if (convRes.ok) {
          currentConv = await convRes.json();
          setActiveConversation(currentConv);
          fetchConversations();
        }
      } catch (err) {
        console.error('Error creating conversation:', err);
      }
    }

    // 2. Optimistically add User message & initial Assistant message
    const userMsg = {
      message_id: `user_${Date.now()}`,
      role: 'user',
      content: user_prompt,
      source_url: source_url,
      created_at: new Date().toISOString()
    };

    const initialAckText = `Got it. I'll analyze the video content, extract the requested information, and reconstruct the knowledge artifacts for you.\n\n✓ Video link verified\n⏳ Preparing video content source...`;

    const assistantMsg = {
      message_id: `assist_${Date.now()}`,
      role: 'assistant',
      content: initialAckText,
      created_at: new Date().toISOString()
    };

    setMessages([userMsg, assistantMsg]);

    try {
      // 3. Create Project via backend API
      const projRes = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_url, user_prompt })
      });

      if (!projRes.ok) {
        const errStr = await parseSafeErrorMessage(projRes, 'Failed to validate video URL.');
        setMessages([userMsg, {
          message_id: `err_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ ${errStr}`,
          created_at: new Date().toISOString()
        }]);
        setIsLoading(false);
        return;
      }

      const projData = await projRes.json();
      setActiveProject(projData);

      // 4. Start Background Analysis Job
      const jobRes = await fetch(`/api/projects/${projData.project_id}/analyze`, {
        method: 'POST'
      });

      if (!jobRes.ok) {
        const errStr = await parseSafeErrorMessage(jobRes, 'Failed to start video processing job.');
        setMessages([userMsg, {
          message_id: `err_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ ${errStr}`,
          created_at: new Date().toISOString()
        }]);
        setIsLoading(false);
        return;
      }

      const jobData = await jobRes.json();
      setActiveJob({
        job_id: jobData.job_id,
        project_id: projData.project_id,
        status: jobData.status,
        progress_percent: 15,
        current_stage: projData.is_playlist ? 'Discovering playlist videos...' : 'Checking video source...',
        is_playlist: projData.is_playlist,
        total_videos: projData.playlist_metadata ? projData.playlist_metadata.total_videos : 1,
        completed_videos: 0,
        failed_videos: 0
      });

      // 5. Connect Real-time SSE Stream
      const eventSource = new EventSource(`/api/jobs/${jobData.job_id}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const streamData = JSON.parse(event.data);
          setActiveJob(streamData);

          if (streamData.status === 'COMPLETED' || streamData.status === 'PARTIALLY_FAILED') {
            eventSource.close();
            setIsLoading(false);
            fetchArtifactsSummary(projData.project_id);

            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: `Done. I've analyzed the video and reconstructed your extracted knowledge package.`
                };
              }
              return updated;
            });
          } else if (streamData.status === 'FAILED') {
            eventSource.close();
            setIsLoading(false);
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: `⚠️ Extraction failed: ${streamData.error_message || 'Unknown processing error.'}`
                };
              }
              return updated;
            });
          }
        } catch (err) {
          console.error('Error parsing SSE event data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('EventSource connection error:', err);
        eventSource.close();
        setIsLoading(false);
      };

    } catch (err) {
      console.error('Error submitting prompt:', err);
      setIsLoading(false);
    }
  };

  // Handle follow-up chat messages (after extraction or grounded Q&A)
  const handleSendFollowUp = async ({ user_prompt }) => {
    if (!user_prompt.trim()) return;

    let currentConv = activeConversation;
    if (!currentConv) {
      try {
        const convRes = await fetch('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: `Chat: ${user_prompt.slice(0, 30)}...` })
        });
        if (convRes.ok) {
          currentConv = await convRes.json();
          setActiveConversation(currentConv);
          fetchConversations();
        }
      } catch (err) {
        console.error('Error creating conversation for follow-up:', err);
      }
    }

    const tempUserMsg = {
      message_id: `user_${Date.now()}`,
      role: 'user',
      content: user_prompt,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    if (!currentConv) return;

    try {
      const res = await fetch(`/api/conversations/${currentConv.conversation_id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: user_prompt })
      });

      if (res.ok) {
        const assistMsg = await res.json();
        setMessages((prev) => [...prev, assistMsg]);
      } else {
        const errStr = await parseSafeErrorMessage(res, 'Failed to generate answer.');
        setMessages((prev) => [...prev, {
          message_id: `err_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ ${errStr}`,
          created_at: new Date().toISOString()
        }]);
      }
    } catch (err) {
      console.error('Error sending follow-up message:', err);
    }
  };

  // Save project to library
  const handleSaveToLibrary = async () => {
    if (!activeProject || !selectedCollectionId) return;
    setSaveStatusMsg('');

    try {
      const res = await fetch(`/api/projects/${activeProject.project_id}/save-to-library`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection_id: selectedCollectionId })
      });

      if (!res.ok) {
        const errStr = await parseSafeErrorMessage(res, 'Failed to save to library.');
        throw new Error(errStr);
      }

      const data = await res.json();
      setSaveStatusMsg(data.message || 'Successfully saved to My Knowledge!');
      setTimeout(() => {
        setShowSaveModal(false);
        setSaveStatusMsg('');
      }, 1500);
    } catch (err) {
      setSaveStatusMsg(`⚠️ ${err.message}`);
    }
  };

  // Create new collection
  const handleCreateCollection = async (name, description) => {
    try {
      const res = await fetch('/api/collections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
      });
      if (res.ok) {
        const created = await res.json();
        await fetchCollections();
        setSelectedCollectionId(created.collection_id);
      }
    } catch (err) {
      console.error('Error creating collection:', err);
    }
  };

  // Execute Phase 6 Autonomous Agent workflow
  const handleExecuteAgentWorkflow = async (goal, autonomy_level) => {
    setIsExecutingAgentWorkflow(true);
    setActiveAgentWorkflow(null);

    try {
      const res = await fetch('/api/agents/workflows/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, autonomy_level })
      });

      if (res.ok) {
        const data = await res.json();
        setActiveAgentWorkflow(data);
      }
    } catch (err) {
      console.error('Error executing agent workflow:', err);
    } finally {
      setIsExecutingAgentWorkflow(false);
    }
  };

  return (
    <div className={`min-h-screen flex text-gray-100 selection:bg-purple-600 selection:text-white font-sans ${
      isDarkMode ? 'bg-[#0b0f19]' : 'bg-white text-gray-900'
    }`}>
      {/* ChatGPT-Style Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversation?.conversation_id}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onOpenWorkspace={() => {
          fetchWorkspaceData();
          setShowWorkspaceModal(true);
        }}
        onOpenAgents={() => setShowAgentModal(true)}
        onOpenLibrary={() => {
          fetchCollections();
          setShowSaveModal(true);
        }}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        isDarkMode={isDarkMode}
        onToggleTheme={() => setIsDarkMode(!isDarkMode)}
        searchTerm={sidebarSearchTerm}
        onSearchChange={setSidebarSearchTerm}
      />

      {/* Main Conversation & Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <ChatView
          conversation={activeConversation}
          messages={messages}
          activeJob={activeJob}
          artifactsResult={artifactsResult}
          isLoading={isLoading}
          onSubmitPrompt={handleSubmitPrompt}
          onSendFollowUp={handleSendFollowUp}
          onOpenCodeViewer={() => setShowCodeViewerModal(true)}
          onOpenSaveModal={() => {
            fetchCollections();
            setShowSaveModal(true);
          }}
          onRetryJob={async () => {
            if (!activeJob) return;
            setIsLoading(true);
            try {
              const res = await fetch(`/api/jobs/${activeJob.job_id}/resume`, { method: 'POST' });
              if (res.ok) {
                const jobData = await res.json();
                setActiveJob(jobData);
              }
            } catch (err) {
              console.error('Error retrying job:', err);
            } finally {
              setIsLoading(false);
            }
          }}
          isDarkMode={isDarkMode}
          suggestions={exampleSuggestions}
        />
      </div>

      {/* Modals & Slide-over Drawers */}
      <CodeViewerModal
        isOpen={showCodeViewerModal}
        onClose={() => setShowCodeViewerModal(false)}
        artifactsResult={artifactsResult}
        isDarkMode={isDarkMode}
      />

      <SaveToLibraryModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        collections={collections}
        selectedCollectionId={selectedCollectionId}
        onSelectCollection={setSelectedCollectionId}
        onCreateCollection={handleCreateCollection}
        onSave={handleSaveToLibrary}
        saveStatusMsg={saveStatusMsg}
        isDarkMode={isDarkMode}
      />

      <WorkspaceModal
        isOpen={showWorkspaceModal}
        onClose={() => setShowWorkspaceModal(false)}
        workspaceData={workspaceData}
        isLoading={isLoadingWorkspace}
        isDarkMode={isDarkMode}
      />

      <AgentModal
        isOpen={showAgentModal}
        onClose={() => setShowAgentModal(false)}
        isDarkMode={isDarkMode}
        onExecuteWorkflow={handleExecuteAgentWorkflow}
        isExecuting={isExecutingAgentWorkflow}
        activeWorkflow={activeAgentWorkflow}
      />
    </div>
  );
}
