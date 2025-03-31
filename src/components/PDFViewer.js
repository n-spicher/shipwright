import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const PDFViewer = ({ fileUrl }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [loading, setLoading] = useState(true);
  const [pageInput, setPageInput] = useState('1');

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const changePage = (offset) => {
    const newPageNumber = pageNumber + offset;
    if (newPageNumber >= 1 && newPageNumber <= numPages) {
      setPageNumber(newPageNumber);
      setPageInput(newPageNumber.toString());
    }
  };

  const handlePageInputChange = (e) => {
    setPageInput(e.target.value);
  };

  const handlePageInputSubmit = (e) => {
    e.preventDefault();
    const page = parseInt(pageInput, 10);
    if (!isNaN(page) && page >= 1 && page <= numPages) {
      setPageNumber(page);
    } else {
      setPageInput(pageNumber.toString());
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-center items-center mb-4">
        <div className="flex space-x-4">
          <button 
            onClick={() => changePage(-1)} 
            disabled={pageNumber <= 1}
            className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          <form onSubmit={handlePageInputSubmit} className="flex items-center">
            <div className="flex items-center">
              <input
                type="text"
                value={pageInput}
                onChange={handlePageInputChange}
                className="w-16 px-2 py-1 text-sm text-center border rounded"
              />
              <span className="whitespace-nowrap ml-2">
                of {numPages || '--'}
              </span>
            </div>
          </form>
          
          <button 
            onClick={() => changePage(1)} 
            disabled={pageNumber >= numPages}
            className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>

      <div 
        className="flex-1 overflow-auto flex justify-center items-start bg-gray-800 rounded-md p-4"
      >
        {loading && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white mb-4"></div>
            <p className="text-white">Loading PDF...</p>
          </div>
        )}
        
        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={(error) => {
            console.error("Error loading PDF:", error);
            setLoading(false);
          }}
          loading={<></>} // Custom loading component is handled above
        >
          <Page 
            pageNumber={pageNumber} 
            renderTextLayer={false}
            renderAnnotationLayer={false}
            scale={1.0}
          />
        </Document>
      </div>
    </div>
  );
};

export default PDFViewer;
