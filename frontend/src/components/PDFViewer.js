import React from 'react';

const PDFViewer = ({ fileUrl }) => {
  return (
    <div className="h-full w-full">
      <iframe
        src={fileUrl}
        className="w-full h-full border-0"
        title="PDF Viewer"
      />
    </div>
  );
};

export default PDFViewer;
