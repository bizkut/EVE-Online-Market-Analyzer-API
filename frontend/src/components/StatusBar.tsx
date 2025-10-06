'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStatus } from '@/lib/api';
import { Wifi, WifiOff, Clock } from 'lucide-react';

const StatusBar = () => {
  const { data: status, error } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
    refetchInterval: 300000, // Refetch every 5 minutes
  });

  const isOnline = status && !error;

  return (
    <footer className="bg-[#161b22] p-4 text-center text-sm border-t border-gray-700 text-gray-400">
      <div className="flex justify-center items-center space-x-4">
        <div className={`flex items-center space-x-1 ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
          {isOnline ? <Wifi size={16} /> : <WifiOff size={16} />}
          <span>{isOnline ? 'Connected' : 'Offline'}</span>
        </div>
        {status && (
          <>
            <div className="flex items-center space-x-1">
              <Clock size={16} />
              <span>Last Refresh: {new Date(status.last_data_refresh).toLocaleString()}</span>
            </div>
            <span>|</span>
            <span>Items Analyzed: {status.total_items_analyzed}</span>
          </>
        )}
      </div>
    </footer>
  );
};

export default StatusBar;