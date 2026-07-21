# Akaion LifeOS — Task & Workflow Execution API

Servizio backend che riceve un **intent** utente in linguaggio naturale (es. *"invia
un messaggio a Marco e blocca 30 minuti in calendario"*), lo scompone in una
sequenza di step tramite un **Planner agent**, e li esegue tramite un
**Executor agent** che orchestra service modulari (messaging, calendar, ...).
Progettato per girare su Cloud Run in modo cloud-native, ma completamente
eseguibile in locale senza alcuna dipendenza da GCP.

## Architettura

```
Client → POST /api/v1/workflows {intent, context}
       → 202 Accepted {workflow_id, status: pending}   (risposta immediata, non bloccante)

       ├─ salva Workflow su repository (in-memory | Firestore)
       └─ pubblica evento "workflow.created"
              │
              ├─ USE_PUBSUB=false (locale, default) → processing in-process (asyncio.create_task)
              └─ USE_PUBSUB=true  (staging/prod)     → publish su Pub/Sub
                                                            │
                                                       push subscription
                                                            │
                                                    Worker (servizio Cloud Run separato)
                                                    POST /pubsub/push
                                                            │
                                          Planner.run() → Executor.run() → repo.save()

Client → GET /api/v1/workflows/{id}   (polling dello stato)
```

**Separazione agent/service** (il criterio architetturale chiave):

- `app/agents/` — livello decisionale. `PlannerAgent` scompone l'intent in
  `TaskStep`; `ExecutorAgent` orchestra l'esecuzione degli step e gestisce
  fallimenti/stato, ma non conosce i dettagli di *come* uno step venga eseguito.
- `app/services/` — livello esecutivo/IO. Ogni service (`MessagingService`,
  `CalendarService`, ...) implementa la stessa interfaccia `execute(action, payload)`
  (pattern Strategy) e viene risolto a runtime tramite `ServiceRegistry`.
  Aggiungere un nuovo canale (es. email) significa scrivere un nuovo service e
  registrarlo — zero modifiche a planner/executor.
- `app/repository/` — persistenza, stessa interfaccia (`WorkflowRepository`)
  sia per l'implementazione in-memory (dev/test) sia per Firestore (prod).

## Struttura del progetto

```
app/
├── main.py                 # FastAPI app (servizio API)
├── core/
│   ├── config.py           # pydantic-settings, config da env
│   ├── logging.py
│   ├── exceptions.py        # eccezioni di dominio + handler centralizzati
│   └── pubsub.py            # publish evento + fallback locale
├── api/v1/workflows.py       # POST /workflows, GET /workflows/{id}
├── agents/
│   ├── base.py               # interfaccia Agent
│   ├── planner.py             # intent -> list[TaskStep]
│   └── executor.py            # esegue gli step, gestisce fallimenti
├── services/
│   ├── registry.py            # ServiceRegistry (dispatch per nome)
│   ├── messaging.py           # mock connettore messaggistica
│   └── calendar.py             # mock connettore calendario
├── repository/
│   ├── base.py                 # interfaccia WorkflowRepository
│   ├── memory_repo.py           # implementazione in-memory (default locale)
│   └── firestore_repo.py         # implementazione Firestore (prod)
└── workers/
    ├── processor.py              # pipeline planner->executor condivisa
    └── worker.py                  # servizio FastAPI separato: push endpoint Pub/Sub

tests/
├── unit/                          # planner, executor, registry in isolamento
└── integration/                   # API end-to-end via httpx.AsyncClient
```

## Setup e avvio in locale

Nessuna dipendenza da GCP richiesta per lo sviluppo base: di default
`USE_PUBSUB=false` e `USE_FIRESTORE=false`, quindi il servizio usa un
repository in-memory e processa i workflow in-process.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

Esempio di chiamata:

```bash
curl -s -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"intent": "invia un messaggio a Marco e blocca 30 minuti in calendario", "context": {"to": "Marco", "text": "Ci vediamo alle 15"}}'

# → {"workflow_id": "...", "status": "pending"}

curl -s http://localhost:8000/api/v1/workflows/<workflow_id>
# → workflow completato con i risultati di ogni step
```

### Test

```bash
pytest
```

### Stack cloud-native completo in locale (emulatori Pub/Sub + Firestore)

Per dimostrare il percorso completo (API → Pub/Sub → Worker → Firestore)
senza toccare GCP reale:

```bash
docker compose up --build
```

- API su `localhost:8000`, Worker su `localhost:8001`
- `USE_PUBSUB=true` e `USE_FIRESTORE=true` puntano agli emulatori tramite
  `PUBSUB_EMULATOR_HOST` / `FIRESTORE_EMULATOR_HOST`

## Deployment su GCP

Due immagini Docker dallo stesso codebase (`Dockerfile.api`, `Dockerfile.worker`),
deployate come due servizi Cloud Run indipendenti (scalano in modo indipendente:
l'API risponde subito e scala su traffico HTTP, il worker scala sul volume di
messaggi Pub/Sub).

```bash
gcloud builds submit --config cloudbuild.yaml
```

`cloudbuild.yaml` esegue: build + push su Container Registry, deploy di
`akaion-api` (pubblico) e `akaion-worker` (privato, invocabile solo dalla
push subscription).

Setup one-off della subscription (dopo il primo deploy):

```bash
WORKER_URL=$(gcloud run services describe akaion-worker --region=europe-west1 --format='value(status.url)')

gcloud pubsub topics create workflow-created

gcloud pubsub subscriptions create workflow-created-sub \
  --topic=workflow-created \
  --push-endpoint="${WORKER_URL}/pubsub/push" \
  --push-auth-service-account=<SERVICE_ACCOUNT_EMAIL>
```

Il service account usato per l'auth della push subscription deve avere il
ruolo `roles/run.invoker` su `akaion-worker`.

### Persistenza

Abilitare Firestore in modalità Native su GCP e impostare `USE_FIRESTORE=true`:
nessuna migrazione di schema richiesta (document-oriented), la stessa
`Workflow` pydantic viene serializzata/deserializzata direttamente.

## Design decisions

- **Pub/Sub invece di Cloud Tasks**: concettualmente più corretto qui perché
  è un evento di dominio (`workflow.created`) a cui in futuro più subscriber
  potrebbero reagire (es. analytics, audit log), non solo il worker. Cloud
  Tasks resta comunque un'alternativa valida se il flusso restasse
  strettamente punto-punto.
- **Firestore invece di Cloud SQL**: nessuno schema fisso da mantenere (i
  `TaskStep` variano per servizio/azione), scaling serverless nativo, e mapping
  1:1 con i modelli Pydantic senza ORM.
- **Fallback locale invece di richiedere sempre gli emulatori**: `USE_PUBSUB`/
  `USE_FIRESTORE` sono feature flag a runtime — permette di sviluppare e
  testare l'intera logica di planning/execution senza alcuna dipendenza
  esterna, mantenendo lo stesso identico codice di dominio quando si passa
  alla configurazione cloud-native completa.
- **Planner rule-based invece di LLM-based**: l'interfaccia (`intent -> list[TaskStep]`)
  è la stessa che userebbe un planner basato su LLM con function calling;
  la versione rule-based è deterministica, testabile senza costi/latenza
  esterna, ed è uno swap isolato in `PlannerAgent._plan` quando si vuole
  passare a un LLM.

## API Reference

Documentazione OpenAPI/Swagger generata automaticamente: `GET /docs` (o `/redoc`).

Endpoint principali:

| Metodo | Path | Descrizione |
|---|---|---|
| POST | `/api/v1/workflows` | Crea un workflow da un intent, ritorna 202 + `workflow_id` |
| GET | `/api/v1/workflows/{id}` | Stato e risultato del workflow |
| GET | `/healthz` | Health check |
