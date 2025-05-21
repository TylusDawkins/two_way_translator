import { createContext, useContext, createSignal, onMount } from "solid-js";

const AppContext = createContext();

export function AppProvider(props) {
  // Initialize session ID from localStorage or generate new one
  const getSessionId = () => {
    const stored = localStorage.getItem('sessionId');
    if (stored) return stored;
    const newId = crypto.randomUUID();
    localStorage.setItem('sessionId', newId);
    return newId;
  };
  const [sessionId, setSessionId] = createSignal(getSessionId());

  // Other state
  const getPrimLang = () => {
    const stored = localStorage.getItem('primLang');
    console.log('Initializing primLang from localStorage:', stored);
    return stored !== null ? stored : 'en';
  };
  const [primLang, setPrimLang] = createSignal(getPrimLang());

  const getFallLang = () => {
    const stored = localStorage.getItem('fallLang');
    console.log('Initializing fallLang from localStorage:', stored);
    return stored !== null ? stored : 'es';
  };
  const [fallLang, setFallLang] = createSignal(getFallLang());

  const getSpeakerId = () => {
    const stored = localStorage.getItem('speakerId');
    return stored || 'speaker_1';
  };
  const [speakerId, setSpeakerId] = createSignal(getSpeakerId());

  const [user, setUser] = createSignal(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : { name: "Guest", id: 1 };
  });

  // Debug localStorage state
  onMount(() => {
    console.log('AppContext mounted, localStorage state:');
    console.log('primLang:', localStorage.getItem('primLang'));
    console.log('fallLang:', localStorage.getItem('fallLang'));
  });

  // Persist language changes
  const updatePrimLang = (lang) => {
    console.log('Updating primLang to:', lang);
    setPrimLang(lang);
    localStorage.setItem('primLang', lang);
  };

  const updateFallLang = (lang) => {
    console.log('Updating fallLang to:', lang);
    setFallLang(lang);
    localStorage.setItem('fallLang', lang);
  };

  // Persist speaker ID changes
  const updateSpeakerId = (id) => {
    setSpeakerId(id);
    localStorage.setItem('speakerId', id);
  };

  // Persist user changes
  const updateUser = (newUser) => {
    setUser(newUser);
    localStorage.setItem('user', JSON.stringify(newUser));
  };

  // Reset session (for testing or user logout)
  const resetSession = () => {
    const newId = crypto.randomUUID();
    setSessionId(newId);
    localStorage.setItem('sessionId', newId);
  };

  return (
    <AppContext.Provider value={{
      primLang, setPrimLang: updatePrimLang,
      fallLang, setFallLang: updateFallLang,
      speakerId, setSpeakerId: updateSpeakerId,
      user, setUser: updateUser,
      sessionId, setSessionId,
      resetSession,
    }}>
      {props.children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
