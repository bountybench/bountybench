import React from 'react';
import './ResourceDict.css';

const ResourceDict = ({ resources }) => {
  return (
    <div className="workflow-resources">
      <h3>Workflow Resources</h3>
      {resources.map((resource) => (
        <div key={resource.id} className="resource-item">
          <h4>{resource.id}</h4>
          <p>Type: {resource.type}</p>
          {resource.config && (
            <details>
              <summary>Resource Config</summary>
              <pre>{JSON.stringify(resource.config, null, 2)}</pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
};

export default ResourceDict;