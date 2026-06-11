import { useEffect, useState } from 'react';

const STORAGE_KEY = 'aira_show_flagged';
const EVENT = 'aira:show-flagged-changed';

function read(): boolean {
  return localStorage.getItem(STORAGE_KEY) === '1';
}

/**
 * Shared preference: whether the Flagged (duplicates) section is visible.
 * Off by default. Persisted to localStorage and synced across components
 * (and browser tabs) so the sidebar reacts immediately when toggled.
 */
export function useShowFlagged(): [boolean, (value: boolean) => void] {
  const [visible, setVisible] = useState(read);

  useEffect(() => {
    const sync = () => setVisible(read());
    window.addEventListener(EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  const set = (value: boolean) => {
    localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
    setVisible(value);
    window.dispatchEvent(new Event(EVENT));
  };

  return [visible, set];
}
