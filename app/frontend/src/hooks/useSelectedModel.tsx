import { createContext, ReactNode, useCallback, useContext, useState } from 'react';

const STORAGE_KEY = 'nlq_selected_model';

interface SelectedModelContextValue {
  model: string;
  setModel: (model: string) => void;
}

const SelectedModelContext = createContext<SelectedModelContextValue | undefined>(undefined);

const readStored = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) || '';
  } catch {
    return '';
  }
};

/** The model chosen in the navbar picker, shared with the query box so requests use it. */
export const SelectedModelProvider = ({ children }: { children: ReactNode }) => {
  const [model, setModelState] = useState<string>(readStored);

  const setModel = useCallback((next: string) => {
    setModelState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable (private window); the choice still applies for this session.
    }
  }, []);

  return (
    <SelectedModelContext.Provider value={{ model, setModel }}>{children}</SelectedModelContext.Provider>
  );
};

export const useSelectedModel = () => {
  const ctx = useContext(SelectedModelContext);
  if (!ctx) throw new Error('useSelectedModel must be used within SelectedModelProvider');
  return ctx;
};
