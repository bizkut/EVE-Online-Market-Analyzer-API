'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getItemDetails } from '@/lib/api';
import { useModalStore } from '@/stores/modalStore';
import { Dialog, Transition } from '@headlessui/react';
import { X } from 'lucide-react';
import TrendChart from './TrendChart';
import VolumeChart from './VolumeChart';

const ItemDetailModal = () => {
  const { isOpen, closeModal, selectedItemId } = useModalStore();
  const { data: item, isLoading, error } = useQuery({
    queryKey: ['itemDetails', selectedItemId],
    queryFn: () => getItemDetails(selectedItemId!),
    enabled: !!selectedItemId,
  });

  return (
    <Transition appear show={isOpen} as={React.Fragment}>
      <Dialog as="div" className="relative z-50" onClose={closeModal}>
        <Transition.Child
          as={React.Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-75" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={React.Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-panel p-6 text-left align-middle shadow-xl transition-all border border-gray-700">
                <Dialog.Title as="h3" className="text-xl font-bold leading-6 text-white flex justify-between items-center font-orbitron">
                  {item?.name || 'Loading...'}
                  <button onClick={closeModal} className="p-1 rounded-full text-gray-400 hover:bg-gray-700 hover:text-white transition-colors">
                    <X className="h-6 w-6" />
                  </button>
                </Dialog.Title>

                <div className="mt-4">
                  {isLoading && <p className="text-center p-8">Loading item details...</p>}
                  {error && <p className="text-center p-8 text-profit-negative">Error loading item details.</p>}
                  {item && (
                    <div className="space-y-6">
                      <p className="text-sm text-neutral-text">{item.description}</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-background/50 p-4 rounded-lg">
                          <h4 className="font-bold text-white mb-2">Price History</h4>
                          <TrendChart data={item.price_history} />
                        </div>
                        <div className="bg-background/50 p-4 rounded-lg">
                          <h4 className="font-bold text-white mb-2">Volume History</h4>
                          <VolumeChart data={item.volume_history} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

export default ItemDetailModal;