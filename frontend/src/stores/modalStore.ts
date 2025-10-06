import { create } from 'zustand';

interface ModalState {
  selectedItemId: number | null;
  isOpen: boolean;
  openModal: (itemId: number) => void;
  closeModal: () => void;
}

export const useModalStore = create<ModalState>((set) => ({
  selectedItemId: null,
  isOpen: false,
  openModal: (itemId) => set({ selectedItemId: itemId, isOpen: true }),
  closeModal: () => set({ selectedItemId: null, isOpen: false }),
}));