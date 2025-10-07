'use client';

import React from 'react';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { getItemDetails } from '@/lib/api';
import { useModalStore } from '@/stores/modalStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { Dialog, Transition } from '@headlessui/react';
import { X, ArrowUp, ArrowDown, Minus } from 'lucide-react';
import TrendChart from './TrendChart';
import VolumeChart from './VolumeChart';
import ProfitEvolutionChart from './ProfitEvolutionChart';
import { ModalSkeleton } from './SkeletonLoader';

const formatCurrency = (num: number | null) => num ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'ISK' }).format(num) : 'N/A';
const formatPercent = (num: number | null) => num ? `${(num * 100).toFixed(2)}%` : 'N/A';

const ItemDetailModal = () => {
  const { isOpen, closeModal, selectedItemId } = useModalStore();
  const { region } = useSettingsStore();
  const { data: item, isLoading, error } = useQuery({
    queryKey: ['itemDetails', selectedItemId, region],
    queryFn: () => getItemDetails(selectedItemId!, parseInt(region, 10)),
    enabled: !!selectedItemId,
  });

  const TrendIcon = () => {
    if (!item || !item.trend_direction) return <Minus className="text-gray-500" />;
    if (item.trend_direction === 'Up') return <ArrowUp className="text-profit-positive" />;
    if (item.trend_direction === 'Down') return <ArrowDown className="text-profit-negative" />;
    return <Minus className="text-gray-500" />;
  };

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
              <Dialog.Panel className="w-full max-w-6xl transform overflow-hidden rounded-2xl bg-panel p-6 text-left align-middle shadow-xl transition-all border border-gray-700">
                <Dialog.Title as="h3" className="text-xl font-bold leading-6 text-white flex justify-between items-center font-orbitron">
                  <div className="flex items-center gap-4">
                    {item && !isLoading ? (
                      <Image src={item.thumbnail_url} alt={item.name} width={48} height={48} className="rounded-md" />
                    ) : (
                      <div className="h-12 w-12 rounded-md bg-gray-700 animate-pulse" />
                    )}
                    <span>{item?.name || 'Loading...'}</span>
                  </div>
                  <button onClick={closeModal} className="p-1 rounded-full text-gray-400 hover:bg-gray-700 hover:text-white transition-colors">
                    <X className="h-6 w-6" />
                  </button>
                </Dialog.Title>

                <div className="mt-4">
                  {isLoading && <ModalSkeleton />}
                  {error && <div className="h-96 flex items-center justify-center"><p className="text-profit-negative">Error loading item details.</p></div>}
                  {!isLoading && item && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        <div className="bg-background/50 p-3 rounded-lg">
                          <p className="text-sm text-gray-400">Predicted Buy</p>
                          <p className="text-lg font-bold text-white">{formatCurrency(item.predicted_buy_price)}</p>
                        </div>
                        <div className="bg-background/50 p-3 rounded-lg">
                          <p className="text-sm text-gray-400">Predicted Sell</p>
                          <p className="text-lg font-bold text-white">{formatCurrency(item.predicted_sell_price)}</p>
                        </div>
                        <div className="bg-background/50 p-3 rounded-lg">
                          <p className="text-sm text-gray-400">Volatility</p>
                          <p className="text-lg font-bold text-white">{formatPercent(item.volatility)}</p>
                        </div>
                        <div className="bg-background/50 p-3 rounded-lg flex flex-col justify-center items-center">
                          <p className="text-sm text-gray-400">Trend</p>
                          <TrendIcon />
                        </div>
                      </div>
                      <p className="text-sm text-neutral-text italic">{item.description || 'No description available.'}</p>
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-background/50 p-4 rounded-lg">
                          <h4 className="font-bold text-white mb-2">Price History</h4>
                          <TrendChart data={item.price_history} />
                        </div>
                        <div className="bg-background/50 p-4 rounded-lg">
                          <h4 className="font-bold text-white mb-2">Volume History</h4>
                          <VolumeChart data={item.volume_history} />
                        </div>
                         <div className="bg-background/50 p-4 rounded-lg lg:col-span-2">
                          <h4 className="font-bold text-white mb-2">Profit & ROI History</h4>
                           <ProfitEvolutionChart data={item.profit_history} />
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