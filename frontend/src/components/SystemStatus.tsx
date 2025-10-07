"use client";

import React, { useState, useEffect } from 'react';
import { getStatus } from '@/lib/api'; // Assuming getStatus is updated to fetch the new status endpoint

interface SystemStatusData {
  pipeline_status: string;
  initial_seeding_complete: boolean;
  last_data_update: string | null;
  last_analysis_update: string | null;
}

const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        // This will now call the new /api/status endpoint
        const data = await getStatus();
        setStatus(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch system status.');
        console.error(err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusMessage = () => {
    if (!status) return 'Loading status...';
    if (status.pipeline_status.startsWith('running')) {
      const task = status.pipeline_status.split(':')[1] || 'task';
      return `Processing: The ${task.replace('_', ' ')} is currently running.`;
    }
    if (status.pipeline_status.startsWith('failed')) {
      return 'Error: The last data pipeline task failed. Please check the logs.';
    }
    if (!status.initial_seeding_complete) {
      return 'System Initializing: Performing initial data download. This may take a while...';
    }
    return 'System Idle: All data is up-to-date.';
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="bg-gray-800 text-white p-4 rounded-lg shadow-lg">
      <h3 className="text-xl font-bold mb-2 font-orbitron">System Status</h3>
      {error && <p className="text-red-500">{error}</p>}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="col-span-1 md:col-span-3">
            <p className="font-semibold">Current Activity:</p>
            <p className="text-lg">{getStatusMessage()}</p>
          </div>
          <div>
            <p className="font-semibold">Last Data Update:</p>
            <p>{formatDate(status.last_data_update)}</p>
          </div>
          <div>
            <p className="font-semibold">Last Analysis:</p>
            <p>{formatDate(status.last_analysis_update)}</p>
          </div>
           <div>
            <p className="font-semibold">Initial Seeding:</p>
            <p>{status.initial_seeding_complete ? 'Complete' : 'In Progress'}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemStatus;