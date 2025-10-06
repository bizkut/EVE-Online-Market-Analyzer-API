import React from 'react';

const SkeletonLoader = ({ className }: { className?: string }) => {
  return (
    <div className={`animate-pulse bg-gray-300 dark:bg-gray-700 rounded-md ${className}`} />
  );
};

export const TableSkeleton = () => (
  <div className="bg-panel rounded-2xl shadow-lg overflow-hidden p-4">
    <div className="space-y-4">
      <SkeletonLoader className="h-8 w-1/4" />
      <div className="space-y-2">
        {[...Array(10)].map((_, i) => (
          <SkeletonLoader key={i} className="h-12 w-full" />
        ))}
      </div>
    </div>
  </div>
);

export const ModalSkeleton = () => (
    <div className="space-y-6">
        <div className="flex items-center gap-4">
            <SkeletonLoader className="h-12 w-12 rounded-md" />
            <SkeletonLoader className="h-8 w-1/3" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <SkeletonLoader className="h-16 w-full" />
            <SkeletonLoader className="h-16 w-full" />
            <SkeletonLoader className="h-16 w-full" />
            <SkeletonLoader className="h-16 w-full" />
        </div>
        <SkeletonLoader className="h-24 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonLoader className="h-72 w-full" />
            <SkeletonLoader className="h-72 w-full" />
        </div>
    </div>
);