import React, { useState } from 'react';

const PDFViewer = ({ fileUrl }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: `Search for all occurrences of: "${searchTerm}"`,
        }),
      });
      
      const result = await response.json();
      console.log('Search results:', result);
    } catch (error) {
      console.error('Search error:', error);
    }
  };

  return (
    <div className="h-full w-full flex flex-col">
      {/* Search Box */}
      <div className="flex items-center gap-2 p-4 border-b">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search in PDF..."
          className="flex-1 px-3 py-2 border rounded"
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Search
        </button>
      </div>
      
      {/* PDF Viewer */}
      <div className="flex-1">
        <iframe
          src={fileUrl}
          className="w-full h-full border-0"
          title="PDF Viewer"
        />
      </div>
    </div>
  );
};

export default PDFViewer;
