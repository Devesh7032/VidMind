import React, { useState, useEffect } from 'react';
import {
  X,
  FileCode,
  FileText,
  FolderArchive,
  Download,
  Copy,
  Check,
  Code,
  ExternalLink
} from 'lucide-react';

export default function CodeViewerModal({
  isOpen,
  onClose,
  artifactsResult,
  isDarkMode
}) {
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [copied, setCopied] = useState(false);
  const [fileContent, setFileContent] = useState('');
  const [isLoadingFile, setIsLoadingFile] = useState(false);

  useEffect(() => {
    if (artifactsResult && artifactsResult.artifacts && artifactsResult.artifacts.length > 0) {
      setSelectedArtifact(artifactsResult.artifacts[0]);
    }
  }, [artifactsResult]);

  useEffect(() => {
    if (selectedArtifact) {
      // If markdown preview content available on artifactsResult, use it for knowledge_pack.md
      if (selectedArtifact.filename.endsWith('.md') && artifactsResult.markdown_preview_content) {
        setFileContent(artifactsResult.markdown_preview_content);
      } else {
        fetchFileContent(selectedArtifact.download_url);
      }
    }
  }, [selectedArtifact]);

  const fetchFileContent = async (downloadUrl) => {
    setIsLoadingFile(true);
    try {
      const res = await fetch(downloadUrl);
      if (res.ok) {
        const text = await res.text();
        setFileContent(text);
      } else {
        setFileContent("// Unable to preview binary or compressed file directly. Use Download button.");
      }
    } catch {
      setFileContent("// Error fetching file content.");
    } finally {
      setIsLoadingFile(false);
    }
  };

  const handleCopyCode = () => {
    if (fileContent) {
      navigator.clipboard.writeText(fileContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen || !artifactsResult) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className={`w-full max-w-4xl h-[80vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden ${
        isDarkMode ? 'bg-[#0e1422] border-gray-800 text-gray-100' : 'bg-white border-gray-200 text-gray-900'
      }`}>
        {/* Header Bar */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          isDarkMode ? 'border-gray-800 bg-[#090d16]' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center space-x-2.5">
            <Code className="text-purple-400" size={20} />
            <div>
              <h3 className="text-sm font-bold text-white">Extracted Project Artifacts</h3>
              <p className="text-[11px] text-gray-400">Project ID: {artifactsResult.project_id}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className={`p-1.5 rounded-lg transition-colors ${
                isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
              }`}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Body: Left File Tree Sidebar + Right Code Preview */}
        <div className="flex-1 flex overflow-hidden">
          {/* File Tree Sidebar */}
          <div className={`w-64 border-r p-3 overflow-y-auto space-y-1 ${
            isDarkMode ? 'border-gray-800 bg-[#0b0f19]' : 'border-gray-200 bg-gray-50'
          }`}>
            <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider px-2 py-1">
              Files ({artifactsResult.total_artifacts})
            </h4>

            {artifactsResult.artifacts.map((art) => (
              <button
                key={art.artifact_id}
                onClick={() => setSelectedArtifact(art)}
                className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center space-x-2 transition-all ${
                  selectedArtifact?.artifact_id === art.artifact_id
                    ? (isDarkMode ? 'bg-purple-950/80 border border-purple-800 text-white font-medium' : 'bg-purple-100 border border-purple-300 text-purple-900 font-medium')
                    : (isDarkMode ? 'hover:bg-gray-800/60 text-gray-300' : 'hover:bg-gray-200 text-gray-700')
                }`}
              >
                {art.filename.endsWith('.zip') ? (
                  <FolderArchive size={14} className="text-amber-400 shrink-0" />
                ) : art.filename.endsWith('.md') ? (
                  <FileText size={14} className="text-indigo-400 shrink-0" />
                ) : (
                  <FileCode size={14} className="text-emerald-400 shrink-0" />
                )}
                <span className="truncate flex-1">{art.filename}</span>
              </button>
            ))}
          </div>

          {/* Code File Preview Area */}
          <div className="flex-1 flex flex-col bg-[#050810] text-gray-100 font-mono text-xs overflow-hidden">
            {/* File Actions Bar */}
            {selectedArtifact && (
              <div className="px-4 py-2.5 border-b border-gray-800/80 bg-[#090d16] flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-300 font-sans">
                  <span className="font-bold text-white text-xs">{selectedArtifact.filename}</span>
                  <span className="text-[10px] bg-gray-800 px-2 py-0.5 rounded border border-gray-700 text-gray-400">
                    {(selectedArtifact.file_size_bytes / 1024).toFixed(1)} KB
                  </span>
                </div>

                <div className="flex items-center space-x-2 font-sans">
                  <button
                    onClick={handleCopyCode}
                    className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
                  >
                    {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                    <span>{copied ? "Copied" : "Copy"}</span>
                  </button>
                  <a
                    href={selectedArtifact.download_url}
                    download
                    className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                  >
                    <Download size={13} />
                    <span>Download</span>
                  </a>
                </div>
              </div>
            )}

            {/* Code Content Container */}
            <div className="flex-1 p-4 overflow-auto leading-relaxed">
              {isLoadingFile ? (
                <div className="h-full flex items-center justify-center text-purple-400 text-xs font-sans animate-pulse">
                  Loading file preview...
                </div>
              ) : (
                <pre className="whitespace-pre-wrap font-mono text-xs text-gray-200">{fileContent}</pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
