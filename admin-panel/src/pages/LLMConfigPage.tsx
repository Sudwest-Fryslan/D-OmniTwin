import React, { useState, useEffect } from 'react';
import { llmAPI, systemPromptsAPI } from '../services/api';
import { LLMApiType, LLMConfig, SystemPrompt } from '../types';

export const LLMConfigPage: React.FC = () => {
    const [config, setConfig] = useState<LLMConfig>({ api_url: '', model_name: '', api_type: 'ollama' });
    const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [configRes, modelsRes, promptsRes] = await Promise.all([
                    llmAPI.getConfig(),
                    llmAPI.getModels(),
                    systemPromptsAPI.getAll()
                ]);
                setConfig({ ...configRes.data, api_type: configRes.data.api_type || 'ollama' });
                setAvailableModels(modelsRes.data.models);
                setPrompts(promptsRes.data);

                if (modelsRes.data.error) {
                    setError(`Warning fetching models: ${modelsRes.data.error}`);
                }
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Fout bij het laden van LLM configuratie');
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleConfigSave = async () => {
        setIsSaving(true);
        setError(null);
        setSuccessMessage(null);
        try {
            await llmAPI.updateConfig(config);

            // Reload models in case API URL changed
            const modelsRes = await llmAPI.getModels();
            setAvailableModels(modelsRes.data.models);

            setSuccessMessage('LLM Configuratie succesvol opgeslagen!');
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Fout bij opslaan configuratie');
        } finally {
            setIsSaving(false);
        }
    };

    const handlePromptSave = async (promptName: string, text: string) => {
        setIsSaving(true);
        setError(null);
        try {
            await systemPromptsAPI.update(promptName, { prompt_text: text });
            setSuccessMessage(`Prompt "${promptName}" succesvol bijgewerkt!`);
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err: any) {
            setError(err.response?.data?.detail || `Fout bij opslaan prompt ${promptName}`);
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) return <div className="p-4">Loading LLM Configuration...</div>;

    return (
        <div className="page-container">
            <header className="page-header">
                <div>
                    <h1>AI & LLM Configuratie</h1>
                    <p className="text-secondary">Beheer de verbinding naar het AI Model en pas de systeeminstructies aan.</p>
                </div>
            </header>

            {error && <div className="alert alert-error">{error}</div>}
            {successMessage && <div className="alert alert-success">{successMessage}</div>}

            <div className="grid" style={{ gridTemplateColumns: '1fr', gap: '2rem' }}>

                {/* Connection Settings */}
                <div className="card">
                    <div className="card-header pb-3 mb-3 border-bottom">
                        <h2 className="card-title">LLM API Verbinding</h2>
                    </div>

                    <div className="form-group mb-3">
                        <label className="form-label" htmlFor="apiType">API-type</label>
                        <select
                            id="apiType"
                            className="form-control"
                            value={config.api_type}
                            onChange={(e) => setConfig({ ...config, api_type: e.target.value as LLMApiType })}
                        >
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI-compatibel</option>
                        </select>
                        <small className="text-secondary">
                            Ollama gebruikt de eigen Ollama-API. OpenAI-compatibel werkt met Ollama <code>/v1</code>, vLLM,
                            LM Studio of de LiteLLM-gateway (<code>http://llm-gateway:4000</code>). Een API-sleutel zet je
                            als <code>LLM_API_KEY</code> in <code>.env</code>, niet hier.
                        </small>
                    </div>

                    <div className="form-group mb-3">
                        <label className="form-label" htmlFor="apiUrl">API URL</label>
                        <input
                            id="apiUrl"
                            type="text"
                            className="form-control"
                            value={config.api_url}
                            onChange={(e) => setConfig({ ...config, api_url: e.target.value })}
                            placeholder={config.api_type === 'openai' ? 'http://llm-gateway:4000' : 'http://localhost:11434'}
                        />
                        <small className="text-secondary">De basis URL van de LLM-server (bijv. localhost of een docker container), zonder <code>/api</code> of <code>/v1</code>.</small>
                    </div>

                    <div className="form-group mb-4">
                        <label className="form-label" htmlFor="modelSelect">Actief AI Model</label>
                        <select
                            id="modelSelect"
                            className="form-control"
                            value={config.model_name}
                            onChange={(e) => setConfig({ ...config, model_name: e.target.value })}
                        >
                            <option value="">-- Selecteer of Typ --</option>
                            {availableModels.map(model => (
                                <option key={model} value={model}>{model}</option>
                            ))}
                        </select>
                        <small className="text-secondary">
                            Beschikbare modellen worden na opslaan ingeladen via{' '}
                            <code>{config.api_type === 'openai' ? '/v1/models' : '/api/tags'}</code> op de bovenstaande URL.
                        </small>
                    </div>

                    <button
                        className="btn btn-primary"
                        onClick={handleConfigSave}
                        disabled={isSaving}
                    >
                        {isSaving ? 'Opslaan...' : 'Sla Verbinding Op'}
                    </button>
                </div>

                {/* System Prompts */}
                <div className="card">
                    <div className="card-header pb-3 mb-3 border-bottom">
                        <h2 className="card-title">Systeem Prompts Beheer</h2>
                        <p className="text-secondary">Pas de persona en taakinstructies aan voor de verschillende AI functies binnen de app.</p>
                    </div>

                    {prompts.length === 0 ? (
                        <p className="text-secondary">Geen systeemprompts gevonden in schema_v7_llm_prompts.sql</p>
                    ) : (
                        prompts.map(prompt => (
                            <div key={prompt.naam} className="mb-4 pb-4 border-bottom">
                                <h3 className="h5 mb-2">Prompt: <span className="text-primary">{prompt.naam}</span></h3>
                                {prompt.beschrijving && <p className="text-secondary mb-3">{prompt.beschrijving}</p>}

                                <textarea
                                    className="form-control mb-3"
                                    aria-label={`Systeemprompt ${prompt.naam}`}
                                    rows={10}
                                    style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                                    defaultValue={prompt.prompt_text}
                                    onChange={(e) => {
                                        const newPrompts = [...prompts];
                                        const idx = newPrompts.findIndex(p => p.naam === prompt.naam);
                                        newPrompts[idx].prompt_text = e.target.value;
                                        setPrompts(newPrompts);
                                    }}
                                />

                                <button
                                    className="btn btn-secondary btn-sm"
                                    onClick={() => handlePromptSave(prompt.naam, prompt.prompt_text)}
                                    disabled={isSaving}
                                >
                                    Sla Systeemprompt '{prompt.naam}' Op
                                </button>
                            </div>
                        ))
                    )}
                </div>

            </div>
        </div>
    );
};
