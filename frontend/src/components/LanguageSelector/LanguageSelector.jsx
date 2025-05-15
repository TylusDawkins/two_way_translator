import { useApp } from "@context/AppContext";
import languages from "@utils/languages.json";

export default function LanguageSelector() {
  const { primLang, setPrimLang, fallLang, setFallLang } = useApp();

  return (
    <div class="language-select-controls">
      <label>
        Primary Language:
        <select value={primLang()} onInput={(e) => setPrimLang(e.currentTarget.value)}>
          {languages.map((lang,i) => (
            <option key={i}value={lang.code}>{lang.label}</option>
          ))}
        </select>
      </label>
      <label style="margin-left: 1rem;">
        Secondary Language:
        <select value={fallLang()} onInput={(e) => setFallLang(e.currentTarget.value)}>
          {languages.map((lang) => (
            <option value={lang.code}>{lang.label}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
