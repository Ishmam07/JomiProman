import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getLang, setLangState, t as rawT } from "./strings.js";

const LANG_KEY = "jomiproman.lang";
const THEME_KEY = "jomiproman.theme";

function read(key, fallback) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}
function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable */
  }
}
const systemTheme = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";

const Ctx = createContext(null);

export function AppProvider({ children }) {
  const [lang, setLangValue] = useState(() => {
    const l = read(LANG_KEY, "bn");
    setLangState(l); // must be set before the first render so digits/text are right
    return l === "en" ? "en" : "bn";
  });
  const [theme, setTheme] = useState(() => read(THEME_KEY, "") || systemTheme());

  useEffect(() => {
    setLangState(lang);
    write(LANG_KEY, lang);
    document.documentElement.lang = lang === "en" ? "en" : "bn";
    document.title = lang === "en" ? "JomiProman · Land deed verification" : "জমি প্রমাণ · JomiProman";
  }, [lang]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    write(THEME_KEY, theme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#12141f" : "#4338ca");
  }, [theme]);

  const toggleLang = useCallback(() => {
    const next = getLang() === "bn" ? "en" : "bn";
    setLangState(next);
    setLangValue(next);
  }, []);
  const toggleTheme = useCallback(() => setTheme((cur) => (cur === "dark" ? "light" : "dark")), []);

  // `t` changes identity with the language so memoised children re-render.
  const value = useMemo(
    () => ({ lang, theme, toggleLang, toggleTheme, t: (k, v) => rawT(k, v) }),
    [lang, theme, toggleLang, toggleTheme]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useApp = () => useContext(Ctx);
