import React, { useState } from 'react';
import { X, Bookmark, FolderPlus, Check } from 'lucide-react';

export default function SaveToLibraryModal({
  isOpen,
  onClose,
  collections,
  selectedCollectionId,
  onSelectCollection,
  onCreateCollection,
  onSave,
  saveStatusMsg,
  isDarkMode
}) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCollName, setNewCollName] = useState('');
  const [newCollDesc, setNewCollDesc] = useState('');

  if (!isOpen) return null;

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newCollName.trim()) return;
    await onCreateCollection(newCollName.trim(), newCollDesc.trim());
    setNewCollName('');
    setNewCollDesc('');
    setShowCreateForm(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className={`w-full max-w-md rounded-2xl border shadow-2xl overflow-hidden ${
        isDarkMode ? 'bg-[#0e1422] border-gray-800 text-gray-100' : 'bg-white border-gray-200 text-gray-900'
      }`}>
        {/* Header Bar */}
        <div className={`px-5 py-3.5 border-b flex items-center justify-between ${
          isDarkMode ? 'border-gray-800 bg-[#090d16]' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center space-x-2">
            <Bookmark className="text-emerald-400" size={18} />
            <h3 className="text-sm font-bold text-white">Save Knowledge to Library</h3>
          </div>
          <button
            onClick={onClose}
            className={`p-1 rounded-lg transition-colors ${
              isDarkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-200 text-gray-600'
            }`}
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {/* Select Collection */}
          <div>
            <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              Select Collection
            </label>
            <select
              value={selectedCollectionId}
              onChange={(e) => onSelectCollection(e.target.value)}
              className="w-full bg-[#0b0f19] border border-gray-800 rounded-xl px-3.5 py-2.5 text-xs text-white outline-none"
            >
              {collections.map((coll) => (
                <option key={coll.collection_id} value={coll.collection_id}>
                  📁 {coll.name} ({coll.items_count || 0} items)
                </option>
              ))}
            </select>
          </div>

          {/* Toggle Create Collection */}
          {!showCreateForm ? (
            <button
              type="button"
              onClick={() => setShowCreateForm(true)}
              className="text-xs text-purple-400 hover:text-purple-300 font-medium flex items-center space-x-1.5 cursor-pointer"
            >
              <FolderPlus size={14} />
              <span>+ Create New Collection</span>
            </button>
          ) : (
            <form onSubmit={handleCreate} className="bg-[#090d16] border border-gray-800 rounded-xl p-3 space-y-2">
              <input
                type="text"
                placeholder="Collection Name (e.g. React Tutorials)..."
                value={newCollName}
                onChange={(e) => setNewCollName(e.target.value)}
                className="w-full bg-[#050810] border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white outline-none"
              />
              <input
                type="text"
                placeholder="Description (optional)..."
                value={newCollDesc}
                onChange={(e) => setNewCollDesc(e.target.value)}
                className="w-full bg-[#050810] border border-gray-800 rounded-lg px-3 py-1.5 text-xs text-white outline-none"
              />
              <div className="flex justify-end space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-3 py-1 bg-gray-800 text-gray-300 rounded-lg text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg text-xs"
                >
                  Create
                </button>
              </div>
            </form>
          )}

          {saveStatusMsg && (
            <div className="text-xs font-semibold text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 p-2.5 rounded-xl text-center">
              {saveStatusMsg}
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-2 border-t border-gray-800/60">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-xl text-xs"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white font-bold rounded-xl text-xs shadow-lg"
            >
              Save to Library
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
