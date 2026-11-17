# Coworker - README

Questo documento descrive la struttura del progetto **Coworker** e il ruolo dei tre file principali:

- `coworker.py`
- `coworker_tools.py`
- `app.py`

L'obiettivo del progetto e costruire un agente AI "co-worker" capace di:

- ricevere un task con criteri di successo,
- usare strumenti reali (browser, filesystem, web search, notifiche),
- fermarsi quando serve approvazione umana,
- riprendere il lavoro dal punto esatto in cui si era interrotto.

---

## Panoramica architetturale

L'architettura e separata in 3 livelli:

1. **Orchestrazione agente** (`coworker.py`)
2. **Integrazione tool e sessioni MCP** (`coworker_tools.py`)
3. **Interfaccia utente Gradio** (`app.py`)

Questa separazione rende il progetto estendibile e riusabile in altri casi d'uso.

---

## 1) `coworker.py` - cervello e loop di controllo

`coworker.py` contiene la classe `Coworker`, che coordina tutto il ciclo operativo.

### Responsabilita principali

- inizializzare worker, middleware, memoria e evaluator (`setup`),
- avviare un turno utente (`run_turn`),
- gestire pause e resume (`_advance`, `resume`),
- verificare se i criteri sono soddisfatti (`evaluate`),
- chiudere risorse esterne (`cleanup`).

### Componenti chiave

- **`TolerateToolErrors`**: middleware custom che intercetta errori tool e li restituisce come `ToolMessage` invece di far fallire il run.
- **`HumanInTheLoopMiddleware`**: mette in pausa il run su tool sensibili (es. `send_push_notification`, `request_human_help`).
- **`TodoListMiddleware`**: mantiene una todo list live visualizzabile in UI.
- **`PIIMiddleware`**: redazione PII in input/output tool.
- **`ModelCallLimitMiddleware`**: evita loop infiniti con limite chiamate modello.

### Flusso logico del turno

1. `run_turn()` salva task e criteri, crea payload e invoca `_advance()`.
2. `_advance()` streamma il worker.
3. Se trova `__interrupt__`, imposta stato `paused` e ritorna alla UI.
4. Se non c'e interrupt, prende la risposta e la passa a `evaluate()`.
5. Se criteri non soddisfatti, costruisce feedback e fa un nuovo tentativo (max `MAX_ATTEMPTS`).
6. `resume()` crea un `Command(resume=...)` e continua dallo stesso thread.

---

## 2) `coworker_tools.py` - toolbox e sessioni persistenti

`coworker_tools.py` definisce i tool e gestisce le sessioni MCP (browser + filesystem).

### Tool inclusi

- `search` (Serper)
- `wikipedia_lookup`
- `send_push_notification`
- `request_human_help`
- tool MCP caricati dinamicamente da:
  - server Playwright (browser)
  - server Filesystem (sandbox)

### `McpSessions`: perche e importante

La classe `McpSessions` mantiene aperte sessioni MCP persistenti tra le tool call.

- `_run()` apre sessioni e carica i tool.
- `self._ready.set()` segnala che i server sono pronti.
- `_stop.wait()` tiene il task vivo finche non arriva stop.
- `stop()` attiva chiusura pulita delle sessioni.

Questo approccio e fondamentale per mantenere stato nel browser durante task lunghi.

### Sandbox filesystem

Il filesystem MCP viene avviato con una root `sandbox` dedicata, cosi i file prodotti dall'agente restano confinati in una directory controllata.

---

## 3) `app.py` - UI e wiring eventi

`app.py` espone il Coworker tramite Gradio.

### Funzioni principali

- `setup()`: crea istanza `Coworker` e avvia tool/sessioni.
- `process_message()`: invia richiesta utente a `run_turn()`.
- `approve()`: richiama `resume()` quando il run e in pausa.
- `watch_todos()`: aggiorna periodicamente il pannello piano/todo.
- `reset()`: chiude sessioni e ricrea Coworker da zero.

### Gestione visibilita bottone approvazione

Il bottone "Approve and continue" e controllato da `coworker.paused`:

- visibile solo quando c'e un interrupt,
- nascosto quando il flusso riprende o termina.

---

## Flusso end-to-end

1. UI avvia `setup()`.
2. `coworker.setup()` carica tool + worker + middleware + evaluator.
3. Utente invia task e criteri.
4. Worker lavora con tool reali.
5. Se serve approvazione, il run si ferma e la UI mostra il bottone.
6. Con `approve()`, il run riparte da dove era fermo.
7. Evaluator decide se il task e completato o se serve un nuovo tentativo.
8. `cleanup()` chiude MCP e browser.

---

## Come estendere il progetto

- Aggiungere tool custom in `coworker_tools.py`.
- Estendere `interrupt_on` per richiedere approvazione su altre azioni.
- Personalizzare il prompt in `WORKER_PROMPT` per nuovi domini.
- Rafforzare l'evaluator con rubriche piu specifiche.
- Evolvere la UI con scelte `approve/reject/edit` per ogni action request.

---

## Note operative

- Il progetto usa variabili ambiente (`.env`) per API key e notifiche.
- Browser e filesystem MCP sono avviati in sessioni persistenti, quindi un reset/cleanup corretto e importante.
- In ambiente Windows/Jupyter puo servire la patch stderr descritta nel notebook del lab.

---

