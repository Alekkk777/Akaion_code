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

infra/                              # Terraform: infrastruttura GCP (vedi sezione Deployment)
├── main.tf
├── variables.tf
├── outputs.tf
└── providers.tf
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

## Deployment instructions for GCP

Due immagini Docker dallo stesso codebase (`Dockerfile.api`, `Dockerfile.worker`),
deployate come due servizi Cloud Run indipendenti (scalano in modo indipendente:
l'API risponde subito e scala su traffico HTTP, il worker scala sul volume di
messaggi Pub/Sub).

**Terraform possiede l'infrastruttura** (API abilitate, Artifact Registry,
Firestore, topic/subscription Pub/Sub, service account con ruoli minimi, i due
servizi Cloud Run) — **Cloud Build possiede i deploy applicativi** (build,
push, `gcloud run deploy` con l'immagine aggiornata). Questa separazione evita
che i due processi si "contendano" lo stesso campo (l'immagine del container
è in `lifecycle.ignore_changes` lato Terraform per questo motivo).

Procedura verificata con un deploy reale end-to-end su un progetto GCP: infra
applicata con Terraform, build+deploy con Cloud Build, workflow completo
testato via curl attraverso Pub/Sub fino al worker, poi tutto distrutto con
`terraform destroy`.

### Prerequisiti

1. **Account GCP con billing abilitato** su un progetto (nuovo o esistente).
   ```bash
   gcloud billing accounts list
   gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ACCOUNT_ID>
   ```
2. **gcloud CLI** installato e autenticato:
   ```bash
   gcloud auth login                       # identità utente per i comandi gcloud
   gcloud config set project <PROJECT_ID>
   gcloud auth application-default login   # credenziali usate da Terraform e dai client Python (ADC)
   ```
3. **Terraform** >= 1.5 installato (`brew install hashicorp/tap/terraform` o binario da [releases.hashicorp.com](https://releases.hashicorp.com/terraform/)).

### 1. Provisioning infrastruttura (una tantum, o ad ogni cambio infra)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # imposta project_id

terraform init
terraform plan   -out=tfplan                    # rivedi cosa verrebbe creato
terraform apply  tfplan
```

Crea: API abilitate, Artifact Registry, Firestore (Native), topic + push
subscription Pub/Sub, 3 service account dedicati (vedi sezione IAM sotto), e i
due servizi Cloud Run con un'immagine placeholder (`us-docker.pkg.dev/cloudrun/container/hello`
— è normale, il passo successivo la sostituisce con quella reale).

**Gotcha noti** (incontrati durante il test di deploy, risolti una tantum per progetto):

- *Pub/Sub service agent inesistente*: se il primo `apply` fallisce su
  `google_project_iam_member.pubsub_token_creator` con `does not exist`, il
  service agent di Pub/Sub non è stato ancora creato (è lazy). Fix:
  ```bash
  gcloud beta services identity create --service=pubsub.googleapis.com --project=<PROJECT_ID>
  ```
  poi rilancia `terraform apply`.

### 2. Build & deploy applicativo (ad ogni cambio di codice)

```bash
gcloud builds submit --config cloudbuild.yaml
```

`cloudbuild.yaml` compila entrambe le immagini, le pusha su Artifact Registry
(`europe-west1-docker.pkg.dev/<project>/akaion-lifeos/...`) e aggiorna
`akaion-api` e `akaion-worker` con `gcloud run deploy --image=...` (senza
toccare IAM/env vars, già gestiti da Terraform).

### 3. Verifica

```bash
API_URL=$(cd infra && terraform output -raw api_url)

curl "$API_URL/health"

curl -X POST "$API_URL/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{"intent": "invia un messaggio a Marco e blocca 30 minuti in calendario", "context": {"to": "Marco"}}'
# → {"workflow_id": "...", "status": "pending"}

curl "$API_URL/api/v1/workflows/<workflow_id>"
# → status: completed, dopo il giro api -> Pub/Sub -> worker
```

### 4. Decommissioning

```bash
cd infra
terraform destroy
```

**Gotcha noti:**

- *`cannot destroy service without deletion_protection=false`*: i servizi
  Cloud Run v2 hanno `deletion_protection = false` esplicito in `main.tf`
  proprio per evitare questo blocco; se il provider viene aggiornato e il
  problema ricompare, impostalo e rilancia `apply` prima del `destroy`.
- *Firestore non viene davvero cancellato*: `google_firestore_database` ha
  `deletion_policy = "ABANDON"` (default del provider, per evitare
  cancellazioni accidentali di dati) — `terraform destroy` lo rimuove dallo
  stato ma **non** cancella il database reale. Per eliminarlo davvero:
  ```bash
  gcloud firestore databases delete --database='(default)' --project=<PROJECT_ID>
  ```

### IAM: service account e ruoli minimi

Tre identità distinte, ciascuna con solo i ruoli che le servono:

| Service account | Usato da | Ruoli | Perché |
|---|---|---|---|
| `akaion-api-runtime` | runtime del servizio `akaion-api` | `roles/datastore.user`, `roles/pubsub.publisher` | l'api legge/scrive workflow su Firestore e pubblica l'evento `workflow.created` |
| `akaion-worker-runtime` | runtime del servizio `akaion-worker` | `roles/datastore.user`, `roles/pubsub.subscriber` | il worker legge/scrive workflow su Firestore; `pubsub.subscriber` non è strettamente necessario per la consegna push (autenticata via OIDC, non via pull) ma incluso per coerenza con un eventuale passaggio a pull subscription |
| `akaion-pubsub-invoker` | identità della **push subscription**, non del container | `roles/run.invoker` su `akaion-worker` | è il SA che Pub/Sub usa per generare il token OIDC con cui invoca l'endpoint privato `/pubsub/push` |

`akaion-api` resta pubblico (`roles/run.invoker` su `allUsers`); `akaion-worker`
è invocabile solo dal SA `akaion-pubsub-invoker`.

### Persistenza

Firestore in modalità Native, creato da Terraform. Nessuna migrazione di
schema richiesta (document-oriented), la stessa `Workflow` pydantic viene
serializzata/deserializzata direttamente.

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
- **Service account runtime dedicati e distinti dal SA di invocazione Pub/Sub**:
  `akaion-api-runtime` e `akaion-worker-runtime` hanno solo `datastore.user` +
  il ruolo Pub/Sub che serve loro (publisher/subscriber) — girare con il
  Compute Engine default SA avrebbe dato permessi di progetto molto più ampi
  del necessario. Il terzo SA (`akaion-pubsub-invoker`) è concettualmente
  diverso: non gira nel container, è l'identità che Pub/Sub usa per firmare i
  token OIDC verso il worker.
- **Endpoint di health check su `/health`, non `/healthz`**: `/healthz` è un path
  riservato a livello di infrastruttura Google (intercettato dal Google Frontend
  prima di raggiungere il container, verificato in deploy reale su Cloud Run) —
  qualunque altro path, incluso `/health`, arriva regolarmente all'app.
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
| GET | `/health` | Health check |
