import { createContext, useContext, createSignal } from "solid-js";

const AppContext = createContext();

export function AppProvider(props) {
  const [primLang, setPrimLang] = createSignal('en');
  const [fallLang, setFallLang] = createSignal();
  const [user, setUser] = createSignal({name: "Guest", id:1});

  return (
    <AppContext.Provider value={{
      primLang, setPrimLang,
      fallLang, setFallLang,
      user, setUser,
    }}>
      {props.children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
