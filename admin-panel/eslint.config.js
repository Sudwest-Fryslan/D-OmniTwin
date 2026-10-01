// Minimale lintset, vergelijkbaar met wat CRA (eslint-config-react-app) afdwong:
// alleen de React-hookregels. Strengere typescript-eslint-regels kunnen later.
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['build', 'node_modules'] },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      globals: globals.browser,
    },
    // typescript-eslint geregistreerd zodat eslint-disable-commentaren in de code kloppen.
    plugins: { '@typescript-eslint': tseslint.plugin, 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
);
